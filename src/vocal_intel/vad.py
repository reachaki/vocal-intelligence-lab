"""Voice activity detection and noise-floor estimation.

Provides a single shared speech / non-speech segmentation that later phases
(pause detection, pace estimation, the event timeline) consume. The method is
dependency-light: frame-level RMS energy (from the loudness module) is compared
against an adaptive threshold derived from an estimated noise floor, and short
runs are then smoothed away.

The noise floor is estimated from the quietest frames, so input is expected to
contain some ambient / non-speech regions; a uniformly energetic clip has no
quiet reference and is treated as non-speech. Thresholds are sourced from the
versioned threshold configuration and remain provisional until real-sample
calibration.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from vocal_intel.config import DEFAULT_THRESHOLD_CONFIG, ThresholdConfig
from vocal_intel.loudness import frame_rms, to_dbfs

DEFAULT_FRAME_MS = 25.0
DEFAULT_HOP_MS = 10.0
# A frame is speech when it is this many dB above the estimated noise floor.
DEFAULT_THRESHOLD_MARGIN_DB = DEFAULT_THRESHOLD_CONFIG.vad.threshold_margin_db
# Percentile of frame energies used to estimate the ambient noise floor.
NOISE_FLOOR_PERCENTILE = DEFAULT_THRESHOLD_CONFIG.vad.noise_floor_percentile
# Smoothing: shorter runs are removed (speech) or bridged (silence).
DEFAULT_MIN_SPEECH_SECONDS = DEFAULT_THRESHOLD_CONFIG.vad.min_speech_seconds
DEFAULT_MIN_SILENCE_SECONDS = DEFAULT_THRESHOLD_CONFIG.vad.min_silence_seconds

SPEECH = "speech"
NON_SPEECH = "non_speech"


class VadError(ValueError):
    """Raised for invalid input to voice activity detection."""


@dataclass(frozen=True, eq=False)
class Segment:
    """A contiguous speech or non-speech region."""

    start_seconds: float
    end_seconds: float
    label: str

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass(frozen=True, eq=False)
class VadResult:
    """Voice-activity segmentation and the values used to produce it."""

    sample_rate: int
    noise_floor_rms: float
    noise_floor_dbfs: float
    threshold_dbfs: float
    frame_times: np.ndarray
    frame_rms: np.ndarray
    frame_is_speech: np.ndarray
    segments: list
    config_version: str = DEFAULT_THRESHOLD_CONFIG.version


def estimate_noise_floor(
    frame_energies,
    percentile: float | None = None,
    *,
    config: ThresholdConfig = DEFAULT_THRESHOLD_CONFIG,
) -> float:
    """Estimate the ambient noise floor as a low percentile of frame energy."""
    arr = np.asarray(frame_energies, dtype=np.float64)
    if arr.size == 0:
        raise VadError("frame_energies must not be empty")
    pct = config.vad.noise_floor_percentile if percentile is None else float(percentile)
    return float(np.percentile(arr, pct))


def _remove_short_runs(flags: np.ndarray, value: bool, min_len: int) -> np.ndarray:
    out = flags.copy()
    n = len(out)
    i = 0
    while i < n:
        if bool(out[i]) == value:
            j = i
            while j < n and bool(out[j]) == value:
                j += 1
            if (j - i) < min_len:
                out[i:j] = not value
            i = j
        else:
            i += 1
    return out


def _segments_from_flags(flags, frame_times, total_duration) -> list:
    segments: list = []
    n = len(flags)
    if n == 0:
        return segments
    start = 0
    for i in range(1, n):
        if bool(flags[i]) != bool(flags[start]):
            segments.append(
                Segment(
                    float(frame_times[start]),
                    float(frame_times[i]),
                    SPEECH if bool(flags[start]) else NON_SPEECH,
                )
            )
            start = i
    segments.append(
        Segment(
            float(frame_times[start]),
            float(total_duration),
            SPEECH if bool(flags[start]) else NON_SPEECH,
        )
    )
    return segments


def detect_voice_activity(
    samples,
    sample_rate: int,
    *,
    frame_ms: float = DEFAULT_FRAME_MS,
    hop_ms: float = DEFAULT_HOP_MS,
    threshold_margin_db: float | None = None,
    min_speech_seconds: float | None = None,
    min_silence_seconds: float | None = None,
    config: ThresholdConfig = DEFAULT_THRESHOLD_CONFIG,
) -> VadResult:
    """Segment a mono signal into speech and non-speech regions."""
    arr = np.asarray(samples, dtype=np.float64)
    if arr.ndim != 1:
        raise VadError("samples must be a 1-D (mono) array")
    if arr.size == 0:
        raise VadError("samples must not be empty")
    if sample_rate <= 0:
        raise VadError("sample_rate must be positive")

    frame_length = max(1, int(round(frame_ms / 1000.0 * sample_rate)))
    hop_length = max(1, int(round(hop_ms / 1000.0 * sample_rate)))
    hop_seconds = hop_length / sample_rate
    margin_db = config.vad.threshold_margin_db if threshold_margin_db is None else float(threshold_margin_db)
    min_speech = config.vad.min_speech_seconds if min_speech_seconds is None else float(min_speech_seconds)
    min_silence = config.vad.min_silence_seconds if min_silence_seconds is None else float(min_silence_seconds)

    energies = frame_rms(arr, frame_length, hop_length)
    frame_times = (np.arange(len(energies)) * hop_length / sample_rate).astype(np.float64)

    noise_floor_rms = estimate_noise_floor(energies, config=config)
    noise_floor_dbfs = to_dbfs(noise_floor_rms)
    threshold_dbfs = noise_floor_dbfs + margin_db

    frame_dbfs = np.array([to_dbfs(value) for value in energies], dtype=np.float64)
    is_speech = frame_dbfs >= threshold_dbfs

    min_speech_frames = max(1, int(round(min_speech / hop_seconds)))
    min_silence_frames = max(1, int(round(min_silence / hop_seconds)))
    is_speech = _remove_short_runs(is_speech, True, min_speech_frames)
    is_speech = _remove_short_runs(is_speech, False, min_silence_frames)

    total_duration = arr.size / sample_rate
    segments = _segments_from_flags(is_speech, frame_times, total_duration)

    return VadResult(
        config_version=config.version,
        sample_rate=int(sample_rate),
        noise_floor_rms=noise_floor_rms,
        noise_floor_dbfs=noise_floor_dbfs,
        threshold_dbfs=threshold_dbfs,
        frame_times=frame_times,
        frame_rms=energies,
        frame_is_speech=is_speech,
        segments=segments,
    )
