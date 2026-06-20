"""Audio preprocessing and canonicalisation.

Converts arbitrary input audio into a consistent internal form before feature
extraction: a single (mono) channel, a fixed target sample rate, and the DC
offset removed.

What is normalised:
- channel layout: any number of channels is averaged down to mono
- sample rate: resampled to the target rate (default 16 kHz)
- DC offset: the signal mean is subtracted

What is NOT normalised by default:
- loudness / amplitude: the absolute level is preserved so that later loudness
  features remain meaningful. Peak normalisation is available but opt-in.

Resampling uses linear interpolation, which depends only on numpy. It is
adequate for canonicalisation in this prototype; a higher-quality resampler can
be substituted when the feature-extraction libraries are introduced.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from vocal_intel.ingest import AudioFileNotFoundError, UnreadableAudioError

DEFAULT_TARGET_SAMPLE_RATE = 16000
DEFAULT_MAX_DURATION_SECONDS = 600.0  # 10 minutes; in-memory processing ceiling


class DurationGuardWarning(UserWarning):
    """Emitted when audio exceeds the supported-length ceiling."""


def to_mono(samples: np.ndarray) -> np.ndarray:
    """Average any number of channels down to a single mono channel."""
    arr = np.asarray(samples, dtype=np.float32)
    if arr.ndim == 1:
        return arr
    if arr.ndim == 2:
        # soundfile returns (frames, channels); average across channels.
        return arr.mean(axis=1).astype(np.float32)
    raise ValueError("samples must be a 1-D or 2-D array")


def remove_dc_offset(samples: np.ndarray) -> np.ndarray:
    """Subtract the mean so the signal is centred on zero."""
    arr = np.asarray(samples, dtype=np.float32)
    if arr.size == 0:
        return arr
    return (arr - arr.mean()).astype(np.float32)


def resample(samples: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Resample a mono signal to ``target_sr`` using linear interpolation."""
    if orig_sr <= 0 or target_sr <= 0:
        raise ValueError("sample rates must be positive")
    arr = np.asarray(samples, dtype=np.float32)
    if orig_sr == target_sr or arr.size == 0:
        return arr
    duration = arr.shape[0] / orig_sr
    n_target = int(round(duration * target_sr))
    if n_target <= 0:
        return np.zeros(0, dtype=np.float32)
    orig_times = np.arange(arr.shape[0], dtype=np.float64) / orig_sr
    target_times = np.arange(n_target, dtype=np.float64) / target_sr
    resampled = np.interp(target_times, orig_times, arr.astype(np.float64))
    return resampled.astype(np.float32)


def peak_normalize(samples: np.ndarray, target_peak: float = 0.99) -> np.ndarray:
    """Scale the signal so its peak magnitude equals ``target_peak``.

    This changes the absolute level, so it is opt-in. Silence is returned
    unchanged.
    """
    if not 0.0 < target_peak <= 1.0:
        raise ValueError("target_peak must be within (0.0, 1.0]")
    arr = np.asarray(samples, dtype=np.float32)
    peak = float(np.max(np.abs(arr))) if arr.size else 0.0
    if peak == 0.0:
        return arr
    return (arr * (target_peak / peak)).astype(np.float32)


def check_duration(
    n_samples: int,
    sample_rate: int,
    max_seconds: float = DEFAULT_MAX_DURATION_SECONDS,
) -> float:
    """Return the duration in seconds, warning if it exceeds the ceiling."""
    duration = n_samples / sample_rate if sample_rate else 0.0
    if duration > max_seconds:
        warnings.warn(
            f"Audio duration {duration:.1f}s exceeds the supported ceiling of "
            f"{max_seconds:.0f}s; results may be unreliable.",
            DurationGuardWarning,
            stacklevel=2,
        )
    return duration


@dataclass(frozen=True, eq=False)
class CanonicalAudio:
    """Canonicalised mono audio at a fixed sample rate."""

    samples: np.ndarray
    sample_rate: int

    @property
    def duration_seconds(self) -> float:
        return len(self.samples) / self.sample_rate


def canonicalize(
    samples: np.ndarray,
    orig_sr: int,
    target_sr: int = DEFAULT_TARGET_SAMPLE_RATE,
    *,
    normalize_peak: bool = False,
    max_seconds: float = DEFAULT_MAX_DURATION_SECONDS,
) -> CanonicalAudio:
    """Mono downmix, DC-offset removal, and resample to ``target_sr``.

    Peak normalisation is applied only when ``normalize_peak`` is True. A
    duration-guard warning is emitted for input longer than ``max_seconds``.
    """
    mono = to_mono(samples)
    check_duration(mono.shape[0], orig_sr, max_seconds)
    mono = remove_dc_offset(mono)
    resampled = resample(mono, orig_sr, target_sr)
    if normalize_peak:
        resampled = peak_normalize(resampled)
    return CanonicalAudio(samples=resampled, sample_rate=target_sr)


def load_canonical(
    path,
    target_sr: int = DEFAULT_TARGET_SAMPLE_RATE,
    *,
    normalize_peak: bool = False,
    max_seconds: float = DEFAULT_MAX_DURATION_SECONDS,
) -> CanonicalAudio:
    """Read a local audio file and return canonicalised audio.

    Raises AudioFileNotFoundError for a missing path and UnreadableAudioError
    for an empty, corrupt, or unsupported file.
    """
    p = Path(path)
    if not p.exists():
        raise AudioFileNotFoundError(f"Audio file not found: {p}")
    if not p.is_file():
        raise AudioFileNotFoundError(f"Not a file: {p}")
    try:
        data, orig_sr = sf.read(str(p), dtype="float32", always_2d=False)
    except Exception as exc:  # libsndfile raises a range of errors
        raise UnreadableAudioError(f"Could not read audio file: {p} ({exc})") from exc
    return canonicalize(
        data,
        int(orig_sr),
        target_sr,
        normalize_peak=normalize_peak,
        max_seconds=max_seconds,
    )
