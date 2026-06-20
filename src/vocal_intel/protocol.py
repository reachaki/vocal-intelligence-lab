"""Real-audio validation protocol helpers.

This module holds the label vocabularies for the manual real-audio protocol and
a lightweight validator for validation result records. It performs no audio
processing; it only checks that a pre-registered or result record is well formed
so that manual validation stays consistent across runs.
"""

from __future__ import annotations

from collections.abc import Mapping

# Sample categories captured for the real-audio protocol.
SAMPLE_CATEGORIES = (
    "normal",
    "soft",
    "loud",
    "fast",
    "slow",
    "expressive",
    "thinking_pauses",
)

# Each sample is recorded clean and, where feasible, in a noisy condition.
NOISE_CONDITIONS = ("clean", "noisy")

# Qualitative label vocabularies (shared with the architecture's labels).
LOUDNESS_LABELS = ("soft", "normal", "loud")
PACE_LABELS = ("slow", "normal", "fast")
EXPRESSIVITY_LABELS = ("flat", "normal", "expressive")

# Required fields in a pre-registered validation result record.
REQUIRED_FIELDS = (
    "sample_id",
    "category",
    "noise_condition",
    "recorded_seconds",
    "intended_loudness",
    "intended_pace",
    "expected_pause_count",
)


def words_per_minute(word_count: int, recorded_seconds: float) -> float:
    """Return an objective pace anchor in words per minute."""
    if word_count < 0:
        raise ValueError("word_count must be non-negative")
    if recorded_seconds <= 0:
        raise ValueError("recorded_seconds must be positive")
    return word_count / (recorded_seconds / 60.0)


def _is_real_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_result_record(record: Mapping) -> list[str]:
    """Return a list of problems with a result record (empty means valid)."""
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"missing required field: {field}")
    if errors:
        return errors

    if record["category"] not in SAMPLE_CATEGORIES:
        errors.append(f"category must be one of {SAMPLE_CATEGORIES}")
    if record["noise_condition"] not in NOISE_CONDITIONS:
        errors.append(f"noise_condition must be one of {NOISE_CONDITIONS}")
    if record["intended_loudness"] not in LOUDNESS_LABELS:
        errors.append(f"intended_loudness must be one of {LOUDNESS_LABELS}")
    if record["intended_pace"] not in PACE_LABELS:
        errors.append(f"intended_pace must be one of {PACE_LABELS}")

    if not _is_real_number(record["recorded_seconds"]) or record["recorded_seconds"] <= 0:
        errors.append("recorded_seconds must be a positive number")

    pauses = record["expected_pause_count"]
    if not isinstance(pauses, int) or isinstance(pauses, bool) or pauses < 0:
        errors.append("expected_pause_count must be a non-negative integer")

    expressivity = record.get("expressivity")
    if expressivity is not None and expressivity not in EXPRESSIVITY_LABELS:
        errors.append(f"expressivity must be one of {EXPRESSIVITY_LABELS}")

    return errors


def is_valid_result_record(record: Mapping) -> bool:
    """Return True when the record passes :func:`validate_result_record`."""
    return not validate_result_record(record)
