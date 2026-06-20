"""Tests for loudness and energy analysis (Phase 5).

Uses the Phase 2 synthetic fixtures. Numeric tolerances are documented inline:
the RMS of a sine of amplitude A is A / sqrt(2), matched to within 1e-3.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from vocal_intel import synthetic
from vocal_intel.loudness import (
    LoudnessAnalysis,
    LoudnessError,
    analyze_loudness,
    compare_loudness,
    frame_rms,
    loudness_label,
    peak,
    rms,
    to_dbfs,
)
from vocal_intel.preprocess import canonicalize

SR = 16000


def test_rms_and_peak_of_known_tone():
    sig = synthetic.tone(220.0, 0.5, SR, amplitude=0.5)
    assert math.isclose(rms(sig), 0.5 / np.sqrt(2), rel_tol=1e-2)
    assert math.isclose(peak(sig), 0.5, abs_tol=1e-3)


def test_quiet_is_lower_energy_than_loud():
    quiet = synthetic.quiet_tone(duration_seconds=0.5)
    loud = synthetic.loud_tone(duration_seconds=0.5)
    assert rms(quiet) < rms(loud)
    assert peak(quiet) < peak(loud)


def test_quiet_and_loud_labels():
    assert loudness_label(rms(synthetic.quiet_tone(duration_seconds=0.5))) == "quiet"
    assert loudness_label(rms(synthetic.loud_tone(duration_seconds=0.5))) == "loud"


def test_normal_label_for_mid_amplitude():
    sig = synthetic.tone(220.0, 0.5, SR, amplitude=0.15)
    assert loudness_label(rms(sig)) == "normal"


def test_quiet_rms_within_documented_tolerance():
    quiet = synthetic.quiet_tone(duration_seconds=0.5)
    expected = 0.05 / np.sqrt(2)  # amplitude 0.05
    assert abs(rms(quiet) - expected) < 1e-3


def test_loud_rms_within_documented_tolerance():
    loud = synthetic.loud_tone(duration_seconds=0.5)
    expected = 0.8 / np.sqrt(2)  # amplitude 0.8
    assert abs(rms(loud) - expected) < 1e-3


def test_to_dbfs_silence_and_full_scale():
    assert to_dbfs(0.0) == pytest.approx(-120.0)
    assert to_dbfs(1.0) == pytest.approx(0.0, abs=1e-6)


def test_frame_rms_shape_and_steady_values():
    sig = synthetic.tone(220.0, 0.5, SR, amplitude=0.5)
    fr = frame_rms(sig, frame_length=400, hop_length=160)
    assert fr.ndim == 1
    assert len(fr) > 1
    assert np.all(np.abs(fr - 0.5 / np.sqrt(2)) < 5e-2)


def test_compare_loudness_is_relative():
    quiet = synthetic.quiet_tone(duration_seconds=0.3)
    loud = synthetic.loud_tone(duration_seconds=0.3)
    result = compare_loudness(quiet, loud)
    assert result["louder"] == "b"
    assert result["rms_b"] > result["rms_a"]


def test_analyze_loudness_summary():
    loud = synthetic.loud_tone(duration_seconds=0.5)
    analysis = analyze_loudness(loud, SR)
    assert isinstance(analysis, LoudnessAnalysis)
    assert analysis.label == "loud"
    assert analysis.peak <= 1.0
    assert analysis.rms_dbfs < 0.0
    assert len(analysis.frame_rms) == len(analysis.frame_times)
    assert len(analysis.sections) >= 1


def test_analyze_detects_quiet_and_loud_sections():
    quiet = synthetic.tone(220.0, 0.4, SR, amplitude=0.05)
    loud = synthetic.tone(220.0, 0.4, SR, amplitude=0.8)
    signal = np.concatenate([quiet, loud]).astype(np.float32)
    analysis = analyze_loudness(signal, SR)
    labels = {section.label for section in analysis.sections}
    assert "quiet" in labels
    assert "loud" in labels


def test_analyze_on_canonicalised_audio_preserves_level():
    loud = synthetic.loud_tone(duration_seconds=0.5)
    canon = canonicalize(loud, SR)  # default: no peak normalisation
    analysis = analyze_loudness(canon.samples, canon.sample_rate)
    assert analysis.label == "loud"


def test_invalid_input_raises():
    with pytest.raises(LoudnessError):
        rms(np.zeros((10, 2)))  # not mono
    with pytest.raises(LoudnessError):
        rms(np.array([], dtype=np.float32))  # empty
    with pytest.raises(LoudnessError):
        analyze_loudness(synthetic.tone(220.0, 0.1, SR), 0)  # bad sample rate
    with pytest.raises(LoudnessError):
        frame_rms(synthetic.tone(220.0, 0.1, SR), 0, 160)  # bad frame length
