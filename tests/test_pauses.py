"""Tests for silence and pause detection (Phase 7).

Synthetic gap boundaries are checked within roughly 60 ms, matching the
frame-hop tolerance used by the shared VAD segmentation.
"""

from __future__ import annotations

import pytest

from vocal_intel import synthetic
from vocal_intel.pauses import (
    LONG_PAUSE,
    MEDIUM_PAUSE,
    SHORT_PAUSE,
    PauseDetectionError,
    analyze_pauses,
    detect_pauses_from_segments,
    pause_label,
)
from vocal_intel.vad import NON_SPEECH, SPEECH, Segment, detect_voice_activity

SR = 16000


def test_synthetic_pause_gap_detects_known_silence_region():
    fixture = synthetic.pause_gap(tone_seconds=0.5, gap_seconds=0.4, sample_rate=SR, amplitude=0.5)
    vad_result = detect_voice_activity(fixture.samples, SR)
    analysis = analyze_pauses(vad_result)

    assert len(analysis.pauses) == 1
    pause = analysis.pauses[0]
    assert abs(pause.start_seconds - fixture.gap_start_seconds) < 0.06
    assert abs(pause.end_seconds - fixture.gap_end_seconds) < 0.06
    assert pause.duration_seconds == pytest.approx(0.4, abs=0.06)
    assert pause.label == SHORT_PAUSE
    assert analysis.pause_durations_seconds == [pause.duration_seconds]
    assert analysis.summary.pause_count == 1
    assert analysis.summary.short_count == 1


def test_pause_labels_use_provisional_duration_thresholds():
    assert pause_label(0.20) == SHORT_PAUSE
    assert pause_label(0.50) == MEDIUM_PAUSE
    assert pause_label(0.75) == MEDIUM_PAUSE
    assert pause_label(1.00) == LONG_PAUSE
    assert pause_label(1.40) == LONG_PAUSE


def test_pause_summary_counts_duration_labels():
    segments = [
        Segment(0.0, 0.5, SPEECH),
        Segment(0.5, 0.9, NON_SPEECH),
        Segment(0.9, 1.2, SPEECH),
        Segment(1.2, 1.95, NON_SPEECH),
        Segment(1.95, 2.3, SPEECH),
        Segment(2.3, 3.5, NON_SPEECH),
        Segment(3.5, 4.0, SPEECH),
    ]
    analysis = detect_pauses_from_segments(segments)

    assert analysis.pause_durations_seconds == pytest.approx([0.4, 0.75, 1.2])
    assert [pause.label for pause in analysis.pauses] == [SHORT_PAUSE, MEDIUM_PAUSE, LONG_PAUSE]
    assert analysis.summary.pause_count == 3
    assert analysis.summary.total_pause_seconds == pytest.approx(2.35)
    assert analysis.summary.mean_pause_seconds == pytest.approx(2.35 / 3)
    assert analysis.summary.longest_pause_seconds == pytest.approx(1.2)
    assert analysis.summary.short_count == 1
    assert analysis.summary.medium_count == 1
    assert analysis.summary.long_count == 1
    assert analysis.source_segment_count == len(segments)


def test_leading_and_trailing_silence_are_not_pauses():
    segments = [
        Segment(0.0, 0.5, NON_SPEECH),
        Segment(0.5, 1.0, SPEECH),
        Segment(1.0, 1.5, NON_SPEECH),
    ]
    analysis = detect_pauses_from_segments(segments)

    assert analysis.pauses == []
    assert analysis.pause_durations_seconds == []
    assert analysis.summary.pause_count == 0
    assert analysis.summary.longest_pause_seconds == 0.0


def test_short_internal_silence_can_be_filtered():
    segments = [
        Segment(0.0, 0.5, SPEECH),
        Segment(0.5, 0.6, NON_SPEECH),
        Segment(0.6, 1.0, SPEECH),
    ]

    assert detect_pauses_from_segments(segments).pauses == []
    assert detect_pauses_from_segments(segments, min_pause_seconds=0.05).summary.pause_count == 1


def test_no_speech_yields_empty_pause_analysis():
    segments = [Segment(0.0, 1.0, NON_SPEECH)]
    analysis = detect_pauses_from_segments(segments)

    assert analysis.pauses == []
    assert analysis.summary.pause_count == 0
    assert analysis.source_segment_count == 1


def test_invalid_segments_and_thresholds_raise_clear_errors():
    with pytest.raises(PauseDetectionError):
        detect_pauses_from_segments([Segment(0.0, 1.0, "music")])
    with pytest.raises(PauseDetectionError):
        detect_pauses_from_segments([Segment(1.0, 0.5, SPEECH)])
    with pytest.raises(PauseDetectionError):
        detect_pauses_from_segments([Segment(0.5, 1.0, SPEECH), Segment(0.8, 1.2, NON_SPEECH)])
    with pytest.raises(PauseDetectionError):
        detect_pauses_from_segments([Segment(0.0, 1.0, SPEECH)], min_pause_seconds=-0.1)
    with pytest.raises(PauseDetectionError):
        pause_label(0.0)
    with pytest.raises(PauseDetectionError):
        pause_label(-0.1)
    with pytest.raises(PauseDetectionError):
        pause_label(0.5, short_pause_max_seconds=1.0, medium_pause_max_seconds=0.5)
