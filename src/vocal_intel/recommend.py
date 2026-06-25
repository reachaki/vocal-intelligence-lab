"""Deterministic, signal-level conversation-recommendation document assembler.

This module is an opt-in companion to ``summary``. It assembles a single
JSON-ready document (``schema_version`` ``"1.1"``) that pairs the unified
feature summary with one provisional, rule-based conversation-timing label from
the policy core. It performs no signal-processing math and recomputes no
features: it reuses the feature blocks produced by ``summary`` verbatim and adds
the policy's recommendation, reason, and evidence.

The recommendation is a description of measured audio (clip duration, voiced
fraction, detected speech presence, and the longest measured silence) and the
provisional rule that maps the longest measured silence to a timing action. It
makes no inference about the speaker.

The ``summarize`` output (``schema_version`` ``"1.0"``) is unchanged; this is a
distinct, separately versioned document emitted by a distinct command. The
policy and summary modules are imported here; ``summary`` does not import this
module.
"""

from __future__ import annotations

import json

from vocal_intel import policy
from vocal_intel.config import DEFAULT_THRESHOLD_CONFIG, ThresholdConfig

RECOMMEND_SCHEMA_VERSION = "1.1"

RECOMMEND_LIMITATIONS_TEXT = (
    "Single-speaker, signal-level estimates; thresholds provisional pending "
    "real-audio calibration. The conversation recommendation is a provisional, "
    "rule-based label derived from whole-clip signal measurements (clip "
    "duration, voiced fraction, detected speech presence, and the longest "
    "measured silence); it is a description of measured audio, makes no "
    "inference about the speaker, and is not a validated behavioural claim."
)


def build_recommendation_document(
    summary,
    *,
    config: ThresholdConfig = DEFAULT_THRESHOLD_CONFIG,
) -> dict:
    """Assemble the schema v1.1 recommendation document from a feature summary.

    Pure and free of I/O. ``summary`` is a
    :class:`vocal_intel.summary.FeatureSummary`. The feature blocks are reused
    verbatim from ``summary.to_dict()`` so the embedded feature numbers are
    provably identical to the ``summarize`` output; no feature is recomputed and
    the source document is not mutated.

    Key insertion order below IS the schema v1.1 field order. An intended schema
    change requires bumping ``RECOMMEND_SCHEMA_VERSION`` and regenerating the
    golden manifest in the same change.
    """
    d = summary.to_dict()
    decision = policy.decide(summary, config)

    return {
        "schema_version": RECOMMEND_SCHEMA_VERSION,
        "config_version": d["config_version"],
        "policy_config_version": config.conversation_policy.version,
        "source": d["source"],
        "duration_seconds": d["duration_seconds"],
        "loudness": d["loudness"],
        "pauses": d["pauses"],
        "pitch": d["pitch"],
        "pace": d["pace"],
        "confidence": d["confidence"],
        "limitations": RECOMMEND_LIMITATIONS_TEXT,
        "conversation_recommendation": decision.recommendation,
        "reason": decision.reason,
        "evidence": list(decision.evidence),
        "uncertainty": {},
    }


def recommend_file(
    path,
    *,
    config: ThresholdConfig = DEFAULT_THRESHOLD_CONFIG,
) -> dict:
    """Load a local audio file and assemble its schema v1.1 document.

    ``summary`` is imported lazily so callers and the CLI version/help paths do
    not pull in the audio file stack unless a recommendation is requested. The
    existing ingestion errors raised by ``summarize_file`` are reused; no new
    error types are introduced.
    """
    from vocal_intel import summary

    feature_summary = summary.summarize_file(path, config=config)
    return build_recommendation_document(feature_summary, config=config)


def to_json(document) -> str:
    """Serialize a recommendation document with the pinned deterministic settings.

    Identical settings to the ``summarize`` serializer, so the two documents
    serialise with the same formatting rules.
    """
    return json.dumps(
        document,
        indent=2,
        ensure_ascii=True,
        sort_keys=False,
        separators=(",", ": "),
    )


__all__ = [
    "RECOMMEND_LIMITATIONS_TEXT",
    "RECOMMEND_SCHEMA_VERSION",
    "build_recommendation_document",
    "recommend_file",
    "to_json",
]
