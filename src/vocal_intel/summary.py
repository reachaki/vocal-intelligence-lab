"""Unified feature summary and versioned output schema.

This module orchestrates the already-shipped analysis pipeline (loudness,
voice activity, pauses, pitch, pace) for one local audio clip and assembles a
single deterministic JSON-ready document defined by one in-repo versioned
schema. It performs no new signal-processing math: it reads existing result
dataclass fields only.

The document carries two versions: ``schema_version`` (the shape of this
document) and ``config_version`` (the threshold configuration the features were
computed with). Recommendation, reason, evidence, and uncertainty fields are
reserved for a later phase and are emitted as fixed empty sentinels with no
logic behind them.

The analyzer functions are imported at module top as bound names so callers and
tests can reference (and monkeypatch) them through this module. Audio file I/O
(``preprocess.load_canonical``) is imported lazily inside ``summarize_file`` so
that callers working from an already-loaded :class:`CanonicalAudio` never pull
in the file-reading stack.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from vocal_intel.config import DEFAULT_THRESHOLD_CONFIG, ThresholdConfig
from vocal_intel.loudness import analyze_loudness
from vocal_intel.pace import analyze_pace
from vocal_intel.pauses import analyze_pauses
from vocal_intel.pitch import analyze_pitch
from vocal_intel.vad import detect_voice_activity

SCHEMA_VERSION = "1.0"
CONFIDENCE_NOT_ESTIMATED = "not_estimated"
LIMITATIONS_TEXT = (
    "Single-speaker, signal-level estimates; thresholds provisional pending "
    "real-audio calibration; no transcript or conversation policy."
)

# A serialized float carries at most this many fractional digits, which keeps
# the output stable and free of long binary-rounding tails.
_ROUND_DECIMALS = 6


class SummaryError(ValueError):
    """Raised when a unified summary cannot be assembled consistently."""


def _clean_number(value: Any) -> Any:
    """Coerce a numeric leaf to a deterministic JSON-friendly value.

    ``None`` passes through unchanged. Numpy scalars are coerced to native
    Python ``int``/``float``. Non-finite floats (``NaN``/``Inf``) become
    ``None`` so the serialized output never contains a ``NaN``/``Infinity``
    token. Floats are rounded to six decimals and ``-0.0`` is normalised to
    ``0.0`` so two equal values always serialize identically.
    """
    if value is None:
        return None
    # Coerce numpy scalars (np.float64, np.int64, ...) to native Python types.
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        rounded = round(value, _ROUND_DECIMALS)
        if rounded == 0.0:
            # Collapse -0.0 to 0.0 so equal magnitudes serialize identically.
            return 0.0
        return rounded
    return value


def _assert_consistent_config_version(results: list, *, expected: str) -> None:
    """Internal-consistency guard.

    Every sub-result is computed with the one config object threaded through
    this module, so their ``config_version`` values must all equal the expected
    version. A mismatch can only happen through an internal refactor bug (not a
    user passing two configs, because users pass one); raising here surfaces
    that bug loudly instead of silently emitting an inconsistent document.
    """
    for result in results:
        actual = getattr(result, "config_version", None)
        if actual != expected:
            raise SummaryError(
                "internal config_version mismatch: "
                f"expected {expected!r}, got {actual!r}"
            )


@dataclass(frozen=True, eq=False)
class FeatureSummary:
    """One clip's combined feature labels and numbers in schema v1 form."""

    config_version: str
    source_path: str | None
    sample_rate: int
    duration_seconds: float
    loudness_label: str
    loudness_rms_dbfs: float
    loudness_peak_dbfs: float
    pause_count: int
    total_pause_seconds: float
    longest_pause_seconds: float
    short_pause_count: int
    medium_pause_count: int
    long_pause_count: int
    pitch_delivery_label: str
    pitch_trend_label: str
    pitch_median_frequency_hz: float | None
    pitch_voiced_fraction: float
    pace_label: str
    pace_syllable_rate_per_second: float | None
    pace_speech_active_seconds: float

    def to_dict(self) -> dict:
        """Return the schema v1 document as a nested ordered dict.

        Key insertion order here IS the schema field order. An intended schema
        change requires bumping ``SCHEMA_VERSION`` and regenerating the golden
        manifest in the same change.
        """
        return {
            "schema_version": SCHEMA_VERSION,
            "config_version": self.config_version,
            "source": {
                "path": self.source_path,
                "sample_rate": int(self.sample_rate),
            },
            "duration_seconds": _clean_number(self.duration_seconds),
            "loudness": {
                "label": self.loudness_label,
                "rms_dbfs": _clean_number(self.loudness_rms_dbfs),
                "peak_dbfs": _clean_number(self.loudness_peak_dbfs),
            },
            "pauses": {
                "pause_count": int(self.pause_count),
                "total_pause_seconds": _clean_number(self.total_pause_seconds),
                "longest_pause_seconds": _clean_number(self.longest_pause_seconds),
                "short_count": int(self.short_pause_count),
                "medium_count": int(self.medium_pause_count),
                "long_count": int(self.long_pause_count),
            },
            "pitch": {
                "delivery_label": self.pitch_delivery_label,
                "trend_label": self.pitch_trend_label,
                "median_frequency_hz": _clean_number(self.pitch_median_frequency_hz),
                "voiced_fraction": _clean_number(self.pitch_voiced_fraction),
            },
            "pace": {
                "label": self.pace_label,
                "syllable_rate_per_second": _clean_number(self.pace_syllable_rate_per_second),
                "speech_active_seconds": _clean_number(self.pace_speech_active_seconds),
            },
            "confidence": CONFIDENCE_NOT_ESTIMATED,
            "limitations": LIMITATIONS_TEXT,
            # Reserved for a later phase: emitted as fixed empty sentinels with
            # zero logic behind them.
            "conversation_recommendation": None,
            "reason": None,
            "evidence": [],
            "uncertainty": {},
        }

    def to_json(self) -> str:
        """Serialize :meth:`to_dict` with the pinned deterministic settings."""
        return json.dumps(
            self.to_dict(),
            indent=2,
            ensure_ascii=True,
            sort_keys=False,
            separators=(",", ": "),
        )


