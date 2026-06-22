"""Speech pace estimation from signal-level envelope heuristics.

The estimator consumes the shared VAD segmentation, sums speech-active time,
and counts syllable-like energy nuclei inside those speech regions. The count is
normalised by speech-active duration instead of total clip duration, so leading
silence, trailing silence, and internal pauses do not make speech sound slower.

This phase intentionally stays dependency-light. The envelope-nucleus method is
validated on deterministic synthetic pulse trains; real script-read validation
is still required by the manual protocol. Qualitative thresholds are sourced
from the versioned threshold configuration and remain provisional.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from vocal_intel.config import DEFAULT_THRESHOLD_CONFIG, ThresholdConfig
from vocal_intel.loudness import frame_rms
from vocal_intel.vad import NON_SPEECH, SPEECH, Segment, VadResult

DEFAULT_FRAME_MS = 40.0
DEFAULT_HOP_MS = 10.0
DEFAULT_SMOOTHING_FRAMES = 5
DEFAULT_NUCLEUS_THRESHOLD_RATIO = DEFAULT_THRESHOLD_CONFIG.pace.nucleus_threshold_ratio
DEFAULT_MIN_NUCLEUS_DISTANCE_SECONDS = DEFAULT_THRESHOLD_CONFIG.pace.min_nucleus_distance_seconds

SLOW_SYLLABLE_RATE_MAX = DEFAULT_THRESHOLD_CONFIG.pace.slow_syllable_rate_max
FAST_SYLLABLE_RATE_MIN = DEFAULT_THRESHOLD_CONFIG.pace.fast_syllable_rate_min

SLOW_PACE = "slow"
NORMAL_PACE = "normal"
FAST_PACE = "fast"
UNKNOWN_PACE = "unknown"


class PaceError(ValueError):
    """Raised for invalid input to speech pace analysis."""


@dataclass(frozen=True, eq=False)
class PaceAnalysis:
    """Speech-active duration, syllable-rate estimate, and pace label."""

    sample_rate: int
    speech_active_seconds: float
    estimated_syllable_count: int
    syllable_rate_per_second: float | None
    syllables_per_minute: float | None
    label: str
    frame_times: np.ndarray
    envelope_rms: np.ndarray
    speech_frame_mask: np.ndarray
    syllable_peak_times: np.ndarray
    source_segment_count: int
    config_version: str = DEFAULT_THRESHOLD_CONFIG.version


def _as_mono(samples) -> np.ndarray:
    arr = np.asarray(samples, dtype=np.float64)
    if arr.ndim != 1:
        raise PaceError("samples must be a 1-D (mono) array")
    if arr.size == 0:
        raise PaceError("samples must not be empty")
    return arr


def _positive_finite(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise PaceError(f"{name} must be positive and finite")
    return number


def _validate_segments(segments: Iterable[Segment], total_duration: float) -> list:
    segment_list = list(segments)
    previous_end: float | None = None
    for segment in segment_list:
        if segment.label not in {SPEECH, NON_SPEECH}:
            raise PaceError(f"unsupported segment label: {segment.label}")
        start = float(segment.start_seconds)
        end = float(segment.end_seconds)
        if not math.isfinite(start) or not math.isfinite(end):
            raise PaceError("segment times must be finite")
        if start < 0.0:
            raise PaceError("segment start must be non-negative")
        if end <= start:
            raise PaceError("segment end must be after segment start")
        if previous_end is not None and start < previous_end:
            raise PaceError("segments must be sorted and non-overlapping")
        if end > total_duration + 1e-9:
            raise PaceError("segment end must not exceed signal duration")
        previous_end = end
    return segment_list


def speech_active_duration_seconds(segments: Iterable[Segment]) -> float:
    """Return total duration of speech-labelled segments."""
    total = 0.0
    for segment in segments:
        if segment.label == SPEECH:
            total += float(segment.duration_seconds)
    return total


def pace_label(
    syllable_rate_per_second: float | None,
    *,
    config: ThresholdConfig = DEFAULT_THRESHOLD_CONFIG,
) -> str:
    """Map a syllable-rate estimate to a provisional slow / normal / fast label."""
    if syllable_rate_per_second is None:
        return UNKNOWN_PACE
    rate = float(syllable_rate_per_second)
    if not math.isfinite(rate) or rate < 0.0:
        raise PaceError("syllable_rate_per_second must be finite and non-negative")
    thresholds = config.pace
    if rate < thresholds.slow_syllable_rate_max:
        return SLOW_PACE
    if rate <= thresholds.fast_syllable_rate_min:
        return NORMAL_PACE
    return FAST_PACE


def _frame_starts(n_samples: int, frame_length: int, hop_length: int) -> np.ndarray:
    if n_samples <= frame_length:
        return np.array([0], dtype=np.int64)
    return np.arange(0, n_samples - frame_length + 1, hop_length, dtype=np.int64)


def _smooth(values: np.ndarray, width: int) -> np.ndarray:
    if width <= 1 or values.size <= 1:
        return values.astype(np.float64, copy=True)
    usable_width = min(int(width), int(values.size))
    left = usable_width // 2
    right = usable_width - 1 - left
    padded = np.pad(values, (left, right), mode="edge")
    kernel = np.full(usable_width, 1.0 / usable_width, dtype=np.float64)
    return np.convolve(padded, kernel, mode="valid").astype(np.float64)


def _speech_frame_mask(frame_centres: np.ndarray, segments: list) -> np.ndarray:
    mask = np.zeros(frame_centres.shape, dtype=bool)
    for segment in segments:
        if segment.label != SPEECH:
            continue
        mask |= (frame_centres >= segment.start_seconds) & (frame_centres < segment.end_seconds)
    return mask


def _find_syllable_peaks(
    frame_times: np.ndarray,
    envelope: np.ndarray,
    speech_mask: np.ndarray,
    *,
    nucleus_threshold_ratio: float,
    min_nucleus_distance_seconds: float,
) -> np.ndarray:
    active_envelope = envelope[speech_mask]
    if active_envelope.size == 0:
        return np.array([], dtype=np.float64)

    floor = float(np.percentile(active_envelope, 20.0))
    ceiling = float(np.percentile(active_envelope, 95.0))
    dynamic_range = ceiling - floor
    if ceiling <= 0.0 or dynamic_range <= 1e-9:
        return np.array([], dtype=np.float64)

    threshold = floor + (nucleus_threshold_ratio * dynamic_range)
    high_energy = (envelope >= threshold) & speech_mask

    peak_indices: list[int] = []
    index = 0
    while index < len(high_energy):
        if not bool(high_energy[index]):
            index += 1
            continue
        end = index + 1
        while end < len(high_energy) and bool(high_energy[end]):
            end += 1
        peak_index = index + int(np.argmax(envelope[index:end]))
        if not peak_indices:
            peak_indices.append(peak_index)
        else:
            previous_index = peak_indices[-1]
            distance = float(frame_times[peak_index] - frame_times[previous_index])
            if distance >= min_nucleus_distance_seconds:
                peak_indices.append(peak_index)
            elif envelope[peak_index] > envelope[previous_index]:
                peak_indices[-1] = peak_index
        index = end

    return frame_times[np.asarray(peak_indices, dtype=np.int64)].astype(np.float64)


def analyze_pace(
    samples,
    vad_result: VadResult,
    *,
    frame_ms: float = DEFAULT_FRAME_MS,
    hop_ms: float = DEFAULT_HOP_MS,
    smoothing_frames: int = DEFAULT_SMOOTHING_FRAMES,
    nucleus_threshold_ratio: float | None = None,
    min_nucleus_distance_seconds: float | None = None,
    config: ThresholdConfig = DEFAULT_THRESHOLD_CONFIG,
) -> PaceAnalysis:
    """Estimate speech pace from mono audio and an existing VAD result."""
    arr = _as_mono(samples)
    sample_rate = int(vad_result.sample_rate)
    if sample_rate <= 0:
        raise PaceError("vad_result.sample_rate must be positive")
    frame_duration = _positive_finite(frame_ms, "frame_ms")
    hop_duration = _positive_finite(hop_ms, "hop_ms")
    thresholds = config.pace
    min_distance = _positive_finite(
        thresholds.min_nucleus_distance_seconds
        if min_nucleus_distance_seconds is None
        else min_nucleus_distance_seconds,
        "min_nucleus_distance_seconds",
    )
    smooth_width = int(smoothing_frames)
    if smooth_width <= 0:
        raise PaceError("smoothing_frames must be positive")
    threshold_ratio = (
        thresholds.nucleus_threshold_ratio if nucleus_threshold_ratio is None else float(nucleus_threshold_ratio)
    )
    if not math.isfinite(threshold_ratio) or not 0.0 <= threshold_ratio <= 1.0:
        raise PaceError("nucleus_threshold_ratio must be within [0.0, 1.0]")

    total_duration = arr.size / sample_rate
    segments = _validate_segments(vad_result.segments, total_duration)
    speech_active_seconds = speech_active_duration_seconds(segments)

    frame_length = max(1, int(round(frame_duration / 1000.0 * sample_rate)))
    hop_length = max(1, int(round(hop_duration / 1000.0 * sample_rate)))
    starts = _frame_starts(arr.size, frame_length, hop_length)
    frame_times = (starts / sample_rate).astype(np.float64)
    frame_centres = frame_times + ((frame_length / sample_rate) / 2.0)
    envelope = _smooth(frame_rms(arr, frame_length, hop_length), smooth_width)
    speech_mask = _speech_frame_mask(frame_centres, segments)

    if speech_active_seconds <= 0.0:
        syllable_peaks = np.array([], dtype=np.float64)
        syllable_rate = None
        syllables_per_minute = None
    else:
        syllable_peaks = _find_syllable_peaks(
            frame_times,
            envelope,
            speech_mask,
            nucleus_threshold_ratio=threshold_ratio,
            min_nucleus_distance_seconds=min_distance,
        )
        syllable_rate = float(len(syllable_peaks) / speech_active_seconds)
        syllables_per_minute = syllable_rate * 60.0

    return PaceAnalysis(
        sample_rate=sample_rate,
        speech_active_seconds=speech_active_seconds,
        estimated_syllable_count=int(len(syllable_peaks)),
        syllable_rate_per_second=syllable_rate,
        syllables_per_minute=syllables_per_minute,
        label=pace_label(syllable_rate, config=config),
        frame_times=frame_times,
        envelope_rms=envelope,
        speech_frame_mask=speech_mask,
        syllable_peak_times=syllable_peaks,
        source_segment_count=len(segments),
        config_version=config.version,
    )
