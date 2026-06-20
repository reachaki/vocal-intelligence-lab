"""Tests for voice activity detection and noise-floor estimation (Phase 6).

Uses the Phase 2 synthetic fixtures. Onset/offset tolerances are documented
inline (within ~50-60 ms, i.e. a few analysis frames).
"""

from __future__ import annotations

import numpy as np
import pytest

from vocal_intel import synthetic
from vocal_intel.vad import (
    NON_SPEECH,
    SPEECH,
    Segment,
    VadError,
    VadResult,
    detect_voice_activity,
    estimate_noise_floor,
)

SR = 16000


def _silence_tone_silence(tone_seconds=0.4, amplitude=0.5, pad=0.3):
    return np.concatenate(
        [
            synthetic.silence(pad, SR),
            synthetic.tone(220.0, tone_seconds, SR, amplitude=amplitude),
            synthetic.silence(pad, SR),
        ]
    ).astype(np.float32)


def _speech_segments(result: VadResult):
    return [s for s in result.segments if s.label == SPEECH]


def test_estimate_noise_floor_picks_low_energy():
    frames = np.array([0.001, 0.001, 0.001, 0.5, 0.5])
    assert estimate_noise_floor(frames, percentile=10) < 0.01
    with pytest.raises(VadError):
        estimate_noise_floor(np.array([]))


def test_silence_only_has_no_speech():
    result = detect_voice_activity(synthetic.silence(1.0, SR), SR)
    assert not _speech_segments(result)
    assert all(s.label == NON_SPEECH for s in result.segments)


def test_active_region_detected_with_known_onset_offset():
    signal = _silence_tone_silence(tone_seconds=0.4, pad=0.3)
    result = detect_voice_activity(signal, SR)
    speech = _speech_segments(result)
    assert len(speech) == 1
    assert abs(speech[0].start_seconds - 0.3) < 0.05
    assert abs(speech[0].end_seconds - 0.7) < 0.05
    # segment exposes start, end, duration, and label
    assert speech[0].duration_seconds > 0
    assert speech[0].label == SPEECH


def test_quiet_background_with_louder_region():
    signal = synthetic.tone(180.0, 1.0, SR, amplitude=0.01)
    start, end = int(0.4 * SR), int(0.6 * SR)
    signal[start:end] = signal[start:end] + synthetic.tone(220.0, 0.2, SR, amplitude=0.4)
    result = detect_voice_activity(signal.astype(np.float32), SR)
    speech = _speech_segments(result)
    assert len(speech) == 1
    assert abs(speech[0].start_seconds - 0.4) < 0.06
    assert abs(speech[0].end_seconds - 0.6) < 0.06


def test_pause_gap_yields_two_speech_segments():
    fixture = synthetic.pause_gap(tone_seconds=0.5, gap_seconds=0.4, sample_rate=SR, amplitude=0.5)
    result = detect_voice_activity(fixture.samples, SR)
    speech = _speech_segments(result)
    assert len(speech) == 2
    assert speech[0].end_seconds <= fixture.gap_start_seconds + 0.06
    assert speech[1].start_seconds >= fixture.gap_end_seconds - 0.06


def test_short_blip_is_smoothed_out():
    signal = _silence_tone_silence(tone_seconds=0.08, pad=0.3)
    # A high min-speech requirement treats the 80 ms region as a blip.
    result = detect_voice_activity(signal, SR, min_speech_seconds=0.2)
    assert not _speech_segments(result)


def test_segmentation_stable_with_added_noise():
    clean = _silence_tone_silence(tone_seconds=0.4, pad=0.3)
    rng = np.random.default_rng(0)
    noisy = (clean + rng.normal(0.0, 0.005, size=clean.shape)).astype(np.float32)

    clean_speech = _speech_segments(detect_voice_activity(clean, SR))
    noisy_speech = _speech_segments(detect_voice_activity(noisy, SR))

    assert len(clean_speech) == 1
    assert len(noisy_speech) == 1
    assert abs(clean_speech[0].start_seconds - noisy_speech[0].start_seconds) < 0.05
    assert abs(clean_speech[0].end_seconds - noisy_speech[0].end_seconds) < 0.05


def test_uniform_quiet_background_is_not_all_speech():
    result = detect_voice_activity(synthetic.tone(180.0, 1.0, SR, amplitude=0.02), SR)
    assert result.threshold_dbfs > result.noise_floor_dbfs
    assert not _speech_segments(result)


def test_result_exposes_noise_floor_and_threshold():
    result = detect_voice_activity(_silence_tone_silence(), SR)
    assert isinstance(result, VadResult)
    assert result.threshold_dbfs == pytest.approx(result.noise_floor_dbfs + 8.0)
    assert len(result.frame_rms) == len(result.frame_times) == len(result.frame_is_speech)


def test_invalid_input_raises():
    with pytest.raises(VadError):
        detect_voice_activity(np.zeros((10, 2)), SR)  # not mono
    with pytest.raises(VadError):
        detect_voice_activity(np.array([], dtype=np.float32), SR)  # empty
    with pytest.raises(VadError):
        detect_voice_activity(synthetic.tone(220.0, 0.1, SR), 0)  # bad sample rate
