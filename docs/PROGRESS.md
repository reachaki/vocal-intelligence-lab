# Progress

This document tracks the current state of the project: the active phase, the latest implementation commit, the most recent review, the validation performed, known limitations, and the next approval gate.

## Current phase

Phase 5 — Loudness and energy analysis (implemented; pending review).

## Latest implementation commit

`a136ce9` — Add real-audio validation protocol (merged to `main`).

Phase 5 loudness and energy analysis is proposed in the open pull request from `phase-5-loudness-energy-analysis`.

## Latest review status

In review — pull request open into `main`.

## Validation performed

- Frame-level RMS energy, peak amplitude, and dBFS summary statistics, with loudness-over-time and quiet/loud section detection.
- Quiet versus loud synthetic fixtures verified for energy ordering and RMS values within a documented numeric tolerance.
- Provisional quiet / normal / loud labels verified on quiet, mid, and loud synthetic signals; a relative comparison helper confirms soft-versus-loud ordering independent of thresholds.
- Loudness analysis runs on canonicalised audio and preserves the absolute level (no silent peak normalisation).
- Invalid input (non-mono, empty, bad sample rate, bad frame length) raises a clear error.
- Test suite passes (`pytest`); the command-line shell runs (`python -m vocal_intel --version`, `--help`).
- The staged-file check rejects private audio and local-only files.

## Known limitations

- The quiet / normal / loud thresholds are provisional dBFS placeholders chosen against synthetic tones; absolute labels depend on capture conditions and are scheduled for data-driven, versioned calibration in a later phase.
- Validated on synthetic fixtures only; real soft-versus-loud comparison against pre-registered labels is part of the manual real-audio protocol.
- No pause, pitch, voice-activity, pace analysis, or conversation policy yet.
- Feature-extraction libraries (for example librosa, scipy, scikit-learn) are not installed yet; they are introduced in later phases.

## Next approval gate

Merge of the Phase 5 pull request, then Phase 6 — Voice activity detection and noise-floor estimation.
