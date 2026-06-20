"""Loudness and energy analysis.

Computes frame-level RMS energy, peak amplitude, and loudness summary
statistics, and assigns a provisional ``quiet`` / ``normal`` / ``loud`` label.

Absolute level is preserved: this module never normalises the input, so loudness
features remain meaningful. The qualitative dBFS thresholds below are
PROVISIONAL placeholders (chosen against simple synthetic tones) and depend on
capture conditions; they are scheduled to be replaced by data-driven, versioned
calibration in a later phase. For a comparison that does not depend on absolute
thresholds, use :func:`compare_loudness`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

DEFAULT_FRAME_MS = 25.0
DEFAULT_HOP_MS = 10.0
SILENCE_FLOOR_DBFS = -120.0

# Provisional dBFS thresholds (full-scale reference = 1.0). See module docstring.
QUIET_DBFS_MAX = -25.0
LOUD_DBFS_MIN = -15.0


class LoudnessError(ValueError):
    """Raised for invalid input to loudness analysis."""


def _as_mono(samples) -> np.ndarray:
    arr = np.asarray(samples, dtype=np.float64)
    if arr.ndim != 1:
        raise LoudnessError("samples must be a 1-D (mono) array")
    if arr.size == 0:
        raise LoudnessError("samples must not be empty")
    return arr


def rms(samples) -> float:
    """Root-mean-square energy of the whole signal."""
    arr = _as_mono(samples)
    return float(np.sqrt(np.mean(arr ** 2)))


def peak(samples) -> float:
    """Peak absolute amplitude of the whole signal."""
    arr = _as_mono(samples)
    return float(np.max(np.abs(arr)))


def to_dbfs(amplitude: float) -> float:
    """Convert a linear amplitude to dBFS (full-scale reference = 1.0)."""
    amp = float(amplitude)
    if amp <= 0.0:
        return SILENCE_FLOOR_DBFS
    return max(20.0 * math.log10(amp), SILENCE_FLOOR_DBFS)


def loudness_label(rms_value: float) -> str:
    """Map an RMS value to a provisional quiet / normal / loud label."""
    db = to_dbfs(rms_value)
    if db < QUIET_DBFS_MAX:
        return "quiet"
    if db < LOUD_DBFS_MIN:
        return "normal"
    return "loud"


def frame_rms(samples, frame_length: int, hop_length: int) -> np.ndarray:
    """Return per-frame RMS energy (loudness over time)."""
    arr = _as_mono(samples)
    if frame_length <= 0 or hop_length <= 0:
        raise LoudnessError("frame_length and hop_length must be positive")
    if arr.size < frame_length:
        return np.array([float(np.sqrt(np.mean(arr ** 2)))], dtype=np.float64)
    windows = np.lib.stride_tricks.sliding_window_view(arr, frame_length)[::hop_length]
    return np.sqrt(np.mean(windows ** 2, axis=1)).astype(np.float64)


def compare_loudness(samples_a, samples_b) -> dict:
    """Relative loudness comparison that does not depend on absolute thresholds."""
    a = rms(samples_a)
    b = rms(samples_b)
    if a > b:
        louder = "a"
    elif b > a:
        louder = "b"
    else:
        louder = "equal"
    return {"rms_a": a, "rms_b": b, "louder": louder}


@dataclass(frozen=True, eq=False)
class LoudnessSection:
    """A contiguous run of frames sharing one loudness label."""

    start_seconds: float
    end_seconds: float
    label: str


@dataclass(frozen=True, eq=False)
class LoudnessAnalysis:
    """Summary of loudness and energy for one signal."""

    sample_rate: int
    rms: float
    peak: float
    rms_dbfs: float
    peak_dbfs: float
    label: str
    frame_times: np.ndarray
    frame_rms: np.ndarray
    sections: list


def _group_sections(labels, frame_times, total_duration) -> list:
    sections: list = []
    if not labels:
        return sections
    start = 0
    for i in range(1, len(labels)):
        if labels[i] != labels[start]:
            sections.append(
                LoudnessSection(float(frame_times[start]), float(frame_times[i]), labels[start])
            )
            start = i
    sections.append(
        LoudnessSection(float(frame_times[start]), float(total_duration), labels[start])
    )
    return sections


def analyze_loudness(
    samples,
    sample_rate: int,
    frame_ms: float = DEFAULT_FRAME_MS,
    hop_ms: float = DEFAULT_HOP_MS,
) -> LoudnessAnalysis:
    """Analyse loudness and energy without modifying the input level."""
    arr = _as_mono(samples)
    if sample_rate <= 0:
        raise LoudnessError("sample_rate must be positive")
    frame_length = max(1, int(round(frame_ms / 1000.0 * sample_rate)))
    hop_length = max(1, int(round(hop_ms / 1000.0 * sample_rate)))

    overall_rms = float(np.sqrt(np.mean(arr ** 2)))
    overall_peak = float(np.max(np.abs(arr)))
    per_frame = frame_rms(arr, frame_length, hop_length)
    frame_times = (np.arange(len(per_frame)) * hop_length / sample_rate).astype(np.float64)

    frame_labels = [loudness_label(value) for value in per_frame]
    total_duration = arr.size / sample_rate
    sections = _group_sections(frame_labels, frame_times, total_duration)

    return LoudnessAnalysis(
        sample_rate=int(sample_rate),
        rms=overall_rms,
        peak=overall_peak,
        rms_dbfs=to_dbfs(overall_rms),
        peak_dbfs=to_dbfs(overall_peak),
        label=loudness_label(overall_rms),
        frame_times=frame_times,
        frame_rms=per_frame,
        sections=sections,
    )
