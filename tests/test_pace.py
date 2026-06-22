"""Tests for speech pace estimation (Phase 9).

Synthetic pulse trains stand in for syllable-like energy nuclei. The validation
checks that the estimate follows known pulse rates and normalises by
speech-active time rather than total clip duration.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from vocal_intel import synthetic
from vocal_intel.pace import (
    FAST_PACE,
    NORMAL_PACE,
    SLOW_PACE,
    UNKNOWN_PACE,
    PaceError,
    analyze_pace,
    pace_label,
    speech_active_duration_seconds,
)
from vocal_intel.vad import NON_SPEECH, SPEECH, Segment, VadResult, detect_voice_activity

SR = 16000


def _pulse_train(syllable_count: int, duration_seconds: float, *, baseline: float = 0.02) -> np.ndarray:
    n = int(round(duration_seconds * SR))
    t = np.arange(n, dtype=np.float64) / SR
    period = duration_seconds / syllable_count
    width = min(0.055, period * 0.25)
    envelope = np.full(n, baseline, dtype=np.float64)
    for centre in (np.arange(syllable_count, dtype=np.float64) + 0.5) * period:
        envelope += np.exp(-0.5 * ((t - centre) / width) ** 2)
    envelope = np.clip(envelope, 0.0, 1.0)
    carrier = np.sin(2.0 * np.pi * 220.0 * t)
    return (0.55 * envelope * carrier).astype(np.float32)


def _vad_result(segments: list[Segment]) -> VadResult:
    return VadResult(
        sample_rate=SR,
        noise_floor_rms=0.0,
        noise_floor_dbfs=-120.0,
        threshold_dbfs=-112.0,
        frame_times=np.array([], dtype=np.float64),
        frame_rms=np.array([], dtype=np.float64),
        frame_is_speech=np.array([], dtype=bool),
        segments=segments,
    )


def test_syllable_rate_uses_speech_active_time_not_total_duration():
    first = _pulse_train(4, 1.0)
    gap = synthetic.silence(0.5, SR)
    second = _pulse_train(4, 1.0)
    samples = np.concatenate([first, gap, second])
    vad = _vad_result(
        [
            Segment(0.0, 1.0, SPEECH),
            Segment(1.0, 1.5, NON_SPEECH),
            Segment(1.5, 2.5, SPEECH),
        ]
    )

    analysis = analyze_pace(samples, vad)

    assert analysis.speech_active_seconds == pytest.approx(2.0)
    assert analysis.estimated_syllable_count == 8
    assert analysis.syllable_rate_per_second == pytest.approx(4.0)
    assert analysis.syllables_per_minute == pytest.approx(240.0)
    assert analysis.label == NORMAL_PACE
    assert analysis.source_segment_count == 3
    assert len(analysis.syllable_peak_times) == 8


def test_estimate_tracks_slow_normal_and_fast_pulse_rates():
    cases = [
        (4, 2.0, SLOW_PACE),
        (8, 2.0, NORMAL_PACE),
        (12, 2.0, FAST_PACE),
    ]

    for syllables, seconds, expected_label in cases:
        samples = _pulse_train(syllables, seconds)
        analysis = analyze_pace(samples, _vad_result([Segment(0.0, seconds, SPEECH)]))

        assert analysis.estimated_syllable_count == syllables
        assert analysis.syllable_rate_per_second == pytest.approx(syllables / seconds)
        assert analysis.label == expected_label


def test_pace_can_consume_detected_vad_regions():
    samples = np.concatenate(
        [
            synthetic.silence(0.3, SR),
            _pulse_train(8, 2.0, baseline=0.08),
            synthetic.silence(0.3, SR),
        ]
    )
    vad = detect_voice_activity(samples, SR)

    analysis = analyze_pace(samples, vad)

    assert analysis.speech_active_seconds == pytest.approx(2.0, abs=0.12)
    assert analysis.estimated_syllable_count == 8
    assert analysis.syllable_rate_per_second == pytest.approx(4.0, abs=0.35)
    assert analysis.label == NORMAL_PACE


def test_speech_active_duration_sums_only_speech_segments():
    segments = [
        Segment(0.0, 0.4, NON_SPEECH),
        Segment(0.4, 1.2, SPEECH),
        Segment(1.2, 1.5, NON_SPEECH),
        Segment(1.5, 2.1, SPEECH),
        Segment(2.1, 2.5, NON_SPEECH),
    ]

    assert speech_active_duration_seconds(segments) == pytest.approx(1.4)

    analysis = analyze_pace(np.zeros(int(2.5 * SR), dtype=np.float32), _vad_result(segments))
    assert analysis.speech_active_seconds == pytest.approx(1.4)
    assert analysis.estimated_syllable_count == 0
    assert analysis.syllable_rate_per_second == 0.0
    assert analysis.label == SLOW_PACE


def test_no_speech_yields_unknown_rate_and_label():
    samples = synthetic.silence(1.0, SR)
    analysis = analyze_pace(samples, _vad_result([Segment(0.0, 1.0, NON_SPEECH)]))

    assert analysis.speech_active_seconds == 0.0
    assert analysis.estimated_syllable_count == 0
    assert analysis.syllable_rate_per_second is None
    assert analysis.syllables_per_minute is None
    assert analysis.label == UNKNOWN_PACE
    assert analysis.syllable_peak_times.size == 0


def test_pace_labels_use_provisional_syllable_rate_thresholds():
    assert pace_label(None) == UNKNOWN_PACE
    assert pace_label(2.99) == SLOW_PACE
    assert pace_label(3.0) == NORMAL_PACE
    assert pace_label(5.0) == NORMAL_PACE
    assert pace_label(5.01) == FAST_PACE

    with pytest.raises(PaceError):
        pace_label(-0.1)
    with pytest.raises(PaceError):
        pace_label(math.nan)


def test_invalid_inputs_raise_clear_errors():
    samples = _pulse_train(4, 1.0)
    valid_vad = _vad_result([Segment(0.0, 1.0, SPEECH)])

    with pytest.raises(PaceError):
        analyze_pace(np.zeros((10, 2), dtype=np.float32), valid_vad)
    with pytest.raises(PaceError):
        analyze_pace(np.array([], dtype=np.float32), valid_vad)
    with pytest.raises(PaceError):
        analyze_pace(samples, _vad_result([Segment(0.5, 0.4, SPEECH)]))
    with pytest.raises(PaceError):
        analyze_pace(samples, _vad_result([Segment(0.0, 0.5, SPEECH), Segment(0.4, 1.0, SPEECH)]))
    with pytest.raises(PaceError):
        analyze_pace(samples, _vad_result([Segment(0.0, 1.2, SPEECH)]))
    with pytest.raises(PaceError):
        analyze_pace(samples, _vad_result([Segment(0.0, 1.0, "music")]))
    with pytest.raises(PaceError):
        analyze_pace(samples, valid_vad, frame_ms=0.0)
    with pytest.raises(PaceError):
        analyze_pace(samples, valid_vad, hop_ms=0.0)
    with pytest.raises(PaceError):
        analyze_pace(samples, valid_vad, smoothing_frames=0)
    with pytest.raises(PaceError):
        analyze_pace(samples, valid_vad, nucleus_threshold_ratio=-0.1)
    with pytest.raises(PaceError):
        analyze_pace(samples, valid_vad, nucleus_threshold_ratio=1.1)
    with pytest.raises(PaceError):
        analyze_pace(samples, valid_vad, min_nucleus_distance_seconds=0.0)
