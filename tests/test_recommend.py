"""Tests for the opt-in conversation-recommendation document (Phase 12b).

The recommendation document (``schema_version`` ``"1.1"``) pairs the unified
feature summary with one provisional, rule-based policy label. These tests pin
the document shape and ordering against a committed golden manifest, pin the
exact reason/evidence wording for the classified branches, confirm the
conservative default end-to-end through the CLI, and assert that the
``summarize`` output stays byte-stable.

FeatureSummary inputs are constructed directly with explicit field values where
the policy branch is the focus (mirroring ``tests/test_policy.py``). End-to-end
and CLI tests build synthetic audio with ``vocal_intel.synthetic`` and write a
temporary WAV, so the suite needs no committed audio.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from vocal_intel import cli, policy, recommend, synthetic
from vocal_intel import summary as summary_module
from vocal_intel.config import DEFAULT_THRESHOLD_CONFIG
from vocal_intel.recommend import (
    RECOMMEND_LIMITATIONS_TEXT,
    RECOMMEND_SCHEMA_VERSION,
    build_recommendation_document,
)
from vocal_intel.summary import FeatureSummary, LIMITATIONS_TEXT, field_paths

SR = 16000

TOP_LEVEL_KEYS = [
    "schema_version",
    "config_version",
    "policy_config_version",
    "source",
    "duration_seconds",
    "loudness",
    "pauses",
    "pitch",
    "pace",
    "confidence",
    "limitations",
    "conversation_recommendation",
    "reason",
    "evidence",
    "uncertainty",
]

# The feature blocks the two documents must share byte-for-byte.
SHARED_FEATURE_KEYS = ["source", "duration_seconds", "loudness", "pauses", "pitch", "pace"]

MANIFEST_PATH = (
    Path(__file__).resolve().parent / "data" / "schema_manifest_recommend_v1_1.json"
)


def _summary(
    *,
    duration_seconds: float = 8.4,
    longest_pause_seconds: float = 0.0,
    pause_count: int = 0,
    pitch_voiced_fraction: float = 0.55,
    pace_label: str = "normal",
) -> FeatureSummary:
    """Build a FeatureSummary with only the policy-relevant fields varied.

    The remaining schema fields are filled with neutral, valid placeholders.
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


# --- synthetic audio fixtures --------------------------------------------


def _voiced_raw() -> np.ndarray:
    return np.concatenate(
        [
            synthetic.silence(0.3, SR),
            synthetic.tone(220.0, 0.6, SR, amplitude=0.5),
            synthetic.silence(0.3, SR),
        ]
    )


def _gap_raw(gap_seconds: float) -> np.ndarray:
    """A tone, a silent gap, then a tone; the gap becomes one measured pause."""
    return np.concatenate(
        [
            synthetic.tone(220.0, 0.8, SR, amplitude=0.5),
            synthetic.silence(gap_seconds, SR),
            synthetic.tone(220.0, 0.8, SR, amplitude=0.5),
        ]
    )


def _clarify_raw() -> np.ndarray:
    """Several short pauses between tones (longest below the wait band)."""
    parts = []
    for _ in range(4):
        parts.append(synthetic.tone(220.0, 0.6, SR, amplitude=0.5))
        parts.append(synthetic.silence(0.3, SR))
    parts.append(synthetic.tone(220.0, 0.6, SR, amplitude=0.5))
    return np.concatenate(parts)


def _pinned_dumps(d: dict) -> str:
    return json.dumps(
        d,
        indent=2,
        ensure_ascii=True,
        sort_keys=False,
        separators=(",", ": "),
    )


# --- 1. shape / order -----------------------------------------------------


def test_document_top_level_keys_exact_and_ordered():
    document = build_recommendation_document(_summary(longest_pause_seconds=1.2, pause_count=3))

    assert list(document.keys()) == TOP_LEVEL_KEYS
    assert list(document.keys())[0] == "schema_version"
    assert document["schema_version"] == "1.1"
    assert document["schema_version"] == RECOMMEND_SCHEMA_VERSION


def test_field_paths_match_golden_manifest_ordered():
    document = build_recommendation_document(_summary(longest_pause_seconds=1.2, pause_count=3))
    live = field_paths(document)
    golden = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    # Order-sensitive: catches add, remove, rename, and reorder.
    assert live == golden
    assert len(golden) == 28


# --- 2. classified-branch value-level (exact strings) ---------------------


