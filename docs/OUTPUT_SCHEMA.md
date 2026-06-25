# Output schema (v1)

This document describes the unified feature-summary document produced for one
local audio clip. The document is emitted by `vocal-intel summarize PATH` and by
`vocal_intel.summary.summarize_file` / `summarize_canonical`.

The document carries two independent versions:

- `schema_version` — the shape and field set of this document. The current value
  is `"1.0"`.
- `config_version` — the threshold configuration the features were computed with
  (for example `"phase-10-provisional-v1"`). This is `ThresholdConfig.version`
  for the config that was threaded through every analysis.

All numbers are deterministic: numpy scalars are coerced to native Python
`int`/`float`, non-finite values (`NaN`/`Infinity`) are emitted as `null`, and
floating-point values are rounded to six decimals. The document is serialised
with stable, insertion-ordered keys (`json.dumps(..., indent=2,
ensure_ascii=True, sort_keys=False, separators=(",", ": "))`), so two summaries
of the same input serialise identically.

## Top-level fields

| Field | Type | Notes |
| --- | --- | --- |
| `schema_version` | string | Always `"1.0"` for this schema. |
| `config_version` | string | The threshold configuration version used. |
| `source` | object | Input descriptor (see below). |
| `duration_seconds` | float | Clip duration at the analysis rate, rounded to six decimals. |
| `loudness` | object | Loudness summary (see below). |
| `pauses` | object | Pause summary (see below). |
| `pitch` | object | Pitch summary (see below). |
| `pace` | object | Pace summary (see below). |
| `confidence` | string | Fixed value `"not_estimated"` in this version. |
| `limitations` | string | Fixed static caveat sentence. |
| `conversation_recommendation` | null | Reserved for a later phase; always `null` here. |
| `reason` | null | Reserved for a later phase; always `null` here. |
| `evidence` | array | Reserved for a later phase; always `[]` here. |
| `uncertainty` | object | Reserved for a later phase; always `{}` here. |

### `source`

| Field | Type | Notes |
| --- | --- | --- |
| `path` | string or null | The input path for `summarize_file`; `null` for `summarize_canonical`. |
| `sample_rate` | integer | The analysis/processing sample rate, not the original file rate. |

`sample_rate` is the canonical sample rate the features were actually computed
at (`CanonicalAudio.sample_rate`, always `16000` after preprocessing). It is the
same for both entry points, so both produce an identical schema. It is **not**
the original on-disk sample rate of the input file.

### `loudness`

| Field | Type | Allowed values / notes |
| --- | --- | --- |
| `label` | string | One of `"quiet"`, `"normal"`, `"loud"`. |
| `rms_dbfs` | float | Whole-signal RMS level in dBFS. |
| `peak_dbfs` | float | Peak amplitude in dBFS. |

The silence floor is `-120.0` dBFS, so fully silent input reports `-120.0` for
both `rms_dbfs` and `peak_dbfs` and a `"quiet"` label.

### `pauses`

Pause fields are taken from `analyze_pauses(vad, config=config).summary`, which
shares the single voice-activity segmentation. Leading and trailing silence are
not counted as pauses.

| Field | Type | Notes |
| --- | --- | --- |
| `pause_count` | integer | Number of detected inter-speech pauses. |
| `total_pause_seconds` | float | Sum of pause durations. |
| `longest_pause_seconds` | float | Longest single pause; `0.0` when there are none. |
| `short_count` | integer | Pauses labelled short. |
| `medium_count` | integer | Pauses labelled medium. |
| `long_count` | integer | Pauses labelled long. |

`PauseSummary.mean_pause_seconds` exists in the underlying analysis but is
intentionally excluded from this schema version.

### `pitch`

| Field | Type | Allowed values / notes |
| --- | --- | --- |
| `delivery_label` | string | One of `"flat"`, `"animated"`, `"unknown"`. |
| `trend_label` | string | One of `"rising"`, `"falling"`, `"stable"`, `"unknown"`. |
| `median_frequency_hz` | float or null | Median voiced frequency; `null` when there are no voiced frames. |
| `voiced_fraction` | float | Fraction of frames classified as voiced (`0.0` for silence). |

On silent or unvoiced input the numeric `median_frequency_hz` is `null` and both
labels are `"unknown"`.

### `pace`

| Field | Type | Allowed values / notes |
| --- | --- | --- |
| `label` | string | One of `"slow"`, `"normal"`, `"fast"`, `"unknown"`. |
| `syllable_rate_per_second` | float or null | Syllable rate over speech-active time; `null` when there is no speech. |
| `speech_active_seconds` | float | Total speech-active duration (`0.0` for silence). |

On silent input `syllable_rate_per_second` is `null`, `speech_active_seconds` is
`0.0`, and `label` is `"unknown"`.

## Reserved fields

`confidence` is the fixed string `"not_estimated"` in this version (its closed
vocabulary is `{"not_estimated"}`). `limitations` is a fixed static sentence:

