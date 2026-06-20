"""Tests for the deterministic synthetic audio generators (Phase 2)."""

from __future__ import annotations

import numpy as np
import pytest

from vocal_intel import synthetic
from vocal_intel.ingest import inspect_audio

SR = synthetic.DEFAULT_SAMPLE_RATE


def _dominant_frequency(signal: np.ndarray, sample_rate: int) -> float:
    spectrum = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / sample_rate)
    return float(freqs[int(np.argmax(spectrum))])


def test_silence_is_zeros_with_known_length():
    s = synthetic.silence(0.5, SR)
    assert s.dtype == np.float32
    assert len(s) == int(round(0.5 * SR))
    assert np.count_nonzero(s) == 0


def test_tone_has_expected_length_amplitude_and_frequency():
    freq, amp, dur = 440.0, 0.5, 1.0
    sig = synthetic.tone(freq, dur, SR, amplitude=amp)
    assert sig.dtype == np.float32
    assert len(sig) == int(round(dur * SR))
    peak = float(np.max(np.abs(sig)))
    assert peak <= amp + 1e-6
    assert peak >= amp * 0.99  # a dense sine reaches close to its peak
    assert abs(_dominant_frequency(sig, SR) - freq) <= 1.0


def test_quiet_is_softer_than_loud():
    quiet = synthetic.quiet_tone(duration_seconds=0.5)
    loud = synthetic.loud_tone(duration_seconds=0.5)
    assert float(np.max(np.abs(quiet))) < float(np.max(np.abs(loud)))
    quiet_rms = float(np.sqrt(np.mean(quiet.astype(np.float64) ** 2)))
    loud_rms = float(np.sqrt(np.mean(loud.astype(np.float64) ** 2)))
    assert loud_rms > quiet_rms


def test_pause_gap_has_known_silent_region():
    fixture = synthetic.pause_gap(tone_seconds=0.5, gap_seconds=0.4, sample_rate=SR)
    assert np.isclose(fixture.gap_start_seconds, 0.5)
    assert np.isclose(fixture.gap_end_seconds, 0.9)
    assert np.isclose(fixture.duration_seconds, 1.4)

    start = int(round(fixture.gap_start_seconds * SR))
    end = int(round(fixture.gap_end_seconds * SR))
    assert np.count_nonzero(fixture.samples[start:end]) == 0  # gap is silent
    assert np.max(np.abs(fixture.samples[:start])) > 0  # tone before
    assert np.max(np.abs(fixture.samples[end:])) > 0  # tone after


def test_generators_are_deterministic():
    a = synthetic.tone(330.0, 0.3, SR, amplitude=0.4)
    b = synthetic.tone(330.0, 0.3, SR, amplitude=0.4)
    assert np.array_equal(a, b)


def test_invalid_arguments_raise():
    with pytest.raises(ValueError):
        synthetic.tone(0.0, 1.0, SR)
    with pytest.raises(ValueError):
        synthetic.tone(220.0, 1.0, SR, amplitude=1.5)
    with pytest.raises(ValueError):
        synthetic.silence(-1.0, SR)


def test_write_wav_is_readable_by_ingestion(tmp_path):
    sig = synthetic.tone(220.0, 0.5, SR, amplitude=0.5)
    path = synthetic.write_wav(tmp_path / "tone.wav", sig, SR)

    meta = inspect_audio(path)
    assert meta.sample_rate == SR
    assert meta.channels == 1
    assert meta.frames == len(sig)
    assert np.isclose(meta.duration_seconds, 0.5, atol=1e-3)
    assert (meta.format or "").upper() == "WAV"