def test_respond_branch_exact_reason_and_evidence():
    summary = _summary(
        longest_pause_seconds=1.2,
        duration_seconds=8.4,
        pitch_voiced_fraction=0.55,
        pace_label="normal",
        pause_count=3,
    )
    document = build_recommendation_document(summary)

    assert document["conversation_recommendation"] == "respond"
    assert document["reason"] == (
        "Longest measured silence was 1.2 s, at or above the respond threshold "
        "of 1.0 s; the provisional timing rule maps this to respond."
    )
    assert document["evidence"][0] == (
        "pauses.longest_pause_seconds=1.2 vs policy.respond_pause_min_seconds=1.0"
    )
    assert document["evidence"]
    assert all(isinstance(item, str) for item in document["evidence"])


def test_wait_branch_exact_reason_and_evidence():
    summary = _summary(
        longest_pause_seconds=0.7,
        duration_seconds=8.4,
        pitch_voiced_fraction=0.55,
        pace_label="normal",
        pause_count=3,
    )
    document = build_recommendation_document(summary)

    assert document["conversation_recommendation"] == "wait"
    assert document["reason"] == (
        "Longest measured silence was 0.7 s, within the wait band from 0.5 s up "
        "to 1.0 s; the provisional timing rule maps this to wait."
    )
    assert document["evidence"][0] == (
        "pauses.longest_pause_seconds=0.7 vs policy.wait_pause_min_seconds=0.5"
    )
    assert document["evidence"]


# --- 3. conservative default end-to-end -----------------------------------


def test_pure_silence_end_to_end_is_not_enough_evidence(tmp_path):
    wav = tmp_path / "silence.wav"
    synthetic.write_wav(wav, synthetic.silence(1.5, SR), SR)

    document = recommend.recommend_file(str(wav))

    assert document["conversation_recommendation"] == "not_enough_evidence"
    assert document["evidence"]


def test_sub_min_duration_end_to_end_is_not_enough_evidence(tmp_path):
    wav = tmp_path / "tiny.wav"
    synthetic.write_wav(wav, synthetic.tone(220.0, 0.05, SR, amplitude=0.5), SR)

    document = recommend.recommend_file(str(wav))

    assert document["conversation_recommendation"] == "not_enough_evidence"
    assert document["evidence"]


def test_gate_failing_inputs_never_yield_classified_recommendation():
    gate_failing_summaries = [
        _summary(duration_seconds=DEFAULT_THRESHOLD_CONFIG.conversation_policy.min_clip_seconds - 0.01),
        _summary(pitch_voiced_fraction=DEFAULT_THRESHOLD_CONFIG.conversation_policy.min_voiced_fraction - 0.01),
        _summary(pace_label="unknown"),
    ]
    for summary in gate_failing_summaries:
        document = build_recommendation_document(summary)
        assert document["conversation_recommendation"] == "not_enough_evidence"
        assert document["conversation_recommendation"] not in {"wait", "respond", "clarify"}


# --- 4. evidence is always non-empty across all four values ---------------


def test_evidence_non_empty_for_all_four_recommendation_values():
    summaries = {
        "respond": _summary(longest_pause_seconds=1.2, pause_count=1),
        "wait": _summary(longest_pause_seconds=0.7, pause_count=1),
        "clarify": _summary(longest_pause_seconds=0.3, pause_count=3),
        "not_enough_evidence": _summary(pace_label="unknown"),
    }
    seen = set()
    for expected_value, summary in summaries.items():
        document = build_recommendation_document(summary)
        assert document["conversation_recommendation"] == expected_value
        assert isinstance(document["evidence"], list)
        assert document["evidence"]
        assert all(isinstance(item, str) for item in document["evidence"])
        seen.add(document["conversation_recommendation"])
    assert seen == set(policy.RECOMMENDATIONS)


# --- 5. closed-enum guard -------------------------------------------------


def test_recommendation_is_always_in_closed_enum():
    summaries = [
        _summary(longest_pause_seconds=1.2, pause_count=1),
        _summary(longest_pause_seconds=0.7, pause_count=1),
        _summary(longest_pause_seconds=0.3, pause_count=3),
        _summary(longest_pause_seconds=0.3, pause_count=1),
        _summary(duration_seconds=0.1),
        _summary(pitch_voiced_fraction=0.05),
        _summary(pace_label="unknown"),
    ]
    for summary in summaries:
        document = build_recommendation_document(summary)
        assert document["conversation_recommendation"] in policy.RECOMMENDATIONS


