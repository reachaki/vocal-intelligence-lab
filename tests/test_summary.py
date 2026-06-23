"""Tests for the unified feature summary and versioned output schema (Phase 11).

Two fixed synthetic fixtures (a voiced tone surrounded by silence, and pure
silence) exercise the assembled schema. Known feature outputs are asserted to a
six-decimal tolerance that matches the emission contract. The schema-drift test
compares the live ordered field-path manifest against a committed golden file;
an intended schema change requires bumping ``SCHEMA_VERSION`` and regenerating
that manifest in the same change.

WAV fixtures for the CLI tests are written into pytest's temporary directory, so
the suite needs no committed audio.
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

import numpy as np
import pytest

from vocal_intel import cli, synthetic
from vocal_intel import summary as summary_module
from vocal_intel.config import DEFAULT_THRESHOLD_CONFIG
from vocal_intel.pace import (
    FAST_PACE,
    NORMAL_PACE,
    SLOW_PACE,
    UNKNOWN_PACE,
    analyze_pace,
)
from vocal_intel.pauses import analyze_pauses
from vocal_intel.pitch import (
    ANIMATED_DELIVERY,
    FALLING_TREND,
    FLAT_DELIVERY,
    RISING_TREND,
    STABLE_TREND,
    UNKNOWN_DELIVERY,
    UNKNOWN_TREND,
)
from vocal_intel.preprocess import canonicalize
from vocal_intel.summary import (
    CONFIDENCE_NOT_ESTIMATED,
    LIMITATIONS_TEXT,
    SummaryError,
    field_paths,
    summarize_canonical,
)
from vocal_intel.vad import detect_voice_activity

SR = 16000

# Allowed label sets read from the real feature-module constants.
LOUDNESS_LABELS = {"quiet", "normal", "loud"}
DELIVERY_LABELS = {FLAT_DELIVERY, ANIMATED_DELIVERY, UNKNOWN_DELIVERY}
TREND_LABELS = {RISING_TREND, FALLING_TREND, STABLE_TREND, UNKNOWN_TREND}
PACE_LABELS = {SLOW_PACE, NORMAL_PACE, FAST_PACE, UNKNOWN_PACE}

TOP_LEVEL_KEYS = [
    "schema_version",
    "config_version",
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
SOURCE_KEYS = ["path", "sample_rate"]
LOUDNESS_KEYS = ["label", "rms_dbfs", "peak_dbfs"]
PAUSES_KEYS = [
    "pause_count",
    "total_pause_seconds",
    "longest_pause_seconds",
    "short_count",
    "medium_count",
    "long_count",
]
PITCH_KEYS = ["delivery_label", "trend_label", "median_frequency_hz", "voiced_fraction"]
PACE_KEYS = ["label", "syllable_rate_per_second", "speech_active_seconds"]

MANIFEST_PATH = Path(__file__).resolve().parent / "data" / "schema_manifest_v1.json"


def _voiced_raw() -> np.ndarray:
    return np.concatenate(
        [
            synthetic.silence(0.3, SR),
            synthetic.tone(220.0, 0.6, SR, amplitude=0.5),
            synthetic.silence(0.3, SR),
        ]
    )


def _voiced_fixture():
    return canonicalize(_voiced_raw(), SR, SR)


def _silent_fixture():
    return canonicalize(synthetic.silence(1.0, SR), SR, SR)


def _short_tone_fixture():
    return canonicalize(synthetic.tone(220.0, 0.05, SR, amplitude=0.5), SR, SR)


def _pinned_dumps(d: dict) -> str:
    return json.dumps(
        d,
        indent=2,
        ensure_ascii=True,
        sort_keys=False,
        separators=(",", ": "),
    )


def test_summarize_canonical_top_level_keys_exact_and_ordered():
    d = summarize_canonical(_voiced_fixture()).to_dict()

    assert list(d.keys()) == TOP_LEVEL_KEYS
    assert list(d["source"].keys()) == SOURCE_KEYS
    assert list(d["loudness"].keys()) == LOUDNESS_KEYS
    assert list(d["pauses"].keys()) == PAUSES_KEYS
    assert list(d["pitch"].keys()) == PITCH_KEYS
    assert list(d["pace"].keys()) == PACE_KEYS

    assert d["schema_version"] == "1.0"
    assert d["config_version"] == DEFAULT_THRESHOLD_CONFIG.version
    assert d["source"]["path"] is None
    assert d["source"]["sample_rate"] == 16000
    assert d["duration_seconds"] == 1.2


def test_summarize_canonical_values_match_known_feature_outputs():
    d = summarize_canonical(_voiced_fixture()).to_dict()

    assert d["loudness"]["label"] == "loud"
    assert d["loudness"]["rms_dbfs"] == pytest.approx(-12.041200, abs=1e-6)
    assert d["loudness"]["peak_dbfs"] == pytest.approx(-6.020600, abs=1e-6)

    assert d["pitch"]["delivery_label"] == FLAT_DELIVERY
    assert d["pitch"]["trend_label"] == STABLE_TREND
    assert d["pitch"]["median_frequency_hz"] == pytest.approx(220.952621, abs=1e-6)
    assert d["pitch"]["voiced_fraction"] == pytest.approx(0.521368, abs=1e-6)

    assert d["pace"]["label"] == SLOW_PACE
    assert d["pace"]["syllable_rate_per_second"] == 0.0
    assert d["pace"]["speech_active_seconds"] == pytest.approx(0.62, abs=1e-6)

    assert d["pauses"]["pause_count"] == 0
    assert d["pauses"]["total_pause_seconds"] == 0.0
    assert d["pauses"]["longest_pause_seconds"] == 0.0
    assert d["pauses"]["short_count"] == 0
    assert d["pauses"]["medium_count"] == 0
    assert d["pauses"]["long_count"] == 0


def test_summarize_canonical_labels_are_members_of_allowed_sets():
    for canonical in (_voiced_fixture(), _silent_fixture()):
        d = summarize_canonical(canonical).to_dict()
        assert d["loudness"]["label"] in LOUDNESS_LABELS
        assert d["pitch"]["delivery_label"] in DELIVERY_LABELS
        assert d["pitch"]["trend_label"] in TREND_LABELS
        assert d["pace"]["label"] in PACE_LABELS


def test_summarize_silent_input_nulls_and_unknown_labels():
    d = summarize_canonical(_silent_fixture()).to_dict()

    assert d["pitch"]["median_frequency_hz"] is None
    assert d["pace"]["syllable_rate_per_second"] is None
    assert d["pitch"]["delivery_label"] == UNKNOWN_DELIVERY
    assert d["pitch"]["trend_label"] == UNKNOWN_TREND
    assert d["pace"]["label"] == UNKNOWN_PACE

    assert d["pitch"]["voiced_fraction"] == 0.0
    assert d["pace"]["speech_active_seconds"] == 0.0
    assert d["loudness"]["label"] == "quiet"
    assert d["loudness"]["rms_dbfs"] == -120.0
    assert d["loudness"]["peak_dbfs"] == -120.0

    serialized = _pinned_dumps(d)
    json.loads(serialized)
    assert "NaN" not in serialized
    assert "Infinity" not in serialized


def test_summarize_short_single_tone_input():
    canonical = _short_tone_fixture()
    d = summarize_canonical(canonical).to_dict()

    assert list(d.keys()) == TOP_LEVEL_KEYS
    serialized = _pinned_dumps(d)
    json.loads(serialized)
    assert "NaN" not in serialized
    assert "Infinity" not in serialized

    assert d["loudness"]["label"] in LOUDNESS_LABELS
    assert d["pitch"]["delivery_label"] in DELIVERY_LABELS
    assert d["pitch"]["trend_label"] in TREND_LABELS
    assert d["pace"]["label"] in PACE_LABELS
    assert d["duration_seconds"] == pytest.approx(0.05, abs=1e-6)


def test_reserved_fields_are_empty_sentinels():
    d = summarize_canonical(_voiced_fixture()).to_dict()

    assert d["conversation_recommendation"] is None
    assert d["reason"] is None
    assert d["evidence"] == []
    assert isinstance(d["evidence"], list)
    assert d["uncertainty"] == {}
    assert isinstance(d["uncertainty"], dict)
    assert d["confidence"] == "not_estimated"
    assert d["confidence"] == CONFIDENCE_NOT_ESTIMATED
    assert d["limitations"] == LIMITATIONS_TEXT


def test_summary_module_imports_no_policy():
    source = Path(summary_module.__file__).read_text(encoding="utf-8")

    # No policy module is imported (tripwire against Phase 12 scope creep).
    assert "import policy" not in source
    assert "from vocal_intel.policy" not in source
    assert "import vocal_intel.policy" not in source
    # Reserved fields are emitted as literal sentinels, with no derivation.
    assert '"conversation_recommendation": None' in source
    assert '"reason": None' in source
    assert '"evidence": []' in source
    assert '"uncertainty": {}' in source


def test_serialized_output_is_byte_identical_across_calls():
    first = _pinned_dumps(summarize_canonical(_voiced_fixture()).to_dict())
    second = _pinned_dumps(summarize_canonical(_voiced_fixture()).to_dict())

    assert first == second


def test_serialized_output_has_no_excess_precision_or_nonfinite_tokens():
    serialized = _pinned_dumps(summarize_canonical(_voiced_fixture()).to_dict())

    assert "NaN" not in serialized
    assert "Infinity" not in serialized
    for match in re.findall(r"-?\d+\.\d+", serialized):
        fractional = match.split(".", 1)[1]
        assert len(fractional) <= 6


def _walk_leaves(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk_leaves(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_leaves(child)
    else:
        yield value


def test_emitted_numbers_are_native_python_types():
    d = summarize_canonical(_voiced_fixture()).to_dict()

    for leaf in _walk_leaves(d):
        if leaf is None or isinstance(leaf, (str, bool)):
            continue
        assert type(leaf) is int or type(leaf) is float


def test_cli_summarize_valid_wav_returns_zero(tmp_path, capsys):
    wav = tmp_path / "clip.wav"
    synthetic.write_wav(wav, _voiced_raw(), SR)

    rc = cli.main(["summarize", str(wav)])

    assert rc == 0
    d = json.loads(capsys.readouterr().out)
    assert list(d.keys()) == TOP_LEVEL_KEYS
    assert d["schema_version"] == "1.0"
    assert d["config_version"] == DEFAULT_THRESHOLD_CONFIG.version
    assert d["source"]["sample_rate"] == 16000
    assert d["source"]["path"].endswith("clip.wav")


def test_cli_summarize_missing_path_returns_one(tmp_path, capsys):
    rc = cli.main(["summarize", str(tmp_path / "nope.wav")])

    captured = capsys.readouterr()
    assert rc == 1
    assert "error:" in captured.err
    assert captured.out.strip() == ""


def test_cli_summarize_corrupt_file_returns_one(tmp_path, capsys):
    bogus = tmp_path / "broken.wav"
    bogus.write_bytes(b"this is not audio")

    rc = cli.main(["summarize", str(bogus)])

    captured = capsys.readouterr()
    assert rc == 1
    assert "error:" in captured.err


def test_cli_summarize_empty_file_returns_one(tmp_path, capsys):
    empty = tmp_path / "empty.wav"
    empty.write_bytes(b"")

    rc = cli.main(["summarize", str(empty)])

    captured = capsys.readouterr()
    assert rc == 1
    assert "error:" in captured.err


def test_schema_manifest_matches_golden_ordered():
    live = field_paths(summarize_canonical(_voiced_fixture()).to_dict())
    golden = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    # Order-sensitive: catches add, remove, rename, and reorder. An intended
    # schema change requires bumping SCHEMA_VERSION and regenerating this
    # manifest in the same change.
    assert live == golden


def test_schema_value_level_structural_assertions():
    d = summarize_canonical(_voiced_fixture()).to_dict()

    assert d["schema_version"] == "1.0"
    for key in TOP_LEVEL_KEYS:
        assert key in d
    assert d["conversation_recommendation"] is None
    assert d["reason"] is None
    assert d["evidence"] == []
    assert d["uncertainty"] == {}


def test_top_level_config_version_equals_default_config_version():
    d = summarize_canonical(_voiced_fixture()).to_dict()

    assert d["config_version"] == DEFAULT_THRESHOLD_CONFIG.version
    assert d["config_version"] == "phase-10-provisional-v1"


def test_internal_consistency_guard_raises_summary_error(monkeypatch):
    real_analyze_pitch = summary_module.analyze_pitch

    def _mismatched(*args, **kwargs):
        result = real_analyze_pitch(*args, **kwargs)
        return dataclasses.replace(result, config_version="mismatched-vX")

    monkeypatch.setattr(summary_module, "analyze_pitch", _mismatched)

    with pytest.raises(SummaryError):
        summarize_canonical(_voiced_fixture())


def test_inspect_output_unchanged_regression(tmp_path, capsys):
    wav = tmp_path / "sample.wav"
    synthetic.write_wav(wav, synthetic.silence(0.25, SR), SR)

    rc = cli.main(["inspect", str(wav)])

    assert rc == 0
    d = json.loads(capsys.readouterr().out)
    assert set(d.keys()) == {
        "path",
        "duration_seconds",
        "sample_rate",
        "channels",
        "frames",
        "format",
        "subtype",
    }
    # No unified-summary keys leak into inspect output.
    for key in ("loudness", "pauses", "pitch", "pace", "schema_version"):
        assert key not in d


def test_summary_consumes_shared_vad_segmentation_regression():
    canonical = _voiced_fixture()
    d = summarize_canonical(canonical).to_dict()

    vad = detect_voice_activity(canonical.samples, canonical.sample_rate)
    pauses = analyze_pauses(vad).summary
    pace = analyze_pace(canonical.samples, vad)

    assert d["pauses"]["pause_count"] == pauses.pause_count
    assert d["pauses"]["total_pause_seconds"] == pytest.approx(pauses.total_pause_seconds, abs=1e-6)
    assert d["pauses"]["longest_pause_seconds"] == pytest.approx(pauses.longest_pause_seconds, abs=1e-6)
    assert d["pauses"]["short_count"] == pauses.short_count
    assert d["pauses"]["medium_count"] == pauses.medium_count
    assert d["pauses"]["long_count"] == pauses.long_count

    assert d["pace"]["label"] == pace.label
    assert d["pace"]["speech_active_seconds"] == pytest.approx(pace.speech_active_seconds, abs=1e-6)
    expected_rate = pace.syllable_rate_per_second
    if expected_rate is None:
        assert d["pace"]["syllable_rate_per_second"] is None
    else:
        assert d["pace"]["syllable_rate_per_second"] == pytest.approx(expected_rate, abs=1e-6)


def test_lazy_import_does_not_break_version_and_help_regression(capsys):
    assert cli.main(["version"]) == 0
    assert cli.main([]) == 0
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0

    help_text = capsys.readouterr().out.lower()
    assert "summarize" in help_text

    # The summarize subparser is wired without eagerly importing the audio
    # stack or the summary module at CLI module import time.
    parser_source = Path(cli.__file__).read_text(encoding="utf-8")
    assert "from vocal_intel import summary" in parser_source
    # The summary import lives inside the runner, not at module top.
    top_section = parser_source.split("def _run_summarize", 1)[0]
    assert "import summary" not in top_section
