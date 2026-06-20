"""Deterministic synthetic audio generators for tests and demos.

These helpers produce small, fully reproducible signals with known properties
(duration, amplitude, frequency, and gap positions) so later feature phases can
be tested without committing real audio. Generators return ``float32`` numpy
arrays in the range ``[-1.0, 1.0]``. The output is deterministic: the same
arguments always produce identical samples.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import soundfile as sf

DEFAULT_SAMPLE_RATE = 16000
DEFAULT_FREQUENCY_HZ = 220.0
QUIET_AMPLITUDE = 0.05
LOUD_AMPLITUDE = 0.8


def _num_samples(duration_seconds: float, sample_rate: int) -> int:
    if duration_seconds < 0:
        raise ValueError("duration_seconds must be non-negative")
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    return int(round(duration_seconds * sample_rate))


def silence(duration_seconds: float, sample_rate: int = DEFAULT_SAMPLE_RATE) -> np.ndarray:
    """Return silence of the given duration as float32 zeros."""
    return np.zeros(_num_samples(duration_seconds, sample_rate), dtype=np.float32)


def tone(
    frequency_hz: float = DEFAULT_FREQUENCY_HZ,
    duration_seconds: float = 1.0,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    amplitude: float = 0.5,
) -> np.ndarray:
    """Return a sine tone with a known frequency and amplitude.

    The signal starts at phase zero so it is fully deterministic.
    """
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be positive")
    if not 0.0 <= amplitude <= 1.0:
        raise ValueError("amplitude must be within [0.0, 1.0]")
    n = _num_samples(duration_seconds, sample_rate)
    t = np.arange(n, dtype=np.float64) / sample_rate
    signal = amplitude * np.sin(2.0 * np.pi * frequency_hz * t)
    return signal.astype(np.float32)


def quiet_tone(
    frequency_hz: float = DEFAULT_FREQUENCY_HZ,
    duration_seconds: float = 1.0,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> np.ndarray:
    """A low-amplitude tone (see ``QUIET_AMPLITUDE``)."""
    return tone(frequency_hz, duration_seconds, sample_rate, amplitude=QUIET_AMPLITUDE)


def loud_tone(
    frequency_hz: float = DEFAULT_FREQUENCY_HZ,
    duration_seconds: float = 1.0,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> np.ndarray:
    """A high-amplitude tone (see ``LOUD_AMPLITUDE``)."""
    return tone(frequency_hz, duration_seconds, sample_rate, amplitude=LOUD_AMPLITUDE)


@dataclass(frozen=True, eq=False)
class PauseGapFixture:
    """A tone-silence-tone signal with a known gap location."""

    samples: np.ndarray
    sample_rate: int
    gap_start_seconds: float
    gap_end_seconds: float

    @property
    def duration_seconds(self) -> float:
        return len(self.samples) / self.sample_rate


def pause_gap(
    tone_seconds: float = 0.5,
    gap_seconds: float = 0.4,
    frequency_hz: float = DEFAULT_FREQUENCY_HZ,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    amplitude: float = 0.5,
) -> PauseGapFixture:
    """Return a tone, a silent gap, then a tone, recording the gap position.

    Useful for later pause/silence detection: the gap boundaries are known
    exactly via ``gap_start_seconds`` and ``gap_end_seconds``.
    """
    first = tone(frequency_hz, tone_seconds, sample_rate, amplitude)
    gap = silence(gap_seconds, sample_rate)
    second = tone(frequency_hz, tone_seconds, sample_rate, amplitude)
    samples = np.concatenate([first, gap, second]).astype(np.float32)
    return PauseGapFixture(
        samples=samples,
        sample_rate=sample_rate,
        gap_start_seconds=len(first) / sample_rate,
        gap_end_seconds=(len(first) + len(gap)) / sample_rate,
    )


def write_wav(path, samples: np.ndarray, sample_rate: int = DEFAULT_SAMPLE_RATE) -> str:
    """Write samples to a 16-bit PCM WAV file and return the path as a string.

    The file can be inspected with the audio ingestion command.
    """
    sf.write(str(path), np.asarray(samples, dtype=np.float32), int(sample_rate), subtype="PCM_16")
    return str(path)
