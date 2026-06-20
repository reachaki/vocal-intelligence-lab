# Progress

This document tracks the current state of the project: the active phase, the latest implementation commit, the most recent review, the validation performed, known limitations, and the next approval gate.

## Current phase

Phase 4 — Real-audio validation protocol (implemented; pending review).

## Latest implementation commit

`f927e5c` — Add audio preprocessing and canonicalisation (merged to `main`).

Phase 4 real-audio validation protocol is proposed in the open pull request from `phase-4-real-audio-validation-protocol`.

## Latest review status

In review — pull request open into `main`.

## Validation performed

- A documented real-audio validation protocol (`docs/REAL_AUDIO_PROTOCOL.md`) defines the sample categories, pre-registered labels, objective anchors, storage, and privacy and retention rules.
- A manual result template (`docs/templates/real-audio-result-template.md`) records results in discrete fields.
- The result-record format and label vocabularies are checked by `vocal_intel.protocol`, with tests for valid records, missing fields, bad labels, and the words-per-minute anchor.
- The designated recordings directory (`recordings/`) is confirmed ignored by version control.
- Test suite passes (`pytest`); the command-line shell runs (`python -m vocal_intel --version`, `--help`).
- The staged-file check rejects private audio and local-only files.

## Known limitations

- The protocol is manual; it documents how to record, label, and check real audio but performs no analysis.
- Real recordings, labels, and results stay local only and are never committed, so the real-audio pass is reproduced per machine rather than in shared CI.
- No feature extraction yet (no loudness, pause, pitch, voice-activity, or pace analysis).
- Feature-extraction libraries (for example librosa, scipy, scikit-learn) are not installed yet; they are introduced in later phases.

## Next approval gate

Merge of the Phase 4 pull request, then Phase 5 — Loudness and energy analysis.
