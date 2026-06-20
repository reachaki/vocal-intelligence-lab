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

Possible recommendations:
- wait
- respond
- clarify
- interrupt_politely
- challenge

The policy must be explainable. Every recommendation should include a reason.

### Output schema

The system produces structured JSON that conforms to a single versioned schema. Every output carries a `schema_version`, and a `config_version` that identifies the threshold configuration in use. All JSON-emitting components share the same schema definition so the contract cannot drift between them.

The `conversation_recommendation` field is one of a fixed set of values: `wait`, `respond`, `clarify`, `interrupt_politely`, `challenge`.

Example:

{
  "schema_version": "1.0",
  "config_version": "1.0",
  "duration_seconds": 8.4,
  "speech_rate_estimate": "fast",
  "volume_profile": "rising",
  "pause_pattern": "thinking_pause_detected",
  "pitch_profile": "animated",
  "conversation_recommendation": "wait",
  "reason": "Long pause detected after unfinished phrase; likely thinking.",
  "confidence": "medium",
  "limitations": "Single-speaker calibration; pace is a signal-level estimate."
}

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
