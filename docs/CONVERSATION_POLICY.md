# Conversation timing policy

## Purpose

The conversation timing policy is a deterministic, rule-based heuristic that
maps one clip's measured vocal features to a single timing action. It is
strictly signal-level: it reads only measured quantities (clip duration, the
longest measured silence, the measured pause count, the voiced fraction, and the
pace label) and applies fixed numeric comparisons.

The policy makes no inference about a speaker. It says nothing about emotions,
intent, truthfulness, attention, or any internal state. A recommendation
describes a measured pause and the provisional rule that maps it to an action,
and nothing more.

## Outputs

The policy produces exactly one of four values:

- `wait` — the longest measured silence falls in the medium band.
- `respond` — the longest measured silence is at or above the long-pause
  threshold.
- `clarify` — the longest measured silence is short but several pauses were
  measured (a mixed pattern).
- `not_enough_evidence` — the conservative default. It is produced whenever a
  required signal is weak or absent, or when the pause pattern matches no rule.

`not_enough_evidence` is the hard default: any failing gate, or any pause
pattern outside the three classified bands, resolves to it.

## Gates

Before any pause classification, three gates must pass. A failing gate yields
`not_enough_evidence` with its own reason. Thresholds are read from the
versioned configuration (`conversation_policy`) and are provisional.

- G1 — clip duration is at least `min_clip_seconds` (default 0.6 s).
- G2 — voiced fraction is at least `min_voiced_fraction` (default 0.3).
- G3 — a speech-active region was detected (pace label is not `unknown`).

## Classification rules

When all gates pass, the policy classifies on `L`, the longest measured silence
in seconds. The three bands are disjoint by construction, so `wait` and
`respond` can never both apply (no tie is possible). The bands align with the
short / medium / long pause ranges used elsewhere in the project, which use the
same strict-less-than boundaries.

- `respond` — `L >= respond_pause_min_seconds` (default 1.0 s); the long band.
- `wait` — `wait_pause_min_seconds <= L < respond_pause_min_seconds`
  (default 0.5 s up to 1.0 s); the medium band.
- `clarify` — `L < wait_pause_min_seconds` and the measured pause count is at
  least `min_pause_count_for_clarify` (default 2); short pauses, mixed pattern.
- `not_enough_evidence` — otherwise (for example a short longest silence with
  too few measured pauses to classify a mixed pattern).

## Provisional thresholds

| Threshold | Default | Meaning |
| --- | --- | --- |
| `min_clip_seconds` | 0.60 | Minimum clip duration to assess timing |
| `min_voiced_fraction` | 0.30 | Minimum voiced fraction to assess timing |
| `wait_pause_min_seconds` | 0.50 | Lower edge of the wait band |
| `respond_pause_min_seconds` | 1.00 | Lower edge of the respond band |
| `min_pause_count_for_clarify` | 2 | Pause count needed for the clarify rule |

These values are sourced from `conversation_policy` in the versioned
configuration. They are provisional (see Limitations).

## Reason and evidence format

Every decision carries a non-empty `reason` chosen from a closed set of
templates keyed by the decision branch; no free-form text is produced. Every
number embedded in a reason is rounded to six decimals, with `-0.0` normalised
to `0.0`, so equal values render identically.

Each decision also carries an ordered `evidence` list. Each entry is a short
factual comparison of the form `<dotted_field>=<value> vs
<threshold_name>=<value>`, with numbers rounded the same way. The ordering is
fixed so the output is byte-stable.

## Worked examples

The inputs below are hand-authored synthetic feature values, not real
recordings. Paths shown are placeholders.

### Example 1 — respond

Input: `clip.wav`, duration 8.4 s, longest measured silence 1.2 s, voiced
fraction 0.55, pace label `normal`.

- Gates pass; `L = 1.2 >= 1.0`.
- Recommendation: `respond`.
- Reason: "Longest measured silence was 1.2 s, at or above the respond
  threshold of 1.0 s; the provisional timing rule maps this to respond."

### Example 2 — wait

Input: `sample.wav`, duration 6.0 s, longest measured silence 0.7 s, voiced
fraction 0.45, pace label `normal`.

- Gates pass; `0.5 <= 0.7 < 1.0`.
- Recommendation: `wait`.
- Reason: "Longest measured silence was 0.7 s, within the wait band from 0.5 s
  up to 1.0 s; the provisional timing rule maps this to wait."

### Example 3 — clarify

Input: `take.wav`, duration 5.0 s, longest measured silence 0.3 s, measured
pause count 3, voiced fraction 0.40, pace label `fast`.

- Gates pass; `L = 0.3 < 0.5` and pause count `3 >= 2`.
- Recommendation: `clarify`.

### Example 4 — not enough evidence (gate failure)

Input: `short.wav`, duration 0.4 s, voiced fraction 0.55, pace label `normal`.

- G1 fails: `0.4 < 0.6`.
- Recommendation: `not_enough_evidence`.
- Reason: "Clip duration 0.4 s is below the minimum of 0.6 s needed to assess
  timing; not enough evidence."

### Example 5 — not enough evidence (no rule matched)

Input: `quiet.wav`, duration 7.0 s, longest measured silence 0.3 s, measured
pause count 1, voiced fraction 0.50, pace label `normal`.

- Gates pass, but `L = 0.3 < 0.5` and pause count `1 < 2`.
- Recommendation: `not_enough_evidence`.

## Reserved values

`interrupt_politely` and `challenge` are reserved for a future, separately
scoped iteration. They are NOT implemented by this policy and are never
produced.

## Limitations

The thresholds and the whole-file pause-to-timing mapping are provisional. They
preserve a conservative default and have not been validated against real
recordings. They are pending the real-audio validation run and are not
validated behavioural claims. The policy operates on whole-clip aggregates only
and describes measured audio features, never the speaker.
