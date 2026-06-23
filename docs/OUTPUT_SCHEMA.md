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
