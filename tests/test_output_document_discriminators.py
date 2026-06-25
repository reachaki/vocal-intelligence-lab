"""Cross-document discriminator tests.

The project emits three distinct JSON documents from three distinct commands:

- ``summarize`` -> the feature summary (``schema_version`` ``"1.0"``)
- ``recommend`` -> the conversation-recommendation document (``schema_version`` ``"1.1"``)
- ``transcript-info`` -> the transcript metadata document
  (``document_type`` ``"transcript_metadata"``, ``schema_version`` ``"1.0"``)

These tests pin the contract a consumer relies on to tell the three apart, exactly
as documented in ``docs/OUTPUT_SCHEMA.md``: the audio family is discriminated by
``schema_version`` (and ``policy_config_version`` is present iff ``recommend``),
while the transcript document is a separate family identified by ``document_type``.

Inputs are synthetic: a fixed tone-and-silence clip and a fixed placeholder text.
"""

from __future__ import annotations

import numpy as np

from vocal_intel import synthetic
from vocal_intel.preprocess import canonicalize
from vocal_intel.recommend import build_recommendation_document
from vocal_intel.summary import summarize_canonical
from vocal_intel.transcript_meta import metadata_from_text

SR = 16000


def _voiced_canonical():
    raw = np.concatenate(
        [
            synthetic.silence(0.3, SR),
            synthetic.tone(220.0, 0.6, SR, amplitude=0.5),
            synthetic.silence(0.3, SR),
        ]
    )
    return canonicalize(raw, SR, SR)


def _documents() -> dict:
    summary = summarize_canonical(_voiced_canonical())
    return {
        "summarize": summary.to_dict(),
        "recommend": build_recommendation_document(summary),
        "transcript": metadata_from_text(
            "two words here\nand one more line\n", path="transcript.txt", fmt="txt"
        ).to_dict(),
    }


def test_document_type_present_only_in_transcript_document():
    docs = _documents()
    assert "document_type" not in docs["summarize"]
    assert "document_type" not in docs["recommend"]
    assert docs["transcript"]["document_type"] == "transcript_metadata"


def test_schema_versions_are_as_specified():
    docs = _documents()
    assert docs["summarize"]["schema_version"] == "1.0"
    assert docs["recommend"]["schema_version"] == "1.1"
    assert docs["transcript"]["schema_version"] == "1.0"


def test_policy_config_version_present_only_in_recommend():
    docs = _documents()
    assert "policy_config_version" not in docs["summarize"]
    assert "policy_config_version" in docs["recommend"]
    assert "policy_config_version" not in docs["transcript"]


def test_transcript_document_carries_no_audio_or_recommendation_fields():
    transcript = _documents()["transcript"]
    for forbidden in (
        "config_version",
        "duration_seconds",
        "loudness",
        "pauses",
        "pitch",
        "pace",
        "conversation_recommendation",
        "reason",
        "evidence",
        "uncertainty",
    ):
        assert forbidden not in transcript, forbidden


def test_each_document_is_uniquely_classifiable():
    # Mirrors the discrimination rule documented in docs/OUTPUT_SCHEMA.md: the
    # transcript document is identified by ``document_type``; within the audio
    # family, ``policy_config_version`` is present iff the recommend (1.1) document.
    def classify(doc: dict) -> str:
        if doc.get("document_type") == "transcript_metadata":
            return "transcript"
        if "policy_config_version" in doc:
            return "recommend"
        if doc.get("schema_version") == "1.0":
            return "summarize"
        return "unknown"

    docs = _documents()
    assert classify(docs["summarize"]) == "summarize"
    assert classify(docs["recommend"]) == "recommend"
    assert classify(docs["transcript"]) == "transcript"
    # The three classifications are mutually distinct.
    kinds = {name: classify(doc) for name, doc in docs.items()}
    assert len(set(kinds.values())) == 3, kinds
