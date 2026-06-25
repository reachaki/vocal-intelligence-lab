# Architecture

## Overview

The system converts local audio input into structured vocal context.

The early architecture is intentionally simple:

Audio file
→ audio loader
→ preprocessing and canonicalisation
→ voice activity detection and noise floor
→ feature extraction
→ feature summary
→ conversation policy
→ versioned JSON output

Optional transcript text can later be added:

Audio file + transcript
→ combined interpretation
→ conversation recommendation

As shipped, transcript support is metadata only: the `transcript-info` command
reports neutral structural counts for a local text file and does not feed the
conversation recommendation. The combined-interpretation path above is a future
direction that would require separate, explicit approval.

## Main components

### Audio ingestion

Responsible for:
- loading local audio files
- validating supported formats
- reporting clear errors for unsupported or malformed files
- extracting sample rate, channels, duration, and waveform data

### Audio preprocessing

Responsible for converting arbitrary input into a consistent internal form:
- mono downmix
- resampling to a fixed target sample rate
- DC-offset removal
- optional peak normalisation that preserves meaningful loudness features
- a duration guard with a supported-length ceiling

### Voice activity detection and noise floor

Responsible for a single shared speech/non-speech segmentation, reused by pause detection, pace estimation, and the event timeline:
- noise-floor estimation
- a relative, noise-aware speech threshold
- segmentation with minimum-duration smoothing

### Feature extraction

Responsible for:
- loudness
- speech energy
- silence and pause regions, derived from the segmentation
- pitch estimate, with explicit voiced/unvoiced handling
- pace estimate, normalised by speech-active time
- changes over time

### Threshold configuration

Responsible for the numeric cut-points behind every qualitative label:
- a single versioned configuration file shared by all label code
- cut-points derived from the real-sample set
- a configuration version stamped into outputs

### Feature summary

Responsible for converting raw numbers into interpretable labels, using the cut-points from the threshold configuration.

Examples:
- loudness: soft, normal, loud
- pace: slow, normal, fast
- pitch: flat, animated
- pauses: few, many, long thinking pause

### Conversation policy

Responsible for producing an action recommendation.

Recommendations produced by the live policy:
- wait
- respond
- clarify
- not_enough_evidence (the conservative default)

`interrupt_politely` and `challenge` are reserved for a future, separately
scoped iteration; they are never produced by the current policy.

The policy must be explainable. Every recommendation includes a reason.

### Output schema

The system produces structured JSON under a two-document contract. The
`summarize` command emits `schema_version` 1.0 (features only; the recommendation
fields are reserved empty sentinels). The opt-in `recommend` command emits
`schema_version` 1.1 (the same feature blocks plus a populated conversation
recommendation, and a `policy_config_version`). Both documents share the same
feature-block sub-schemas — `source`, `loudness`, `pauses`, `pitch`, `pace` — and
differ only in the top-level version and in whether the recommendation fields are
populated. The two cannot drift apart because those feature blocks are produced
by the same `summary` code and reused verbatim. Every output carries a
`schema_version` and a `config_version` that identifies the threshold
configuration in use.

In the 1.1 document the `conversation_recommendation` field is one of a fixed set
of values: `wait`, `respond`, `clarify`, `not_enough_evidence`. The reserved
actions `interrupt_politely` and `challenge` are never produced.

Example (the `summarize` output; `conversation_recommendation` and the other
reserved fields are populated in a later phase):

{
  "schema_version": "1.0",
  "config_version": "phase-10-provisional-v1",
  "source": { "path": "clip.wav", "sample_rate": 16000 },
  "duration_seconds": 8.4,
  "loudness": { "label": "loud", "rms_dbfs": -12.0412, "peak_dbfs": -6.0206 },
  "pauses": {
    "pause_count": 1,
    "total_pause_seconds": 0.9,
    "longest_pause_seconds": 0.9,
    "short_count": 0,
    "medium_count": 1,
    "long_count": 0
  },
  "pitch": {
    "delivery_label": "animated",
    "trend_label": "rising",
    "median_frequency_hz": 198.4,
    "voiced_fraction": 0.62
  },
  "pace": { "label": "fast", "syllable_rate_per_second": 5.4, "speech_active_seconds": 6.1 },
  "confidence": "not_estimated",
  "limitations": "Single-speaker, signal-level estimates; thresholds provisional pending real-audio calibration; no transcript or conversation policy.",
  "conversation_recommendation": null,
  "reason": null,
  "evidence": [],
  "uncertainty": {}
}

The full field reference is in `docs/OUTPUT_SCHEMA.md`.

## Design constraints

- Local-first
- Small enough for Apple Silicon development
- No required cloud GPU
- No paid APIs for early versions
- No private audio or local-only files committed to source control
- Qualitative labels driven by a single versioned configuration
- A single versioned schema for all structured output
- Simple CLI before UI
- Measurable behaviour before visual polish

## Future architecture

Possible later architecture:

Live microphone stream
→ chunk processor
→ rolling vocal feature state
→ event timeline
→ conversation policy
→ external conversational system

This would allow near-real-time turn-taking decisions.