def summarize_canonical(
    canonical,
    *,
    path: str | None = None,
    config: ThresholdConfig = DEFAULT_THRESHOLD_CONFIG,
) -> FeatureSummary:
    """Assemble a :class:`FeatureSummary` from already-loaded canonical audio.

    One ``config`` object is threaded through every analysis so the document's
    top-level ``config_version`` matches each feature's stamped version.
    ``source.sample_rate`` is the canonical analysis/processing rate
    (``CanonicalAudio.sample_rate``), not the original file rate.
    """
    samples = canonical.samples
    sample_rate = int(canonical.sample_rate)

    loudness = analyze_loudness(samples, sample_rate, config=config)
    vad = detect_voice_activity(samples, sample_rate, config=config)
    pauses = analyze_pauses(vad, config=config)
    pitch = analyze_pitch(samples, sample_rate, config=config)
    pace = analyze_pace(samples, vad, config=config)

    _assert_consistent_config_version(
        [loudness, vad, pauses, pitch, pace],
        expected=config.version,
    )

    pause_summary = pauses.summary

    return FeatureSummary(
        config_version=config.version,
        source_path=path,
        sample_rate=sample_rate,
        duration_seconds=round(float(canonical.duration_seconds), _ROUND_DECIMALS),
        loudness_label=loudness.label,
        loudness_rms_dbfs=loudness.rms_dbfs,
        loudness_peak_dbfs=loudness.peak_dbfs,
        pause_count=pause_summary.pause_count,
        total_pause_seconds=pause_summary.total_pause_seconds,
        longest_pause_seconds=pause_summary.longest_pause_seconds,
        short_pause_count=pause_summary.short_count,
        medium_pause_count=pause_summary.medium_count,
        long_pause_count=pause_summary.long_count,
        pitch_delivery_label=pitch.delivery_label,
        pitch_trend_label=pitch.trend_label,
        pitch_median_frequency_hz=pitch.median_frequency_hz,
        pitch_voiced_fraction=pitch.voiced_fraction,
        pace_label=pace.label,
        pace_syllable_rate_per_second=pace.syllable_rate_per_second,
        pace_speech_active_seconds=pace.speech_active_seconds,
    )


def summarize_file(
    path,
    *,
    config: ThresholdConfig = DEFAULT_THRESHOLD_CONFIG,
) -> FeatureSummary:
    """Load a local audio file and assemble its :class:`FeatureSummary`.

    Reuses the existing ingestion errors raised by ``load_canonical``
    (``AudioFileNotFoundError`` / ``UnreadableAudioError``); no new error types
    are introduced. ``source.path`` is the input path as a string.
    """
    # Imported lazily so callers working from an already-loaded CanonicalAudio
    # (and the CLI version/help paths) do not require the audio file stack.
    from vocal_intel.preprocess import load_canonical

    canonical = load_canonical(path)
    return summarize_canonical(canonical, path=str(path), config=config)


def field_paths(emitted_dict) -> list[str]:
    """Return depth-first dotted field paths from a REAL emitted ``to_dict``.

    The walk follows the dict's insertion order, so the resulting list captures
    both the field set and its ordering. Lists (the reserved ``evidence``
    sentinel) are leaf paths and are not descended into. An empty dict (the
    reserved ``uncertainty`` sentinel) is itself a leaf path, so the reserved
    fields remain visible in the manifest.
    """
    paths: list[str] = []

    def _walk(value, prefix: str) -> None:
        if isinstance(value, dict) and value:
            for key, child in value.items():
                child_prefix = f"{prefix}.{key}" if prefix else key
                _walk(child, child_prefix)
        else:
            paths.append(prefix)

    for key, child in emitted_dict.items():
        _walk(child, key)
    return paths


__all__ = [
    "CONFIDENCE_NOT_ESTIMATED",
    "FeatureSummary",
    "LIMITATIONS_TEXT",
    "SCHEMA_VERSION",
    "SummaryError",
    "field_paths",
    "summarize_canonical",
    "summarize_file",
]
