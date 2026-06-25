"""Deterministic, signal-level conversation-timing policy core.

This module maps a single clip's measured feature summary to one of four
provisional timing actions. It is purely deterministic and operates only on
signal-level measurements: the longest measured silence, the clip duration, the
voiced fraction, the measured pause count, and the pace label. It makes no
inference about a speaker -- nothing about emotion, intent, truthfulness,
attention, or any internal state. A recommendation describes a measured pause
and the provisional rule that maps it to an action, and nothing more.

All thresholds are read from ``config.conversation_policy`` and are PROVISIONAL
pending the real-audio calibration run; they are not validated behavioural
claims. The module depends only on the standard library.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from vocal_intel.config import DEFAULT_THRESHOLD_CONFIG, ThresholdConfig
from vocal_intel.summary import FeatureSummary

# Closed enum of recommendation strings. Only these four values are produced.
# The two reserved actions described in the project plan are intentionally
# absent here: they belong to a separately scoped future iteration and are not
# implemented by this module.
WAIT = "wait"
RESPOND = "respond"
CLARIFY = "clarify"
NOT_ENOUGH_EVIDENCE = "not_enough_evidence"

RECOMMENDATIONS = (WAIT, RESPOND, CLARIFY, NOT_ENOUGH_EVIDENCE)


@dataclass(frozen=True, eq=True)
class PolicyDecision:
    """One clip's timing recommendation, its reason, and its evidence.

    ``evidence`` is stored as a tuple internally so the value is immutable and
    deterministic; ``to_dict`` exposes it as a fresh list. ``reason`` is always
    a non-empty string drawn from a closed template set.
    """

    recommendation: str
    reason: str
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        # Defensively coerce evidence to a tuple so callers cannot mutate it and
        # so equality / hashing stay deterministic regardless of input type.
        object.__setattr__(self, "evidence", tuple(self.evidence))

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict, independent of the summary output schema."""
        return {
            "recommendation": self.recommendation,
            "reason": self.reason,
            "evidence": list(self.evidence),
        }


# A serialized float carries at most this many fractional digits; this keeps
# embedded numbers stable and free of long binary-rounding tails.
_ROUND_DECIMALS = 6


def _fmt(value: Any) -> str:
    """Render a number deterministically, mirroring summary._clean_number.

    The value is coerced with ``float()``; non-finite values render as
    ``"null"``; finite values are rounded to six decimals with ``-0.0``
    normalised to ``0.0`` so equal magnitudes render identically. This mirrors
    the rounding behaviour of ``summary._clean_number`` so embedded numbers
    match what the summary schema would serialize.
    """
    if value is None:
        return "null"
    number = float(value)
    if not math.isfinite(number):
        return "null"
    rounded = round(number, _ROUND_DECIMALS)
    if rounded == 0.0:
        rounded = 0.0  # Collapse -0.0 to 0.0.
    return repr(rounded)


# Closed template set keyed by decision branch. Reasons are built ONLY from
# these strings; no free-form text is produced. Every embedded number is
# _fmt-rounded before formatting.
_REASON_TEMPLATES = {
    "respond": (
        "Longest measured silence was {L} s, at or above the respond threshold "
        "of {respond_min} s; the provisional timing rule maps this to respond."
    ),
    "wait": (
        "Longest measured silence was {L} s, within the wait band from "
        "{wait_min} s up to {respond_min} s; the provisional timing rule maps "
        "this to wait."
    ),
    "clarify": (
        "Longest measured silence was {L} s, below the wait threshold of "
        "{wait_min} s, across {pause_count} measured pauses; the provisional "
        "timing rule maps this mixed pattern to clarify."
    ),
    "nee_duration": (
        "Clip duration {dur} s is below the minimum of {min_clip} s needed to "
        "assess timing; not enough evidence."
    ),
    "nee_voiced": (
        "Voiced fraction {vf} is below the minimum of {min_vf} needed to "
        "assess timing; not enough evidence."
    ),
    "nee_pace": (
        "No speech-active region was detected; not enough evidence."
    ),
    "nee_fallthrough": (
        "Longest measured silence was {L} s across {pause_count} measured "
        "pauses, which matches no timing rule; not enough evidence."
    ),
}


