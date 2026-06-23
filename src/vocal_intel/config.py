"""Versioned threshold configuration for vocal feature labels.

Phase 10 centralises the provisional numeric cut-points used by qualitative
feature labels. The values below preserve the earlier phase behaviour while
making threshold changes explicit and versioned.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

CONFIG_VERSION = "phase-10-provisional-v1"


class ThresholdConfigError(ValueError):
    """Raised when threshold configuration values are invalid."""


def _finite(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ThresholdConfigError(f"{name} must be finite")
    return number


def _positive(value: float, name: str) -> float:
    number = _finite(value, name)
    if number <= 0.0:
        raise ThresholdConfigError(f"{name} must be positive")
    return number


def _non_negative(value: float, name: str) -> float:
    number = _finite(value, name)
    if number < 0.0:
        raise ThresholdConfigError(f"{name} must be non-negative")
    return number


@dataclass(frozen=True)
class LoudnessThresholds:
    quiet_dbfs_max: float = -25.0
    loud_dbfs_min: float = -15.0

    def __post_init__(self) -> None:
        quiet_max = _finite(self.quiet_dbfs_max, "loudness.quiet_dbfs_max")
        loud_min = _finite(self.loud_dbfs_min, "loudness.loud_dbfs_min")
        if quiet_max >= loud_min:
            raise ThresholdConfigError("loudness.quiet_dbfs_max must be less than loudness.loud_dbfs_min")


@dataclass(frozen=True)
class VadThresholds:
    noise_floor_percentile: float = 10.0
    threshold_margin_db: float = 8.0
    min_speech_seconds: float = 0.05
    min_silence_seconds: float = 0.05

    def __post_init__(self) -> None:
        percentile = _finite(self.noise_floor_percentile, "vad.noise_floor_percentile")
        if not 0.0 <= percentile <= 100.0:
            raise ThresholdConfigError("vad.noise_floor_percentile must be within [0.0, 100.0]")
        _finite(self.threshold_margin_db, "vad.threshold_margin_db")
        _positive(self.min_speech_seconds, "vad.min_speech_seconds")
        _positive(self.min_silence_seconds, "vad.min_silence_seconds")


@dataclass(frozen=True)
class PauseThresholds:
    min_pause_seconds: float = 0.20
    short_pause_max_seconds: float = 0.50
    medium_pause_max_seconds: float = 1.00

    def __post_init__(self) -> None:
        _non_negative(self.min_pause_seconds, "pauses.min_pause_seconds")
        short_max = _positive(self.short_pause_max_seconds, "pauses.short_pause_max_seconds")
        medium_max = _positive(self.medium_pause_max_seconds, "pauses.medium_pause_max_seconds")
        if short_max >= medium_max:
            raise ThresholdConfigError(
                "pauses.short_pause_max_seconds must be less than pauses.medium_pause_max_seconds"
            )


@dataclass(frozen=True)
class PitchThresholds:
    f0_min_hz: float = 75.0
    f0_max_hz: float = 400.0
    voicing_clarity: float = 0.30
    min_rms: float = 1e-4
    flat_stability_max_cents: float = 50.0
    trend_min_change_hz: float = 10.0
    trend_min_change_ratio: float = 0.05

    def __post_init__(self) -> None:
        f0_min = _positive(self.f0_min_hz, "pitch.f0_min_hz")
        f0_max = _positive(self.f0_max_hz, "pitch.f0_max_hz")
        if f0_min >= f0_max:
            raise ThresholdConfigError("pitch.f0_min_hz must be less than pitch.f0_max_hz")
        clarity = _finite(self.voicing_clarity, "pitch.voicing_clarity")
        if not 0.0 <= clarity <= 1.0:
            raise ThresholdConfigError("pitch.voicing_clarity must be within [0.0, 1.0]")
        _non_negative(self.min_rms, "pitch.min_rms")
        _non_negative(self.flat_stability_max_cents, "pitch.flat_stability_max_cents")
        _non_negative(self.trend_min_change_hz, "pitch.trend_min_change_hz")
        _non_negative(self.trend_min_change_ratio, "pitch.trend_min_change_ratio")


@dataclass(frozen=True)
class PaceThresholds:
    slow_syllable_rate_max: float = 3.0
    fast_syllable_rate_min: float = 5.0
    nucleus_threshold_ratio: float = 0.45
    min_nucleus_distance_seconds: float = 0.12

    def __post_init__(self) -> None:
        slow_max = _non_negative(self.slow_syllable_rate_max, "pace.slow_syllable_rate_max")
        fast_min = _positive(self.fast_syllable_rate_min, "pace.fast_syllable_rate_min")
        if slow_max >= fast_min:
            raise ThresholdConfigError("pace.slow_syllable_rate_max must be less than pace.fast_syllable_rate_min")
        ratio = _finite(self.nucleus_threshold_ratio, "pace.nucleus_threshold_ratio")
        if not 0.0 <= ratio <= 1.0:
            raise ThresholdConfigError("pace.nucleus_threshold_ratio must be within [0.0, 1.0]")
        _positive(self.min_nucleus_distance_seconds, "pace.min_nucleus_distance_seconds")


@dataclass(frozen=True)
class ThresholdConfig:
    version: str = CONFIG_VERSION
    loudness: LoudnessThresholds = LoudnessThresholds()
    vad: VadThresholds = VadThresholds()
    pauses: PauseThresholds = PauseThresholds()
    pitch: PitchThresholds = PitchThresholds()
    pace: PaceThresholds = PaceThresholds()

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ThresholdConfigError("config version must not be empty")


DEFAULT_THRESHOLD_CONFIG = ThresholdConfig()


__all__ = [
    "CONFIG_VERSION",
    "DEFAULT_THRESHOLD_CONFIG",
    "LoudnessThresholds",
    "PaceThresholds",
    "PauseThresholds",
    "PitchThresholds",
    "ThresholdConfig",
    "ThresholdConfigError",
    "VadThresholds",
]