> Single-speaker, signal-level estimates; thresholds provisional pending
> real-audio calibration; no transcript or conversation policy.

`conversation_recommendation`, `reason`, `evidence`, and `uncertainty` are
reserved for a later phase and are emitted as fixed empty sentinels (`null`,
`null`, `[]`, `{}`). There is no logic behind them in this version.

## Schema stability

The field set and order are frozen by a golden manifest
(`tests/data/schema_manifest_v1.json`) and an order-sensitive drift test. Any
intended change to the field set or order requires bumping `SCHEMA_VERSION` and
regenerating that manifest in the same change.

# Schema v1.1 (recommend output)

This is a separate document, emitted by the opt-in `vocal-intel recommend PATH`
command and by `vocal_intel.recommend.recommend_file` /
`build_recommendation_document`. It is **not** a semantic upgrade of the v1.0
`summarize` document: it is a distinct document produced by a distinct command.
Its `schema_version` is `"1.1"`.

The v1.1 document carries the same feature blocks as v1.0 plus a populated,
provisional conversation-timing label from the policy core. It has 28 ordered
field-paths, frozen by `tests/data/schema_manifest_recommend_v1_1.json`.

## Top-level fields (v1.1)

| Field | Type | Notes |
| --- | --- | --- |
| `schema_version` | string | Always `"1.1"` for this document. |
| `config_version` | string | The threshold configuration version used for the FEATURE blocks (same value as v1.0). |
| `policy_config_version` | string | The conversation-policy threshold version used for the recommendation. Present only on v1.1. |
| `source` | object | Input descriptor; see the v1.0 [`source`](#source) table. |
| `duration_seconds` | float | Clip duration; see v1.0. |
| `loudness` | object | Loudness summary; see the v1.0 [`loudness`](#loudness) table. |
| `pauses` | object | Pause summary; see the v1.0 [`pauses`](#pauses) table. |
| `pitch` | object | Pitch summary; see the v1.0 [`pitch`](#pitch) table. |
| `pace` | object | Pace summary; see the v1.0 [`pace`](#pace) table. |
| `confidence` | string | Fixed value `"not_estimated"` in this version. |
| `limitations` | string | Fixed caveat sentence; see below. |
| `conversation_recommendation` | string | One of `"wait"`, `"respond"`, `"clarify"`, `"not_enough_evidence"`. |
| `reason` | string | A non-empty, closed-template explanation of the recommendation. |
| `evidence` | array of strings | Ordered factual comparisons; **always non-empty** in v1.1, including for `not_enough_evidence`. |
| `uncertainty` | object | Reserved; always `{}` in this version. |

The `source`, `duration_seconds`, `loudness`, `pauses`, `pitch`, and `pace`
blocks are produced by the same `summary` code as v1.0 and reused verbatim — they
are the single source of truth and are not duplicated or recomputed here. Refer
to the v1.0 tables above for their fields.

`conversation_recommendation` is a LABEL of a measured pause band, not advice. It
describes the longest measured silence and the provisional rule that maps it to a
timing action; it makes no inference about the speaker. The recommendation values
and the policy rules are documented in `docs/CONVERSATION_POLICY.md`. The reserved
policy actions `interrupt_politely` and `challenge` are never produced.

The fixed `limitations` sentence for v1.1 is:

> Single-speaker, signal-level estimates; thresholds provisional pending
> real-audio calibration. The conversation recommendation is a provisional,
> rule-based label derived from whole-clip signal measurements (clip duration,
> voiced fraction, detected speech presence, and the longest measured silence);
> it is a description of measured audio, makes no inference about the speaker, and
> is not a validated behavioural claim.

## Telling the two documents apart

`schema_version` is the SOLE discriminator between the two documents.

- `"1.0"` (from `summarize`): `conversation_recommendation` and `reason` are
  `null`, `evidence` is `[]`, `uncertainty` is `{}`, and there is **no**
  `policy_config_version` field.
- `"1.1"` (from `recommend`): `conversation_recommendation`, `reason`, and
  `evidence` are populated, and `policy_config_version` is present.

Notes for consumers:

- `config_version` is NOT a discriminator — it is identical across both documents
  and governs the FEATURE thresholds. `policy_config_version` governs the
  RECOMMENDATION thresholds and is present iff `schema_version >= 1.1`.
- `evidence` is ALWAYS non-empty in v1.1 (including for `not_enough_evidence`).
  Branch on `conversation_recommendation`, never on whether `evidence` is empty.
- v1.0 and v1.1 are DISTINCT documents from DISTINCT commands, not a semver
  upgrade path. A v1.0-only parser must not be fed a v1.1 document.

## Schema stability (v1.1)

The v1.1 field set and order are frozen by a golden manifest
(`tests/data/schema_manifest_recommend_v1_1.json`) and an order-sensitive drift
test, the same way v1.0 is. Any intended change requires bumping
`RECOMMEND_SCHEMA_VERSION` and regenerating that manifest in the same change.
