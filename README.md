# Vocal Intelligence Lab

Vocal Intelligence Lab is a local-first research prototype for analysing speech beyond transcript text.

Most voice systems reduce speech into words. This project explores the extra information carried by spoken delivery: loudness, pitch, pace, rhythm, pauses, hesitation, intensity, and turn-taking signals.

The goal is to produce structured vocal context that can help a conversational system decide whether to wait, respond, clarify, interrupt politely, or challenge.

## Goals

- Analyse audio locally
- Extract vocal features from speech
- Detect pause and timing patterns
- Combine audio features with optional transcript text
- Produce explainable JSON output
- Validate with both synthetic and real local audio
- Run early prototypes on Apple Silicon without cloud GPU requirements

## Current status

Planning and project foundation.

## Documentation

- [Project Plan](docs/PROJECT_PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Validation Plan](docs/VALIDATION_PLAN.md)
- [Project Brief](docs/PROJECT_BRIEF.md)

## Development approach

The project is built in small validated phases. Each phase should include tests, a runnable demo, or a documented manual validation check.

## Privacy

Private voice recordings should not be committed to this repository. Real audio validation should use local-only files.
