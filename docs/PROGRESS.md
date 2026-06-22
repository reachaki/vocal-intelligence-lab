# Progress

This document tracks the current state of the project: the active phase, the latest implementation commit, the most recent review, the validation performed, known limitations, and the next approval gate.

## Current phase

Phase 10 — Threshold calibration and versioned configuration (implemented; pending review).

## Latest implementation commit

`bc4d768` — Merge pull request #10 from reachaki/phase-9-speech-pace-estimation (merged to `main`).

Phase 10 threshold configuration is proposed in the open pull request from `phase-10-threshold-config`.

## Latest review status

In review — pull request open into `main`.

## Validation performed

- Qualitative thresholds for loudness, VAD, pauses, pitch, and pace are centralised in `src/vocal_intel/config.py`.
- Feature analysis outputs expose a `config_version` tied to the active threshold configuration.
- Deterministic tests verify that threshold edits through configuration change labels without editing feature modules.
- The calibration procedure is documented in `docs/THRESHOLD_CALIBRATION.md`.
- Invalid threshold configuration values raise clear errors before analysis.
- Test suite passes (`pytest`); the command-line shell runs (`python -m vocal_intel --version`, `--help`).
- The staged-file check rejects private audio and local-only files.

## Known limitations

- Threshold values remain provisional because private real-audio recordings are not tracked in the repository.
- The documented calibration procedure is ready for real-sample measurements, but checked-in values still preserve deterministic synthetic baselines.
- Feature analyses now stamp the threshold configuration version, but no unified schema output yet.
- Pace is analysed as an isolated feature; no conversation policy yet.
- Feature-extraction libraries (for example librosa, scipy, scikit-learn) are not installed yet; they are introduced in later phases.

## Next approval gate

Merge of the Phase 10 pull request, then Phase 11 — Unified feature summary and versioned output schema.
