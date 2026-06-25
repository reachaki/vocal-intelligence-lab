# Vocal Intelligence Lab

Vocal Intelligence Lab is a local-first research prototype for analysing speech beyond transcript text.

Most voice systems reduce speech into words. This project explores the extra information carried by spoken delivery: loudness, pitch, pace, rhythm, pauses, hesitation, intensity, and turn-taking signals.

The goal is to produce structured vocal context that can help a conversational system decide whether to wait, respond, clarify, interrupt politely, or challenge.

## Goals

- Analyse audio locally
- Canonicalise audio to a consistent form before analysis
- Extract vocal features from speech
- Detect pause and timing patterns
- Combine audio features with optional transcript text
- Produce explainable, versioned JSON output
- Validate with both synthetic and real local audio
- Run early prototypes on Apple Silicon without cloud GPU requirements

## Current status

An installable command-line tool. It can inspect a local audio file, summarise its
vocal features as versioned JSON, emit an opt-in conversation-timing recommendation,
and report neutral structural metadata for a local text transcript. The feature and
policy thresholds remain provisional, pending real-audio calibration.

## Commands

All commands read a single local file and print JSON to standard output. They run as
`vocal-intel <command> <path>` (or `python -m vocal_intel <command> <path>`).

- `inspect PATH` — Inspect a local audio file and print its metadata as JSON.
- `summarize PATH` — Summarise a local audio file's vocal features as versioned JSON
  (`schema_version` 1.0).
- `recommend PATH` — Emit the opt-in conversation-timing recommendation document
  (`schema_version` 1.1), pairing the feature summary with one provisional, rule-based
  timing label.
- `transcript-info PATH` — Report neutral structural metadata (character, word, and line
  counts) for a local plain-text transcript (`.txt` or `.md`). The transcript text itself
  is never included in the output, and this command does not affect the recommendation.

```
vocal-intel summarize audio.wav
vocal-intel recommend audio.wav
vocal-intel transcript-info transcript.txt
```

## Documentation

- [Project Plan](docs/PROJECT_PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Validation Plan](docs/VALIDATION_PLAN.md)
- [Project Brief](docs/PROJECT_BRIEF.md)
- [Progress](docs/PROGRESS.md)
- [Real-Audio Validation Protocol](docs/REAL_AUDIO_PROTOCOL.md)

## Development approach

The project is built in small validated phases. Each phase should include tests, a runnable demo, or a documented manual validation check.

## Development

The project targets Python 3.11 or newer. From a fresh checkout:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the test suite and the command-line shell:

```
pytest
vocal-intel --version
```

The command-line shell can also be run without installation:

```
python -m vocal_intel --version
```

A staged-file check helps keep private audio and local-only files out of version control, and can be used as a pre-commit hook:

```
python scripts/check_staged_files.py
```

## Privacy

Private voice recordings and local-only working files must not be committed to this repository. Real audio validation uses local-only files. Repository ignore rules cover audio file types and local-only files, and a staged-file check guards against accidental commits.
