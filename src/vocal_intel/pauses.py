"""Silence and pause detection derived from voice-activity segments.

Pause detection deliberately consumes the shared VAD segmentation instead of
running a second audio classifier. A pause is a non-speech region between two
speech regions; leading and trailing silence are not counted as pauses.

The duration cut-points below are PROVISIONAL placeholders. They are scheduled
to move into the versioned threshold configuration in a later phase.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from vocal_intel.vad import NON_SPEECH, SPEECH, Segment, VadResult

DEFAULT_MIN_PAUSE_SECONDS = 0.20
SHORT_PAUSE_MAX_SECONDS = 0.50
MEDIUM_PAUSE_MAX_SECONDS = 1.00

SHORT_PAUSE = "short"
MEDIUM_PAUSE = "medium"
LONG_PAUSE = "long"


class PauseDetectionError(ValueError):
    """Raised for invalid input to pause detection."""


@dataclass(frozen=True, eq=False)
class PauseRegion:
    """A non-speech region between speech regions."""

    start_seconds: float
    end_seconds: float
    label: str

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass(frozen=True, eq=False)
class PauseSummary:
    """Aggregate pause counts and durations."""

    pause_count: int
    total_pause_seconds: float
    mean_pause_seconds: float
    longest_pause_seconds: float
    short_count: int
    medium_count: int
    long_count: int


@dataclass(frozen=True, eq=False)
class PauseAnalysis:
    """Pause regions, durations, and summary derived from VAD output."""

    pauses: list
    pause_durations_seconds: list
    summary: PauseSummary
    source_segment_count: int


def _validate_duration(value: float, name: str, *, allow_zero: bool = False) -> float:
    duration = float(value)
    if not math.isfinite(duration):
        raise PauseDetectionError(f"{name} must be finite")
    if allow_zero:
        if duration < 0.0:
            raise PauseDetectionError(f"{name} must be non-negative")
    elif duration <= 0.0:
        raise PauseDetectionError(f"{name} must be positive")
    return duration


def _validate_thresholds(
    min_pause_seconds: float,
    short_pause_max_seconds: float,
    medium_pause_max_seconds: float,
) -> tuple[float, float, float]:
    minimum = _validate_duration(min_pause_seconds, "min_pause_seconds", allow_zero=True)
    short_max = _validate_duration(short_pause_max_seconds, "short_pause_max_seconds")
    medium_max = _validate_duration(medium_pause_max_seconds, "medium_pause_max_seconds")
    if not short_max < medium_max:
        raise PauseDetectionError("short_pause_max_seconds must be less than medium_pause_max_seconds")
    return minimum, short_max, medium_max


def pause_label(
    duration_seconds: float,
    *,
    short_pause_max_seconds: float = SHORT_PAUSE_MAX_SECONDS,
    medium_pause_max_seconds: float = MEDIUM_PAUSE_MAX_SECONDS,
) -> str:
    """Return the provisional short / medium / long label for a pause."""
    duration = _validate_duration(duration_seconds, "duration_seconds")
    _, short_max, medium_max = _validate_thresholds(
        DEFAULT_MIN_PAUSE_SECONDS,
        short_pause_max_seconds,
        medium_pause_max_seconds,
    )
    if duration < short_max:
        return SHORT_PAUSE
    if duration < medium_max:
        return MEDIUM_PAUSE
    return LONG_PAUSE


def _validate_segments(segments: list) -> None:
    previous_end: float | None = None
    for segment in segments:
        if segment.label not in {SPEECH, NON_SPEECH}:
            raise PauseDetectionError(f"unsupported segment label: {segment.label}")
        start = _validate_duration(segment.start_seconds, "segment start", allow_zero=True)
        end = _validate_duration(segment.end_seconds, "segment end", allow_zero=True)
        if end <= start:
            raise PauseDetectionError("segment end must be after segment start")
        if previous_end is not None and start < previous_end:
            raise PauseDetectionError("segments must be sorted and non-overlapping")
        previous_end = end


def _summarise(pauses: list) -> PauseSummary:
    durations = [pause.duration_seconds for pause in pauses]
    total = float(sum(durations))
    count = len(pauses)
    return PauseSummary(
        pause_count=count,
        total_pause_seconds=total,
        mean_pause_seconds=(total / count) if count else 0.0,
        longest_pause_seconds=max(durations) if durations else 0.0,
        short_count=sum(1 for pause in pauses if pause.label == SHORT_PAUSE),
        medium_count=sum(1 for pause in pauses if pause.label == MEDIUM_PAUSE),
        long_count=sum(1 for pause in pauses if pause.label == LONG_PAUSE),
    )


def detect_pauses_from_segments(
    segments: Iterable[Segment],
    *,
    min_pause_seconds: float = DEFAULT_MIN_PAUSE_SECONDS,
    short_pause_max_seconds: float = SHORT_PAUSE_MAX_SECONDS,
    medium_pause_max_seconds: float = MEDIUM_PAUSE_MAX_SECONDS,
) -> PauseAnalysis:
    """Find non-speech regions between speech regions."""
    segment_list = list(segments)
    minimum, short_max, medium_max = _validate_thresholds(
        min_pause_seconds,
        short_pause_max_seconds,
        medium_pause_max_seconds,
    )
    _validate_segments(segment_list)

    pauses: list = []
    speech_before = False
    has_speech_after = [False] * len(segment_list)
    seen_speech_after = False
    for i in range(len(segment_list) - 1, -1, -1):
        has_speech_after[i] = seen_speech_after
        if segment_list[i].label == SPEECH:
            seen_speech_after = True

    for i, segment in enumerate(segment_list):
        if segment.label == SPEECH:
            speech_before = True
            continue
        if not speech_before or not has_speech_after[i]:
            continue
        duration = segment.duration_seconds
        if duration < minimum:
            continue
        pauses.append(
            PauseRegion(
                start_seconds=segment.start_seconds,
                end_seconds=segment.end_seconds,
                label=pause_label(
                    duration,
                    short_pause_max_seconds=short_max,
                    medium_pause_max_seconds=medium_max,
                ),
            )
        )

    durations = [pause.duration_seconds for pause in pauses]
    return PauseAnalysis(
        pauses=pauses,
        pause_durations_seconds=durations,
        summary=_summarise(pauses),
        source_segment_count=len(segment_list),
    )


def analyze_pauses(vad_result: VadResult, **kwargs) -> PauseAnalysis:
    """Analyse pauses from a voice-activity detection result."""
    return detect_pauses_from_segments(vad_result.segments, **kwargs)
