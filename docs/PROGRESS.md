# Progress

This document tracks the current state of the project: the active phase, the latest implementation commit, the most recent review, the validation performed, known limitations, and the next approval gate.

## Current phase

Phase 3 — Audio preprocessing and canonicalisation (implemented; pending review).

## Latest implementation commit

`676985b` — Add synthetic audio fixture generators (merged to `main`).

Phase 3 audio preprocessing is proposed in the open pull request from `phase-3-audio-preprocessing`.

## Latest review status

In review — pull request open into `main`.

## Validation performed

- Mono downmix, DC-offset removal, and linear-interpolation resampling to a fixed target rate.
- The same signal sampled at two rates canonicalises to equivalent output (matched length, frequency, and high correlation).
- Two input gains canonicalise to equivalent output when peak normalisation is enabled.
- The duration guard warns above its configured ceiling and stays silent below it.
- A synthetic WAV is loaded and canonicalised end to end; missing and corrupt inputs raise clear errors.
- Test suite passes (`pytest`); the command-line shell runs (`python -m vocal_intel --version`, `--help`).
- The staged-file check rejects private audio and local-only files.

## Known limitations

- Resampling uses linear interpolation (numpy only); a higher-quality resampler can replace it when the feature-extraction libraries are introduced.
- Peak normalisation is opt-in; by default the absolute level is preserved so later loudness features remain meaningful.
- No feature extraction yet (no loudness, pause, pitch, voice-activity, or pace analysis).
- Feature-extraction libraries (for example librosa, scipy, scikit-learn) are not installed yet; they are introduced in later phases.

## Next approval gate

Merge of the Phase 3 pull request, then Phase 4 — Real-audio validation protocol.
