"""Tests for pitch analysis (Phase 8).

Known synthetic tones are checked within a small frequency tolerance. Synthetic
sweeps validate trend direction only; real expressive speech remains part of the
manual real-audio protocol.
"""

from __future__ import annotations

import numpy as np
import pytest

from vocal_intel import synthetic
from vocal_intel.pitch import (
    ANIMATED_DELIVERY,
    FALLING_TREND,
    FLAT_DELIVERY,
    RISING_TREND,
    STABLE_TREND,
    UNKNOWN_DELIVERY,
    UNKNOWN_TREND,
    PitchError,
    analyze_pitch,
)

SR = 16000


def _sweep(start_hz: float, end_hz: float, duration_seconds: float = 1.2) -> np.ndarray:
    n = int(round(duration_seconds * SR))
    frequencies = np.linspace(start_hz, end_hz, n, dtype=np.float64)
    phase = 2.0 * np.pi * np.cumsum(frequencies) / SR
    return (0.5 * np.sin(phase)).astype(np.float32)


def test_known_tone_frequency_is_estimated_within_tolerance():
    analysis = analyze_pitch(synthetic.tone(220.0, 1.0, SR, amplitude=0.5), SR)

    assert analysis.sample_rate == SR
    assert analysis.f0_min_hz == 75.0
    assert analysis.f0_max_hz == 400.0
    assert analysis.voiced_fraction > 0.95
    assert analysis.median_frequency_hz == pytest.approx(220.0, abs=2.0)
    assert analysis.mean_frequency_hz == pytest.approx(220.0, abs=2.0)
    assert analysis.pitch_stability_cents is not None
    assert analysis.pitch_stability_cents < 20.0
    assert analysis.delivery_label == FLAT_DELIVERY
    assert analysis.trend_label == STABLE_TREND
    assert np.all(np.isfinite(analysis.frequencies_hz[analysis.voiced_frames]))
    assert len(analysis.frame_times) == len(analysis.frequencies_hz) == len(analysis.voiced_frames)


def test_silence_is_explicitly_unvoiced():
    analysis = analyze_pitch(synthetic.silence(0.5, SR), SR)

    assert not np.any(analysis.voiced_frames)
    assert np.all(np.isnan(analysis.frequencies_hz))
    assert analysis.voiced_fraction == 0.0
    assert analysis.median_frequency_hz is None
    assert analysis.mean_frequency_hz is None
    assert analysis.pitch_stability_cents is None
    assert analysis.delivery_label == UNKNOWN_DELIVERY
    assert analysis.trend_label == UNKNOWN_TREND


def test_tone_surrounded_by_silence_has_voiced_and_unvoiced_frames():
    signal = np.concatenate(
        [
            synthetic.silence(0.2, SR),
            synthetic.tone(200.0, 0.5, SR, amplitude=0.5),
            synthetic.silence(0.2, SR),
        ]
    )
    analysis = analyze_pitch(signal, SR)

    assert not analysis.voiced_frames[0]
    assert not analysis.voiced_frames[-1]
    assert np.any(analysis.voiced_frames)
    assert np.any(~analysis.voiced_frames)
    assert np.all(np.isnan(analysis.frequencies_hz[~analysis.voiced_frames]))
    assert analysis.median_frequency_hz == pytest.approx(200.0, abs=2.0)


def test_rising_and_falling_sweeps_get_trend_labels():
    rising = analyze_pitch(_sweep(170.0, 270.0), SR)
    falling = analyze_pitch(_sweep(270.0, 170.0), SR)

    assert rising.trend_label == RISING_TREND
    assert falling.trend_label == FALLING_TREND
    assert rising.delivery_label == ANIMATED_DELIVERY
    assert falling.delivery_label == ANIMATED_DELIVERY
    assert rising.pitch_stability_cents is not None
    assert rising.pitch_stability_cents > 50.0


def test_custom_f0_search_range_is_exposed_and_used():
    analysis = analyze_pitch(
        synthetic.tone(180.0, 1.0, SR, amplitude=0.5),
        SR,
        f0_min_hz=100.0,
        f0_max_hz=300.0,
    )

    assert analysis.f0_min_hz == 100.0
    assert analysis.f0_max_hz == 300.0
    assert analysis.median_frequency_hz == pytest.approx(180.0, abs=2.0)


def test_invalid_input_raises():
    with pytest.raises(PitchError):
        analyze_pitch(np.zeros((10, 2)), SR)
    with pytest.raises(PitchError):
        analyze_pitch(np.array([], dtype=np.float32), SR)
    with pytest.raises(PitchError):
        analyze_pitch(synthetic.tone(220.0, 0.1, SR), 0)
    with pytest.raises(PitchError):
        analyze_pitch(synthetic.tone(220.0, 0.1, SR), SR, f0_min_hz=300.0, f0_max_hz=100.0)
    with pytest.raises(PitchError):
        analyze_pitch(synthetic.tone(220.0, 0.1, SR), SR, f0_max_hz=SR / 2)
    with pytest.raises(PitchError):
        analyze_pitch(synthetic.tone(220.0, 0.1, SR), SR, frame_ms=0.0)
    with pytest.raises(PitchError):
        analyze_pitch(synthetic.tone(220.0, 0.1, SR), SR, hop_ms=0.0)
    with pytest.raises(PitchError):
        analyze_pitch(synthetic.tone(220.0, 0.1, SR), SR, min_rms=-1.0)
    with pytest.raises(PitchError):
        analyze_pitch(synthetic.tone(220.0, 0.1, SR), SR, voicing_clarity=1.1)
