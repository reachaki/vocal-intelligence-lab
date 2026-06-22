# Progress

This document tracks the current state of the project: the active phase, the latest implementation commit, the most recent review, the validation performed, known limitations, and the next approval gate.

## Current phase

Phase 8 — Pitch analysis (implemented; pending review).

## Latest implementation commit

`2d85552` — Merge pull request #8 from reachaki/phase-7-silence-pause-detection (merged to `main`).

Phase 8 pitch analysis is proposed in the open pull request from `phase-8-pitch-analysis`.

## Latest review status

In review — pull request open into `main`.

## Validation performed

- Pitch contour extraction uses frame-level autocorrelation with an explicit fundamental-frequency search range.
- Unvoiced frames are represented explicitly with `NaN` frequencies and boolean voiced-frame flags.
- A known synthetic tone is estimated within the documented frequency tolerance.
- Synthetic silence yields no voiced frames and unknown pitch labels.
- Synthetic rising and falling sweeps produce the expected trend labels.
- Pitch stability is computed over voiced frames only and mapped to provisional flat/animated delivery labels.
- Invalid input, invalid sample rates, bad search ranges, and invalid analysis thresholds raise clear errors.
- Test suite passes (`pytest`); the command-line shell runs (`python -m vocal_intel --version`, `--help`).
- The staged-file check rejects private audio and local-only files.

## Known limitations

- Pitch search range and label thresholds are provisional and documented; they are scheduled for data-driven, versioned calibration in a later phase.
- The autocorrelation estimator is dependency-light and validated on synthetic signals; real expressive-versus-monotone and question-versus-statement checks remain part of the manual real-audio protocol.
- Simple autocorrelation can produce octave errors on difficult real speech; this is not ruled out by synthetic tone tests.
- Unvoiced detection is energy- and clarity-threshold based, so noisy or breathy speech may produce missed or spurious voiced frames.
- No pace analysis, conversation policy, or unified schema output yet.
- Feature-extraction libraries (for example librosa, scipy, scikit-learn) are not installed yet; they are introduced in later phases.

## Next approval gate

Merge of the Phase 8 pull request, then Phase 9 — Speech pace estimation.
