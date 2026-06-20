"""Tests for audio preprocessing and canonicalisation (Phase 3).

Uses the Phase 2 synthetic fixtures; no real or committed audio.
"""

from __future__ import annotations

import numpy as np
import pytest

from vocal_intel import synthetic
from vocal_intel.ingest import AudioFileNotFoundError, UnreadableAudioError
from vocal_intel.preprocess import (
    DEFAULT_TARGET_SAMPLE_RATE,
    CanonicalAudio,
    DurationGuardWarning,
    canonicalize,
    load_canonical,
    peak_normalize,
    remove_dc_offset,
    resample,
    to_mono,
)

TARGET = DEFAULT_TARGET_SAMPLE_RATE


def _dominant_frequency(signal: np.ndarray, sample_rate: int) -> float:
    spectrum = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / sample_rate)
    return float(freqs[int(np.argmax(spectrum))])


def test_to_mono_averages_channels():
    left = synthetic.tone(220.0, 0.2, 16000, amplitude=0.5)
    right = synthetic.tone(440.0, 0.2, 16000, amplitude=0.5)
    stereo = np.stack([left, right], axis=1)  # (frames, channels)

    mono = to_mono(stereo)

    assert mono.ndim == 1
    assert len(mono) == len(left)
    assert np.allclose(mono, (left + right) / 2.0, atol=1e-6)


def test_to_mono_passes_through_mono():
    sig = synthetic.tone(220.0, 0.1, 16000)
    assert np.array_equal(to_mono(sig), sig)


def test_remove_dc_offset_centres_signal():
    sig = synthetic.tone(220.0, 0.5, 16000, amplitude=0.5) + 0.3
    centred = remove_dc_offset(sig)
    assert abs(float(np.mean(centred))) < 1e-6


def test_resample_changes_length_and_preserves_frequency():
    sig = synthetic.tone(220.0, 0.5, 16000, amplitude=0.5)
    out = resample(sig, 16000, 8000)
    assert len(out) == 4000
    assert abs(_dominant_frequency(out, 8000) - 220.0) <= 2.0


def test_resample_noop_when_rates_equal():
    sig = synthetic.tone(220.0, 0.2, 16000)
    assert np.array_equal(resample(sig, 16000, 16000), sig)


def test_peak_normalize_scales_to_target():
    sig = synthetic.tone(220.0, 0.2, 16000, amplitude=0.2)
    out = peak_normalize(sig, target_peak=0.9)
    assert np.isclose(float(np.max(np.abs(out))), 0.9, atol=1e-3)


def test_peak_normalize_leaves_silence_unchanged():
    silent = synthetic.silence(0.2, 16000)
    assert np.array_equal(peak_normalize(silent), silent)


def test_same_signal_two_sample_rates_canonicalise_equivalently():
    native = synthetic.tone(220.0, 0.5, TARGET, amplitude=0.5)
    high = synthetic.tone(220.0, 0.5, 48000, amplitude=0.5)

    canon_native = canonicalize(native, TARGET)
    canon_high = canonicalize(high, 48000)

    assert canon_native.sample_rate == canon_high.sample_rate == TARGET
    assert len(canon_native.samples) == len(canon_high.samples)
    assert abs(
        _dominant_frequency(canon_native.samples, TARGET)
        - _dominant_frequency(canon_high.samples, TARGET)
    ) <= 1.0
    corr = float(np.corrcoef(canon_native.samples, canon_high.samples)[0, 1])
    assert corr > 0.99


def test_two_gains_equivalent_when_peak_normalised():
    soft = synthetic.tone(220.0, 0.4, 16000, amplitude=0.2)
    loud = synthetic.tone(220.0, 0.4, 16000, amplitude=0.8)

    canon_soft = canonicalize(soft, 16000, normalize_peak=True)
    canon_loud = canonicalize(loud, 16000, normalize_peak=True)

    assert np.allclose(canon_soft.samples, canon_loud.samples, atol=1e-3)


def test_duration_guard_warns_above_ceiling():
    sig = synthetic.tone(220.0, 1.0, 16000)
    with pytest.warns(DurationGuardWarning):
        canonicalize(sig, 16000, max_seconds=0.1)


def test_duration_guard_silent_below_ceiling(recwarn):
    sig = synthetic.tone(220.0, 0.2, 16000)
    canonicalize(sig, 16000, max_seconds=10.0)
    assert not any(isinstance(w.message, DurationGuardWarning) for w in recwarn.list)


def test_load_canonical_reads_synthetic_wav(tmp_path):
    sig = synthetic.tone(220.0, 0.5, 48000, amplitude=0.5)
    path = synthetic.write_wav(tmp_path / "tone.wav", sig, 48000)

    canon = load_canonical(path, target_sr=16000)

    assert isinstance(canon, CanonicalAudio)
    assert canon.sample_rate == 16000
    assert canon.samples.ndim == 1
    assert np.isclose(canon.duration_seconds, 0.5, atol=1e-3)


def test_load_canonical_missing_file_raises(tmp_path):
    with pytest.raises(AudioFileNotFoundError):
        load_canonical(tmp_path / "nope.wav")


def test_load_canonical_corrupt_file_raises(tmp_path):
    bad = tmp_path / "broken.wav"
    bad.write_bytes(b"not audio")
    with pytest.raises(UnreadableAudioError):
        load_canonical(bad)
