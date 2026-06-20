"""Tests for the real-audio validation protocol helpers (Phase 4)."""

from __future__ import annotations

import pytest

from vocal_intel import protocol
from vocal_intel.protocol import (
    SAMPLE_CATEGORIES,
    is_valid_result_record,
    validate_result_record,
    words_per_minute,
)


def _valid_record(**overrides):
    record = {
        "sample_id": "2026-06-20-normal-clean",
        "category": "normal",
        "noise_condition": "clean",
        "recorded_seconds": 8.4,
        "intended_loudness": "normal",
        "intended_pace": "normal",
        "expected_pause_count": 2,
    }
    record.update(overrides)
    return record


def test_categories_cover_required_set():
    for category in (
        "normal",
        "soft",
        "loud",
        "fast",
        "slow",
        "expressive",
        "thinking_pauses",
    ):
        assert category in SAMPLE_CATEGORIES


def test_valid_record_passes():
    assert validate_result_record(_valid_record()) == []
    assert is_valid_result_record(_valid_record())


def test_missing_field_is_reported():
    record = _valid_record()
    del record["category"]
    errors = validate_result_record(record)
    assert any("category" in e for e in errors)


def test_bad_enum_values_are_reported():
    assert validate_result_record(_valid_record(category="whisper"))
    assert validate_result_record(_valid_record(intended_loudness="medium"))
    assert validate_result_record(_valid_record(intended_pace="brisk"))
    assert validate_result_record(_valid_record(noise_condition="muffled"))


def test_negative_pause_count_is_reported():
    assert validate_result_record(_valid_record(expected_pause_count=-1))


def test_booleans_are_not_accepted_as_numbers():
    assert validate_result_record(_valid_record(recorded_seconds=True))
    assert validate_result_record(_valid_record(expected_pause_count=True))


def test_optional_expressivity_is_validated():
    assert validate_result_record(_valid_record(expressivity="expressive")) == []
    assert validate_result_record(_valid_record(expressivity="dramatic"))


def test_words_per_minute_anchor():
    assert words_per_minute(150, 60.0) == 150.0
    assert words_per_minute(0, 10.0) == 0.0
    with pytest.raises(ValueError):
        words_per_minute(10, 0)
    with pytest.raises(ValueError):
        words_per_minute(-1, 10.0)
