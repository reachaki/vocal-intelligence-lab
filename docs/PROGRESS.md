# Progress

This document tracks the current state of the project: the active phase, the latest implementation commit, the most recent review, the validation performed, known limitations, and the next approval gate.

## Current phase

Phase 6 — Voice activity detection and noise-floor estimation (implemented; pending review).

## Latest implementation commit

`4441b12` — Add loudness and energy analysis (merged to `main`).

Phase 6 voice activity detection is proposed in the open pull request from `phase-6-vad-noise-floor`.

## Latest review status

In review — pull request open into `main`.

## Validation performed

- Noise-floor estimation from a low percentile of frame-level RMS energy, with a relative, noise-aware speech threshold.
- Speech/non-speech segmentation with minimum-duration smoothing; segments expose start, end, duration, and label.
- Silence-only audio yields no speech; an active region in silence is detected with onset and offset within a documented tolerance.
- A quiet background with a louder active region isolates the active region; the known pause-gap fixture yields two speech segments around the gap.
- Short blips are smoothed away; segmentation is stable across a clean and an added-noise version of the same clip.
- Invalid input (non-mono, empty, bad sample rate) raises a clear error.
- Test suite passes (`pytest`); the command-line shell runs (`python -m vocal_intel --version`, `--help`).
- The staged-file check rejects private audio and local-only files.

## Known limitations

- Thresholds (noise-floor percentile and the dB margin) are provisional and documented; they are scheduled for data-driven, versioned calibration in a later phase.
- The noise floor is estimated from the quietest frames, so input is expected to contain some ambient/non-speech regions; a uniformly energetic clip has no quiet reference and is treated as non-speech.
- Validated on synthetic fixtures only; real-speech validation is part of the manual real-audio protocol.
- No pause classification, pitch, pace analysis, or conversation policy yet (this phase provides the shared segmentation those will consume).
- Feature-extraction libraries (for example librosa, scipy, scikit-learn) are not installed yet; they are introduced in later phases.

## Next approval gate

Merge of the Phase 6 pull request, then Phase 7 — Silence and pause detection.
