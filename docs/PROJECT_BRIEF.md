# Vocal Intelligence Lab

## Vision

Build a prototype AI speech-understanding system that goes beyond text.

Current voice assistants mostly receive final transcribed text after the user stops speaking. This project explores real-time or near-real-time vocal intelligence: tone, pitch, volume, pace, pauses, intensity, hesitation, interruption timing, and conversational state.

The goal is NOT to build a full ChatGPT competitor.

The goal is to build a research/developer prototype that can:

1. Record or ingest audio.
2. Extract speech/audio features.
3. Detect useful vocal patterns:
   - loud vs soft
   - fast vs slow
   - long pause vs short pause
   - rising/falling pitch
   - energetic vs calm delivery
   - possible frustration/excitement/hesitation
4. Combine these signals with transcript text.
5. Decide conversational behaviour:
   - wait
   - respond
   - ask a clarification
   - interrupt politely (reserved; not implemented)
   - challenge the user (reserved; not implemented)
   - let the user think
6. Produce a structured JSON output that another AI system could use.

## Hardware target

Primary development machine:
- Apple Silicon M1 MacBook Air
- No dedicated NVIDIA GPU
- Must work locally for basic prototype
- No cloud GPU required for Phase 1-5

## Important constraints

- Do not train huge models.
- Do not download massive datasets without asking.
- Do not require paid APIs.
- Do not require secrets.
- Do not break the repo.
- Keep each phase small and committed separately.
- After each phase, stop and provide:
  - what changed
  - commands run
  - tests run
  - current limitations
  - next recommended phase

## Preferred stack

- Python
- librosa/soundfile/scipy for audio features
- scikit-learn for small baseline models
- pytest for tests
- CLI-first prototype
- Later: web dashboard or live microphone stream

## Success definition

A working local prototype where I can provide an audio file and receive output like:

{
  "schema_version": "1.0",
  "config_version": "1.0",
  "transcript": "optional placeholder",
  "duration_seconds": 8.4,
  "speech_rate_estimate": "fast",
  "volume_profile": "rising",
  "pause_pattern": "medium_pause",
  "pitch_profile": "animated",
  "conversation_recommendation": "wait",
  "reason": "A trailing silence of 0.6 s was measured within the medium pause band; under the provisional timing rules this maps to wait."
}

The current implementation produces `wait`, `respond`, `clarify`, and `not_enough_evidence` for the `conversation_recommendation` field; `interrupt_politely` and `challenge` are reserved and not implemented. These recommendations and their reasons are strictly signal-level descriptions of measured audio features and make no inference about a speaker's emotions, intent, or state of mind. All output conforms to a single versioned schema.
