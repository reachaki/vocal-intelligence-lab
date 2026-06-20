# Architecture

## Overview

The system converts local audio input into structured vocal context.

The early architecture is intentionally simple:

Audio file
→ audio loader
→ feature extraction
→ feature summary
→ conversation policy
→ JSON output

Optional transcript text can later be added:

Audio file + transcript
→ combined interpretation
→ conversation recommendation

## Main components

### Audio ingestion

Responsible for:
- loading local audio files
- validating supported formats
- extracting sample rate, channels, duration, and waveform data

### Feature extraction

Responsible for:
- loudness
- speech energy
- silence and pause regions
- pitch estimate
- pace estimate
- changes over time

### Feature summary

Responsible for converting raw numbers into interpretable labels.

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

The system should produce structured JSON.

Example:

{
  "duration_seconds": 8.4,
  "speech_rate_estimate": "fast",
  "volume_profile": "rising",
  "pause_pattern": "thinking_pause_detected",
  "pitch_profile": "animated",
  "conversation_recommendation": "wait",
  "reason": "Long pause detected after unfinished phrase; likely thinking."
}

## Design constraints

- Local-first
- Small enough for Apple Silicon development
- No required cloud GPU
- No paid APIs for early versions
- No private audio committed to source control
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
