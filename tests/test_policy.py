"""Tests for the deterministic conversation-timing policy core (Phase 12).

Inputs are :class:`FeatureSummary` instances constructed directly with explicit
field values, so the tests need no real or synthetic audio. Every assertion is
against an independently known value, and the exact-string tests pin both the
closed-template wording and the six-decimal number rounding.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from vocal_intel import policy
from vocal_intel.config import DEFAULT_THRESHOLD_CONFIG
from vocal_intel.policy import (
    CLARIFY,
    NOT_ENOUGH_EVIDENCE,
    RECOMMENDATIONS,
    RESPOND,
    WAIT,
    PolicyDecision,
    decide,
)
from vocal_intel.summary import FeatureSummary

T = DEFAULT_THRESHOLD_CONFIG.conversation_policy


def _summary(
    *,
    duration_seconds: float = 8.4,
    longest_pause_seconds: float = 0.0,
    pause_count: int = 0,
    pitch_voiced_fraction: float = 0.55,
    pace_label: str = "normal",
) -> FeatureSummary:
    """Build a FeatureSummary with only the policy-relevant fields varied.

    The remaining schema fields are filled with neutral, valid placeholders;
    the policy reads only duration_seconds, longest_pause_seconds, pause_count,
    pitch_voiced_fraction, and pace_label.
    """
    return FeatureSummary(
        config_version=DEFAULT_THRESHOLD_CONFIG.version,
        source_path=None,
        sample_rate=16000,
        duration_seconds=duration_seconds,
        loudness_label="normal",
        loudness_rms_dbfs=-20.0,
        loudness_peak_dbfs=-10.0,
        pause_count=pause_count,
        total_pause_seconds=longest_pause_seconds,
        longest_pause_seconds=longest_pause_seconds,
        short_pause_count=0,
        medium_pause_count=0,
        long_pause_count=0,
        pitch_delivery_label="flat",
        pitch_trend_label="stable",
        pitch_median_frequency_hz=220.0,
        pitch_voiced_fraction=pitch_voiced_fraction,
        pace_label=pace_label,
        pace_syllable_rate_per_second=4.0,
        pace_speech_active_seconds=2.0,
    )


# --- the four core recommendations ---------------------------------------


def test_long_pause_maps_to_respond():
    decision = decide(_summary(longest_pause_seconds=1.2, pause_count=1))
    assert decision.recommendation == RESPOND


def test_medium_pause_maps_to_wait():
    decision = decide(_summary(longest_pause_seconds=0.7, pause_count=1))
    assert decision.recommendation == WAIT


def test_several_short_pauses_map_to_clarify():
    decision = decide(_summary(longest_pause_seconds=0.3, pause_count=3))
    assert decision.recommendation == CLARIFY


def test_weak_pattern_maps_to_not_enough_evidence():
    # Below the wait band with too few pauses to clarify.
    decision = decide(_summary(longest_pause_seconds=0.3, pause_count=1))
    assert decision.recommendation == NOT_ENOUGH_EVIDENCE


# --- gate edge cases ------------------------------------------------------


def test_duration_just_below_minimum_is_not_enough_evidence():
    decision = decide(_summary(duration_seconds=T.min_clip_seconds - 0.01))
    assert decision.recommendation == NOT_ENOUGH_EVIDENCE
    assert "Clip duration" in decision.reason


def test_voiced_fraction_just_below_floor_is_not_enough_evidence():
    decision = decide(_summary(pitch_voiced_fraction=T.min_voiced_fraction - 0.01))
    assert decision.recommendation == NOT_ENOUGH_EVIDENCE
    assert "Voiced fraction" in decision.reason


def test_unknown_pace_is_not_enough_evidence():
    decision = decide(_summary(pace_label="unknown"))
    assert decision.recommendation == NOT_ENOUGH_EVIDENCE
    assert decision.evidence == ("pace.label=unknown",)


def test_single_short_pause_below_clarify_count_is_not_enough_evidence():
    # One short pause: pause_count < min_pause_count_for_clarify, small L.
    decision = decide(_summary(longest_pause_seconds=0.2, pause_count=1))
    assert decision.recommendation == NOT_ENOUGH_EVIDENCE
    assert decision.recommendation != CLARIFY


# --- boundary operators ---------------------------------------------------


def test_longest_pause_exactly_at_respond_threshold_maps_to_respond():
    decision = decide(
        _summary(longest_pause_seconds=T.respond_pause_min_seconds, pause_count=1)
    )
    assert decision.recommendation == RESPOND


def test_longest_pause_exactly_at_wait_threshold_maps_to_wait():
    decision = decide(
        _summary(longest_pause_seconds=T.wait_pause_min_seconds, pause_count=1)
    )
    assert decision.recommendation == WAIT


# --- determinism ----------------------------------------------------------


def test_decide_is_deterministic_and_byte_stable():
    summary = _summary(longest_pause_seconds=1.2, pause_count=1)
    first = decide(summary)
    second = decide(summary)

    assert first == second
    assert first.to_dict() == second.to_dict()
    assert json.dumps(first.to_dict(), sort_keys=True) == json.dumps(
        second.to_dict(), sort_keys=True
    )


def test_decision_evidence_is_an_immutable_tuple():
    decision = decide(_summary(longest_pause_seconds=1.2, pause_count=1))
    assert isinstance(decision.evidence, tuple)
    assert isinstance(decision.to_dict()["evidence"], list)


# --- exact-string assertions (pins template wording and rounding) ---------


def test_respond_reason_and_evidence_exact_strings():
    decision = decide(_summary(longest_pause_seconds=1.2, pause_count=1))

    assert decision.reason == (
        "Longest measured silence was 1.2 s, at or above the respond threshold "
        "of 1.0 s; the provisional timing rule maps this to respond."
    )
    assert (
        "pauses.longest_pause_seconds=1.2 vs policy.respond_pause_min_seconds=1.0"
        in decision.evidence
    )
    assert decision.evidence[0] == (
        "pauses.longest_pause_seconds=1.2 vs policy.respond_pause_min_seconds=1.0"
    )


def test_wait_reason_renders_binary_tail_to_six_decimals():
    # Raw L carries a binary rounding tail; it must render as 0.68.
    decision = decide(_summary(longest_pause_seconds=0.6799999999999999, pause_count=1))

    assert decision.recommendation == WAIT
    assert decision.reason == (
        "Longest measured silence was 0.68 s, within the wait band from 0.5 s "
        "up to 1.0 s; the provisional timing rule maps this to wait."
    )
    assert decision.evidence[0] == (
        "pauses.longest_pause_seconds=0.68 vs policy.wait_pause_min_seconds=0.5"
    )


def test_reason_is_never_empty_across_branches():
    inputs = [
        _summary(longest_pause_seconds=1.2, pause_count=1),
        _summary(longest_pause_seconds=0.7, pause_count=1),
        _summary(longest_pause_seconds=0.3, pause_count=3),
        _summary(longest_pause_seconds=0.3, pause_count=1),
        _summary(duration_seconds=0.1),
        _summary(pitch_voiced_fraction=0.1),
        _summary(pace_label="unknown"),
    ]
    for summary in inputs:
        decision = decide(summary)
        assert isinstance(decision.reason, str)
        assert decision.reason.strip()


# --- closed recommendation set / reserved values guard --------------------


def test_recommendations_are_the_closed_set():
    assert RECOMMENDATIONS == (WAIT, RESPOND, CLARIFY, NOT_ENOUGH_EVIDENCE)


def test_reserved_recommendations_appear_nowhere():
    for forbidden in ("interrupt_politely", "challenge"):
        assert forbidden not in RECOMMENDATIONS
    source = Path(policy.__file__).read_text(encoding="utf-8")
    assert "interrupt_politely" not in source
    assert "challenge" not in source


def test_every_decision_uses_a_recommendation_from_the_closed_set():
    inputs = [
        _summary(longest_pause_seconds=1.2, pause_count=1),
        _summary(longest_pause_seconds=0.7, pause_count=1),
        _summary(longest_pause_seconds=0.3, pause_count=3),
        _summary(longest_pause_seconds=0.3, pause_count=1),
        _summary(duration_seconds=0.1),
        _summary(pitch_voiced_fraction=0.1),
        _summary(pace_label="unknown"),
    ]
    for summary in inputs:
        assert decide(summary).recommendation in RECOMMENDATIONS


# --- forbidden-vocabulary guard on produced strings -----------------------

_FORBIDDEN_WORDS = [
    "thinking",
    "likely",
    "probably",
    "feels",
    "wants",
    "trying",
    "unfinished",
    "engaged",
    "disengaged",
    "frustrat",
    "excited",
    "hesitat",
    "energy",
]


def test_produced_strings_contain_no_forbidden_vocabulary():
    inputs = [
        _summary(longest_pause_seconds=1.2, pause_count=1),
        _summary(longest_pause_seconds=0.7, pause_count=2),
        _summary(longest_pause_seconds=0.3, pause_count=4),
        _summary(longest_pause_seconds=0.2, pause_count=1),
        _summary(duration_seconds=0.1),
        _summary(pitch_voiced_fraction=0.05),
        _summary(pace_label="unknown"),
    ]
    for summary in inputs:
        decision = decide(summary)
        haystack = " ".join([decision.reason, *decision.evidence]).lower()
        for word in _FORBIDDEN_WORDS:
            assert word not in haystack, (
                f"forbidden word {word!r} found in policy output: {haystack!r}"
            )


# --- missing attribute fails loudly --------------------------------------


def test_missing_required_attribute_raises_attribute_error():
    class _Partial:
        duration_seconds = 8.4
        # longest_pause_seconds intentionally absent.

    with pytest.raises(AttributeError):
        decide(_Partial())


# --- thresholds are read from config -------------------------------------


def test_thresholds_are_sourced_from_config():
    # A tighter respond threshold reclassifies a borderline long pause as wait.
    strict = replace(
        DEFAULT_THRESHOLD_CONFIG,
        conversation_policy=replace(
            DEFAULT_THRESHOLD_CONFIG.conversation_policy,
            respond_pause_min_seconds=1.50,
        ),
    )
    summary = _summary(longest_pause_seconds=1.2, pause_count=1)
    assert decide(summary).recommendation == RESPOND
    assert decide(summary, config=strict).recommendation == WAIT


def test_policy_decision_to_dict_shape():
    decision = PolicyDecision("wait", "a reason", ["e1", "e2"])
    assert decision.to_dict() == {
        "recommendation": "wait",
        "reason": "a reason",
        "evidence": ["e1", "e2"],
    }