def test_reserved_recommendation_strings_appear_nowhere():
    source = Path(recommend.__file__).read_text(encoding="utf-8")
    for forbidden in ("interrupt_politely", "challenge"):
        assert forbidden not in source

    summaries = [
        _summary(longest_pause_seconds=1.2, pause_count=1),
        _summary(longest_pause_seconds=0.7, pause_count=1),
        _summary(longest_pause_seconds=0.3, pause_count=3),
        _summary(longest_pause_seconds=0.3, pause_count=1),
        _summary(duration_seconds=0.1),
        _summary(pitch_voiced_fraction=0.05),
        _summary(pace_label="unknown"),
    ]
    for summary in summaries:
        serialized = _pinned_dumps(build_recommendation_document(summary))
        assert "interrupt_politely" not in serialized
        assert "challenge" not in serialized


# --- 6. feature-block parity with summarize -------------------------------


def _feature_parity_check(canonical):
    feature_summary = summary_module.summarize_canonical(canonical)
    summarize_doc = feature_summary.to_dict()
    recommend_doc = build_recommendation_document(feature_summary)

    # The feature blocks are byte-equal across the two documents.
    for key in SHARED_FEATURE_KEYS:
        assert recommend_doc[key] == summarize_doc[key], key

    # The shared NESTED feature blocks are EXACTLY these keys. The reserved
    # ``uncertainty`` sentinel is ``{}`` in both documents by design (it is not a
    # feature block), so it is excluded; ``evidence`` differs (populated in the
    # recommend document, ``[]`` in summarize).
    nested_equal_keys = [
        key
        for key, value in summarize_doc.items()
        if isinstance(value, (dict, list))
        and key != "uncertainty"
        and key in recommend_doc
        and recommend_doc[key] == value
    ]
    assert set(nested_equal_keys) == {"source", "loudness", "pauses", "pitch", "pace"}

    # The two documents are distinct documents from distinct commands.
    assert recommend_doc != summarize_doc
    assert recommend_doc["schema_version"] != summarize_doc["schema_version"]
    assert recommend_doc["limitations"] != summarize_doc["limitations"]
    assert recommend_doc["conversation_recommendation"] != summarize_doc[
        "conversation_recommendation"
    ]


def test_feature_block_parity_voiced_fixture():
    from vocal_intel.preprocess import canonicalize

    canonical = canonicalize(_voiced_raw(), SR, SR)
    _feature_parity_check(canonical)


def test_feature_block_parity_gap_fixture():
    from vocal_intel.preprocess import canonicalize

    canonical = canonicalize(_gap_raw(1.2), SR, SR)
    _feature_parity_check(canonical)
    # The classified gap fixture exercises a populated recommendation alongside
    # the shared feature blocks.
    feature_summary = summary_module.summarize_canonical(canonical)
    recommend_doc = build_recommendation_document(feature_summary)
    assert recommend_doc["conversation_recommendation"] in policy.RECOMMENDATIONS
    assert recommend_doc["evidence"]


# --- 7. summarize byte-stability regression -------------------------------


def test_summarize_cli_output_is_byte_stable(tmp_path, capsys):
    wav = tmp_path / "clip.wav"
    synthetic.write_wav(wav, _voiced_raw(), SR)

    rc = cli.main(["summarize", str(wav)])
    assert rc == 0
    first = capsys.readouterr().out

    # Pin the summarize document against the in-repo serializer over the SAME
    # loaded audio (the file path the CLI loaded), so this regression breaks if
    # either the schema shape or the serialization settings drift.
    expected = (
        _pinned_dumps(summary_module.summarize_file(str(wav)).to_dict()) + "\n"
    )
    assert first == expected

    # Byte-identical across two independent CLI invocations of the same file.
    rc2 = cli.main(["summarize", str(wav)])
    assert rc2 == 0
    second = capsys.readouterr().out
    assert second == first

    document = json.loads(first)
    assert document["schema_version"] == "1.0"
    assert document["conversation_recommendation"] is None
    assert document["reason"] is None
    assert document["evidence"] == []
    assert document["uncertainty"] == {}
    # No recommend-only key leaks into the summarize document.
    assert "policy_config_version" not in document


# --- 8. limitations -------------------------------------------------------