def decide(
    summary: FeatureSummary,
    config: ThresholdConfig = DEFAULT_THRESHOLD_CONFIG,
) -> PolicyDecision:
    """Map a feature summary to a provisional timing recommendation.

    Deterministic and signal-level only: this reads the flat measured fields of
    ``summary`` and applies fixed threshold comparisons. It makes no inference
    about the speaker. ``not_enough_evidence`` is the conservative default; it
    is returned whenever a gate fails or the pause pattern matches no rule.

    Required ``summary`` attributes are read directly; a missing attribute
    raises ``AttributeError`` rather than being silently defaulted.
    """
    t = config.conversation_policy

    duration = float(summary.duration_seconds)
    voiced_fraction = float(summary.pitch_voiced_fraction)
    pace_label = summary.pace_label
    longest_pause = float(summary.longest_pause_seconds)
    pause_count = int(summary.pause_count)

    # Gates. Any failing gate yields not_enough_evidence with its own reason.
    if duration < t.min_clip_seconds:
        reason = _REASON_TEMPLATES["nee_duration"].format(
            dur=_fmt(duration), min_clip=_fmt(t.min_clip_seconds)
        )
        evidence = (
            f"duration_seconds={_fmt(duration)} "
            f"vs policy.min_clip_seconds={_fmt(t.min_clip_seconds)}",
        )
        return PolicyDecision(NOT_ENOUGH_EVIDENCE, reason, evidence)

    if voiced_fraction < t.min_voiced_fraction:
        reason = _REASON_TEMPLATES["nee_voiced"].format(
            vf=_fmt(voiced_fraction), min_vf=_fmt(t.min_voiced_fraction)
        )
        evidence = (
            f"pitch.voiced_fraction={_fmt(voiced_fraction)} "
            f"vs policy.min_voiced_fraction={_fmt(t.min_voiced_fraction)}",
        )
        return PolicyDecision(NOT_ENOUGH_EVIDENCE, reason, evidence)

    if pace_label == "unknown":
        reason = _REASON_TEMPLATES["nee_pace"]
        evidence = ("pace.label=unknown",)
        return PolicyDecision(NOT_ENOUGH_EVIDENCE, reason, evidence)

    # All gates passed. Classify on L = longest measured silence.
    #
    # The three bands below are DISJOINT by construction, so wait and respond
    # can never both apply (no tie is possible): respond requires L >=
    # respond_min, wait requires wait_min <= L < respond_min, clarify requires
    # L < wait_min. These ranges align with pauses.py's short/medium/long bands
    # (which use the same strict-less-than boundaries): clarify covers the
    # "short" range, wait covers the "medium" range, respond covers the "long"
    # range.
    L = longest_pause

    if L >= t.respond_pause_min_seconds:
        reason = _REASON_TEMPLATES["respond"].format(
            L=_fmt(L), respond_min=_fmt(t.respond_pause_min_seconds)
        )
        evidence = (
            f"pauses.longest_pause_seconds={_fmt(L)} "
            f"vs policy.respond_pause_min_seconds={_fmt(t.respond_pause_min_seconds)}",
            f"duration_seconds={_fmt(duration)} "
            f"vs policy.min_clip_seconds={_fmt(t.min_clip_seconds)}",
            f"pitch.voiced_fraction={_fmt(voiced_fraction)} "
            f"vs policy.min_voiced_fraction={_fmt(t.min_voiced_fraction)}",
        )
        return PolicyDecision(RESPOND, reason, evidence)

    if t.wait_pause_min_seconds <= L < t.respond_pause_min_seconds:
        reason = _REASON_TEMPLATES["wait"].format(
            L=_fmt(L),
            wait_min=_fmt(t.wait_pause_min_seconds),
            respond_min=_fmt(t.respond_pause_min_seconds),
        )
        evidence = (
            f"pauses.longest_pause_seconds={_fmt(L)} "
            f"vs policy.wait_pause_min_seconds={_fmt(t.wait_pause_min_seconds)}",
            f"pauses.longest_pause_seconds={_fmt(L)} "
            f"vs policy.respond_pause_min_seconds={_fmt(t.respond_pause_min_seconds)}",
            f"duration_seconds={_fmt(duration)} "
            f"vs policy.min_clip_seconds={_fmt(t.min_clip_seconds)}",
        )
        return PolicyDecision(WAIT, reason, evidence)

    if L < t.wait_pause_min_seconds and pause_count >= t.min_pause_count_for_clarify:
        reason = _REASON_TEMPLATES["clarify"].format(
            L=_fmt(L),
            wait_min=_fmt(t.wait_pause_min_seconds),
            pause_count=pause_count,
        )
        evidence = (
            f"pauses.longest_pause_seconds={_fmt(L)} "
            f"vs policy.wait_pause_min_seconds={_fmt(t.wait_pause_min_seconds)}",
            f"pauses.pause_count={pause_count} "
            f"vs policy.min_pause_count_for_clarify={t.min_pause_count_for_clarify}",
        )
        return PolicyDecision(CLARIFY, reason, evidence)

    # Fallthrough: L is below the wait band with too few pauses to clarify.
    reason = _REASON_TEMPLATES["nee_fallthrough"].format(
        L=_fmt(L), pause_count=pause_count
    )
    evidence = (
        f"pauses.longest_pause_seconds={_fmt(L)} "
        f"vs policy.wait_pause_min_seconds={_fmt(t.wait_pause_min_seconds)}",
        f"pauses.pause_count={pause_count} "
        f"vs policy.min_pause_count_for_clarify={t.min_pause_count_for_clarify}",
    )
    return PolicyDecision(NOT_ENOUGH_EVIDENCE, reason, evidence)


__all__ = [
    "CLARIFY",
    "NOT_ENOUGH_EVIDENCE",
    "PolicyDecision",
    "RECOMMENDATIONS",
    "RESPOND",
    "WAIT",
    "decide",
]
