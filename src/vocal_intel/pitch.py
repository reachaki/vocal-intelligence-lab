"""Pitch contour extraction with explicit unvoiced-frame handling.

The estimator is intentionally dependency-light for this phase. It uses
frame-level autocorrelation over a documented fundamental-frequency search
range, then reports voiced frames, a pitch contour, voiced-only stability, a
flat / animated delivery label, and a rising / falling / stable trend label.

The method is suitable for deterministic synthetic validation. Real speech
needs the manual validation protocol, and the provisional thresholds below are
scheduled to move into the versioned configuration in a later phase.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

DEFAULT_FRAME_MS = 40.0
DEFAULT_HOP_MS = 10.0
DEFAULT_F0_MIN_HZ = 75.0
DEFAULT_F0_MAX_HZ = 400.0
DEFAULT_VOICING_CLARITY = 0.30
DEFAULT_MIN_RMS = 1e-4

FLAT_STABILITY_MAX_CENTS = 50.0
TREND_MIN_CHANGE_HZ = 10.0
TREND_MIN_CHANGE_RATIO = 0.05

FLAT_DELIVERY = "flat"
ANIMATED_DELIVERY = "animated"
UNKNOWN_DELIVERY = "unknown"

RISING_TREND = "rising"
FALLING_TREND = "falling"
STABLE_TREND = "stable"
UNKNOWN_TREND = "unknown"


class PitchError(ValueError):
    """Raised for invalid input to pitch analysis."""


@dataclass(frozen=True, eq=False)
class PitchAnalysis:
    """Pitch contour and voiced-frame summary."""

    sample_rate: int
    f0_min_hz: float
    f0_max_hz: float
    frame_times: np.ndarray
    frequencies_hz: np.ndarray
    voiced_frames: np.ndarray
    frame_clarity: np.ndarray
    voiced_fraction: float
    median_frequency_hz: float | None
    mean_frequency_hz: float | None
    pitch_stability_cents: float | None
    delivery_label: str
    trend_label: str


def _as_mono(samples) -> np.ndarray:
    arr = np.asarray(samples, dtype=np.float64)
    if arr.ndim != 1:
        raise PitchError("samples must be a 1-D (mono) array")
    if arr.size == 0:
        raise PitchError("samples must not be empty")
    return arr


def _positive_finite(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise PitchError(f"{name} must be positive and finite")
    return number


def _validate_search_range(f0_min_hz: float, f0_max_hz: float, sample_rate: int) -> tuple[float, float]:
    f0_min = _positive_finite(f0_min_hz, "f0_min_hz")
    f0_max = _positive_finite(f0_max_hz, "f0_max_hz")
    if not f0_min < f0_max:
        raise PitchError("f0_min_hz must be less than f0_max_hz")
    if f0_max >= sample_rate / 2:
        raise PitchError("f0_max_hz must be below the Nyquist frequency")
    return f0_min, f0_max


def _frame_starts(n_samples: int, frame_length: int, hop_length: int) -> np.ndarray:
    if n_samples <= frame_length:
        return np.array([0], dtype=np.int64)
    return np.arange(0, n_samples - frame_length + 1, hop_length, dtype=np.int64)


def _parabolic_lag(correlation: np.ndarray, lag: int) -> float:
    if lag <= 0 or lag >= len(correlation) - 1:
        return float(lag)
    left = float(correlation[lag - 1])
    centre = float(correlation[lag])
    right = float(correlation[lag + 1])
    denominator = left - (2.0 * centre) + right
    if denominator == 0.0:
        return float(lag)
    shift = 0.5 * (left - right) / denominator
    if not math.isfinite(shift) or abs(shift) > 1.0:
        return float(lag)
    return float(lag) + shift


def _estimate_frame_pitch(
    frame: np.ndarray,
    sample_rate: int,
    *,
    min_lag: int,
    max_lag: int,
    min_rms: float,
    voicing_clarity: float,
) -> tuple[float, bool, float]:
    centred = frame.astype(np.float64) - float(np.mean(frame))
    rms = float(np.sqrt(np.mean(centred ** 2))) if centred.size else 0.0
    if rms < min_rms:
        return math.nan, False, 0.0

    window = np.hanning(centred.size)
    windowed = centred * window
    correlation = np.correlate(windowed, windowed, mode="full")[centred.size - 1 :]
    zero_lag = float(correlation[0]) if correlation.size else 0.0
    if zero_lag <= 0.0:
        return math.nan, False, 0.0

    usable_max_lag = min(max_lag, len(correlation) - 1)
    if min_lag > usable_max_lag:
        return math.nan, False, 0.0

    search = correlation[min_lag : usable_max_lag + 1]
    best_lag = int(np.argmax(search)) + min_lag
    clarity = float(correlation[best_lag] / zero_lag)
    if clarity < voicing_clarity:
        return math.nan, False, clarity

    refined_lag = _parabolic_lag(correlation, best_lag)
    if refined_lag <= 0.0:
        return math.nan, False, clarity
    return float(sample_rate / refined_lag), True, clarity


def _pitch_stability_cents(frequencies: np.ndarray, median_frequency: float) -> float:
    cents = 1200.0 * np.log2(frequencies / median_frequency)
    return float(np.std(cents))


def _delivery_label(stability_cents: float | None) -> str:
    if stability_cents is None:
        return UNKNOWN_DELIVERY
    if stability_cents <= FLAT_STABILITY_MAX_CENTS:
        return FLAT_DELIVERY
    return ANIMATED_DELIVERY


def _trend_label(times: np.ndarray, frequencies: np.ndarray, median_frequency: float | None) -> str:
    if median_frequency is None or len(frequencies) < 2:
        return UNKNOWN_TREND
    span = float(times[-1] - times[0])
    if span <= 0.0:
        return UNKNOWN_TREND

    centred_times = times - float(np.mean(times))
    denominator = float(np.sum(centred_times ** 2))
    if denominator == 0.0:
        return UNKNOWN_TREND
    slope = float(np.sum(centred_times * (frequencies - float(np.mean(frequencies)))) / denominator)
    estimated_change = slope * span
    threshold = max(TREND_MIN_CHANGE_HZ, TREND_MIN_CHANGE_RATIO * median_frequency)

    if estimated_change > threshold:
        return RISING_TREND
    if estimated_change < -threshold:
        return FALLING_TREND
    return STABLE_TREND


def analyze_pitch(
    samples,
    sample_rate: int,
    *,
    frame_ms: float = DEFAULT_FRAME_MS,
    hop_ms: float = DEFAULT_HOP_MS,
    f0_min_hz: float = DEFAULT_F0_MIN_HZ,
    f0_max_hz: float = DEFAULT_F0_MAX_HZ,
    min_rms: float = DEFAULT_MIN_RMS,
    voicing_clarity: float = DEFAULT_VOICING_CLARITY,
) -> PitchAnalysis:
    """Estimate a pitch contour from mono audio."""
    arr = _as_mono(samples)
    if sample_rate <= 0:
        raise PitchError("sample_rate must be positive")
    frame_duration = _positive_finite(frame_ms, "frame_ms")
    hop_duration = _positive_finite(hop_ms, "hop_ms")
    minimum_rms = float(min_rms)
    if not math.isfinite(minimum_rms) or minimum_rms < 0.0:
        raise PitchError("min_rms must be finite and non-negative")
    clarity_threshold = float(voicing_clarity)
    if not 0.0 <= clarity_threshold <= 1.0:
        raise PitchError("voicing_clarity must be within [0.0, 1.0]")
    f0_min, f0_max = _validate_search_range(f0_min_hz, f0_max_hz, sample_rate)

    frame_length = max(1, int(round(frame_duration / 1000.0 * sample_rate)))
    hop_length = max(1, int(round(hop_duration / 1000.0 * sample_rate)))
    starts = _frame_starts(arr.size, frame_length, hop_length)
    frame_times = (starts / sample_rate).astype(np.float64)

    min_lag = max(1, int(math.floor(sample_rate / f0_max)))
    max_lag = max(min_lag, int(math.ceil(sample_rate / f0_min)))
    frequencies = np.full(len(starts), math.nan, dtype=np.float64)
    voiced = np.zeros(len(starts), dtype=bool)
    clarity = np.zeros(len(starts), dtype=np.float64)

    for index, start in enumerate(starts):
        frame = arr[start : start + frame_length]
        frequency, is_voiced, frame_clarity = _estimate_frame_pitch(
            frame,
            sample_rate,
            min_lag=min_lag,
            max_lag=max_lag,
            min_rms=minimum_rms,
            voicing_clarity=clarity_threshold,
        )
        frequencies[index] = frequency
        voiced[index] = is_voiced
        clarity[index] = frame_clarity

    voiced_frequencies = frequencies[voiced]
    voiced_times = frame_times[voiced]
    voiced_fraction = float(np.count_nonzero(voiced) / len(voiced)) if len(voiced) else 0.0
    median_frequency = float(np.median(voiced_frequencies)) if voiced_frequencies.size else None
    mean_frequency = float(np.mean(voiced_frequencies)) if voiced_frequencies.size else None
    stability = (
        _pitch_stability_cents(voiced_frequencies, median_frequency)
        if median_frequency is not None and voiced_frequencies.size >= 2
        else None
    )

    return PitchAnalysis(
        sample_rate=int(sample_rate),
        f0_min_hz=f0_min,
        f0_max_hz=f0_max,
        frame_times=frame_times,
        frequencies_hz=frequencies,
        voiced_frames=voiced,
        frame_clarity=clarity,
        voiced_fraction=voiced_fraction,
        median_frequency_hz=median_frequency,
        mean_frequency_hz=mean_frequency,
        pitch_stability_cents=stability,
        delivery_label=_delivery_label(stability),
        trend_label=_trend_label(voiced_times, voiced_frequencies, median_frequency),
    )