def test_limitations_text_is_pinned_and_distinct():
    document = build_recommendation_document(_summary(longest_pause_seconds=1.2, pause_count=3))

    assert document["limitations"] == RECOMMEND_LIMITATIONS_TEXT
    assert document["limitations"] != LIMITATIONS_TEXT
    assert "no conversation policy" not in document["limitations"]


# --- 9. policy_config_version ---------------------------------------------


def test_policy_config_version_present_and_matches_config():
    document = build_recommendation_document(_summary(longest_pause_seconds=1.2, pause_count=3))

    assert "policy_config_version" in document
    assert document["policy_config_version"] == (
        DEFAULT_THRESHOLD_CONFIG.conversation_policy.version
    )
    assert document["policy_config_version"] == "phase-12-policy-provisional-v1"


# --- 10. CLI error / exit parity ------------------------------------------


def test_cli_recommend_valid_wav_returns_zero(tmp_path, capsys):
    wav = tmp_path / "clip.wav"
    synthetic.write_wav(wav, _gap_raw(1.2), SR)

    rc = cli.main(["recommend", str(wav)])

    assert rc == 0
    document = json.loads(capsys.readouterr().out)
    assert list(document.keys()) == TOP_LEVEL_KEYS
    assert document["schema_version"] == "1.1"
    assert document["conversation_recommendation"] in policy.RECOMMENDATIONS
    assert document["source"]["path"].endswith("clip.wav")


def test_cli_recommend_missing_path_returns_one_empty_stdout(tmp_path, capsys):
    rc = cli.main(["recommend", str(tmp_path / "nope.wav")])

    captured = capsys.readouterr()
    assert rc == 1
    assert "error:" in captured.err
    assert captured.out == ""


def test_cli_recommend_empty_file_returns_one_empty_stdout(tmp_path, capsys):
    empty = tmp_path / "empty.wav"
    empty.write_bytes(b"")

    rc = cli.main(["recommend", str(empty)])

    captured = capsys.readouterr()
    assert rc == 1
    assert "error:" in captured.err
    assert captured.out == ""


def test_cli_recommend_corrupt_file_returns_one_empty_stdout(tmp_path, capsys):
    bogus = tmp_path / "broken.wav"
    bogus.write_bytes(b"this is not audio")

    rc = cli.main(["recommend", str(bogus)])

    captured = capsys.readouterr()
    assert rc == 1
    assert "error:" in captured.err
    assert captured.out == ""


def test_recommend_appears_in_help(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    help_text = capsys.readouterr().out.lower()
    assert "recommend" in help_text


# --- 11. determinism ------------------------------------------------------


def test_serialized_document_is_byte_identical_across_calls():
    summary = _summary(longest_pause_seconds=1.2, pause_count=3)
    first = recommend.to_json(build_recommendation_document(summary))
    second = recommend.to_json(build_recommendation_document(summary))

    assert first == second


def test_no_scientific_notation_in_reason_or_evidence():
    summaries = [
        _summary(longest_pause_seconds=1.2, pause_count=1),
        _summary(longest_pause_seconds=0.7, pause_count=1),
        _summary(longest_pause_seconds=0.3, pause_count=3),
        _summary(longest_pause_seconds=0.3, pause_count=1),
        _summary(duration_seconds=0.1),
        _summary(pitch_voiced_fraction=0.05),
        _summary(pace_label="unknown"),
    ]
    for summary in summaries:
        document = build_recommendation_document(summary)
        strings = [document["reason"], *document["evidence"]]
        for text in strings:
            assert "e+" not in text
            assert "e-" not in text


# --- 12. forbidden vocabulary ---------------------------------------------

_OVERCLAIM_WORDS = [
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


def test_produced_strings_contain_no_overclaim_vocabulary():
    summaries = [
        _summary(longest_pause_seconds=1.2, pause_count=1),
        _summary(longest_pause_seconds=0.7, pause_count=2),
        _summary(longest_pause_seconds=0.3, pause_count=4),
        _summary(longest_pause_seconds=0.2, pause_count=1),
        _summary(duration_seconds=0.1),
        _summary(pitch_voiced_fraction=0.05),
        _summary(pace_label="unknown"),
    ]
    for summary in summaries:
        document = build_recommendation_document(summary)
        haystack = " ".join(
            [document["reason"], document["limitations"], *document["evidence"]]
        ).lower()
        for word in _OVERCLAIM_WORDS:
            assert word not in haystack, (
                f"overclaim word {word!r} found in recommend output: {haystack!r}"
            )
