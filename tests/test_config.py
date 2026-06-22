"""Tests for versioned threshold configuration (Phase 10)."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from vocal_intel import synthetic
from vocal_intel.config import DEFAULT_THRESHOLD_CONFIG, ThresholdConfigError
from vocal_intel.loudness import analyze_loudness, loudness_label, rms
from vocal_intel.pace import FAST_PACE, NORMAL_PACE, analyze_pace, pace_label
from vocal_intel.pauses import LONG_PAUSE, MEDIUM_PAUSE, analyze_pauses, pause_label
from vocal_intel.pitch import ANIMATED_DELIVERY, FLAT_DELIVERY, RISING_TREND, STABLE_TREND, analyze_pitch
from vocal_intel.vad import NON_SPEECH, SPEECH, Segment, VadResult, detect_voice_activity

SR = 16000


def _speech_fixture() -> np.ndarray:
    return np.concatenate(
        [
            synthetic.silence(0.3, SR),
            synthetic.tone(220.0, 0.4, SR, amplitude=0.5),
            synthetic.silence(0.3, SR),
        ]
    ).astype(np.float32)


def _sweep(start_hz: float, end_hz: float, duration_seconds: float = 1.2) -> np.ndarray:
    n = int(round(duration_seconds * SR))
    frequencies = np.linspace(start_hz, end_hz, n, dtype=np.float64)
    phase = 2.0 * np.pi * np.cumsum(frequencies) / SR
    return (0.5 * np.sin(phase)).astype(np.float32)


def test_default_config_version_is_stamped_into_feature_outputs():
    version = DEFAULT_THRESHOLD_CONFIG.version
    samples = _speech_fixture()
    vad = detect_voice_activity(samples, SR)

    manual_vad = VadResult(
        sample_rate=SR,
        noise_floor_rms=0.0,
        noise_floor_dbfs=-120.0,
        threshold_dbfs=-112.0,
        frame_times=np.array([], dtype=np.float64),
        frame_rms=np.array([], dtype=np.float64),
        frame_is_speech=np.array([], dtype=bool),
        segments=[Segment(0.0, 1.0, NON_SPEECH)],
    )

    assert analyze_loudness(samples, SR).config_version == version
    assert vad.config_version == version
    assert analyze_pauses(vad).config_version == version
    assert analyze_pitch(samples, SR).config_version == version
    assert analyze_pace(synthetic.silence(1.0, SR), manual_vad).config_version == version


def test_config_threshold_edits_change_labels_without_label_code_changes():
    loudness_config = replace(
        DEFAULT_THRESHOLD_CONFIG,
        loudness=replace(DEFAULT_THRESHOLD_CONFIG.loudness, loud_dbfs_min=-20.0),
    )
    mid_rms = rms(synthetic.tone(220.0, 0.5, SR, amplitude=0.15))
    assert loudness_label(mid_rms) == "normal"
    assert loudness_label(mid_rms, config=loudness_config) == "loud"

    pause_config = replace(
        DEFAULT_THRESHOLD_CONFIG,
        pauses=replace(DEFAULT_THRESHOLD_CONFIG.pauses, medium_pause_max_seconds=0.70),
    )
    assert pause_label(0.75) == MEDIUM_PAUSE
    assert pause_label(0.75, config=pause_config) == LONG_PAUSE

    pitch_config = replace(
        DEFAULT_THRESHOLD_CONFIG,
        pitch=replace(
            DEFAULT_THRESHOLD_CONFIG.pitch,
            flat_stability_max_cents=1000.0,
            trend_min_change_hz=200.0,
            trend_min_change_ratio=1.0,
        ),
    )
    default_pitch = analyze_pitch(_sweep(170.0, 270.0), SR)
    custom_pitch = analyze_pitch(_sweep(170.0, 270.0), SR, config=pitch_config)
    assert default_pitch.delivery_label == ANIMATED_DELIVERY
    assert default_pitch.trend_label == RISING_TREND
    assert custom_pitch.delivery_label == FLAT_DELIVERY
    assert custom_pitch.trend_label == STABLE_TREND

    pace_config = replace(
        DEFAULT_THRESHOLD_CONFIG,
        pace=replace(DEFAULT_THRESHOLD_CONFIG.pace, fast_syllable_rate_min=4.0),
    )
    assert pace_label(4.5) == NORMAL_PACE
    assert pace_label(4.5, config=pace_config) == FAST_PACE


def test_vad_thresholds_are_sourced_from_config():
    samples = _speech_fixture()
    default_vad = detect_voice_activity(samples, SR)
    strict_config = replace(
        DEFAULT_THRESHOLD_CONFIG,
        vad=replace(DEFAULT_THRESHOLD_CONFIG.vad, threshold_margin_db=140.0),
    )
    strict_vad = detect_voice_activity(samples, SR, config=strict_config)

    assert any(segment.label == SPEECH for segment in default_vad.segments)
    assert not any(segment.label == SPEECH for segment in strict_vad.segments)
    assert strict_vad.config_version == strict_config.version


def test_invalid_threshold_config_values_raise_clear_errors():
    with np.testing.assert_raises(ThresholdConfigError):
        replace(DEFAULT_THRESHOLD_CONFIG, loudness=replace(DEFAULT_THRESHOLD_CONFIG.loudness, loud_dbfs_min=-30.0))
    with np.testing.assert_raises(ThresholdConfigError):
        replace(DEFAULT_THRESHOLD_CONFIG, pace=replace(DEFAULT_THRESHOLD_CONFIG.pace, fast_syllable_rate_min=2.0))
