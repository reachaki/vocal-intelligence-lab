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
   - interrupt politely
   - challenge the user
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
  "pause_pattern": "thinking_pause_detected",
  "pitch_profile": "animated",
  "conversation_recommendation": "wait",
  "reason": "User paused briefly after unfinished phrase with low falling energy, likely thinking."
}

The `conversation_recommendation` field is one of a fixed set of values: `wait`, `respond`, `clarify`, `interrupt_politely`, `challenge`. All output conforms to a single versioned schema.
