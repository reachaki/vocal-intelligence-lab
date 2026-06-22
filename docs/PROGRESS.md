# Progress

This document tracks the current state of the project: the active phase, the latest implementation commit, the most recent review, the validation performed, known limitations, and the next approval gate.

## Current phase

Phase 9 — Speech pace estimation (implemented; pending review).

## Latest implementation commit

`0dd8f2e` — Merge pull request #9 from reachaki/phase-8-pitch-analysis (merged to `main`).

Phase 9 speech pace estimation is proposed in the open pull request from `phase-9-speech-pace-estimation`.

## Latest review status

In review — pull request open into `main`.

## Validation performed

- Speech-active duration is summed from shared VAD speech segments and excludes leading, trailing, and internal non-speech regions.
- Syllable-like energy nuclei are estimated from a smoothed frame-RMS envelope inside speech-active regions.
- Synthetic pulse trains with known nucleus counts produce expected slow, normal, and fast labels.
- A pause-separated synthetic clip is normalised by speech-active time, not total clip duration.
- A leading/trailing-silence synthetic clip can consume regions from the shared VAD detector.
- No-speech input yields no syllable estimate and an unknown pace label.
- Invalid input, invalid VAD segments, bad frame settings, and invalid analysis thresholds raise clear errors.
- Test suite passes (`pytest`); the command-line shell runs (`python -m vocal_intel --version`, `--help`).
- The staged-file check rejects private audio and local-only files.

## Known limitations

- Syllable-rate label thresholds are provisional and documented; they are scheduled for data-driven, versioned calibration in a later phase.
- The envelope-nucleus estimator is dependency-light and validated on deterministic synthetic pulse trains; real script-read validation against measured words per minute remains part of the manual real-audio protocol.
- The method estimates syllable-like acoustic peaks, not lexical syllables or words; sustained vowels, clipped speech, background noise, or unusual articulation may produce missed or spurious nuclei.
- Pace is analysed as an isolated feature; no conversation policy or unified schema output yet.
- Feature-extraction libraries (for example librosa, scipy, scikit-learn) are not installed yet; they are introduced in later phases.

## Next approval gate

Merge of the Phase 9 pull request, then Phase 10 — Threshold calibration and versioned configuration.
