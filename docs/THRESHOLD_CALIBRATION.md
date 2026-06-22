# Threshold Calibration

Phase 10 centralises qualitative label thresholds in `src/vocal_intel/config.py`.
The default values preserve the earlier feature-phase behaviour and are marked
as provisional until the real-audio validation set is large enough to calibrate
against measured labels.

## Configuration Version

The active configuration version is `phase-10-provisional-v1`. Feature analysis
results expose this value as `config_version` so downstream records can be tied
back to the thresholds that produced their labels.

## Current Threshold Families

- Loudness: quiet / normal / loud dBFS cut-points.
- Voice activity: noise-floor percentile, speech margin, and short-run smoothing
  cut-points.
- Pauses: minimum internal pause duration and short / medium / long boundaries.
- Pitch: search range, voicing threshold, flat / animated stability boundary,
  and rising / falling trend boundaries.
- Pace: slow / normal / fast syllable-rate boundaries and nucleus detection
  cut-points.

## Calibration Procedure

1. Capture real-audio samples using `docs/REAL_AUDIO_PROTOCOL.md`.
2. Record the pre-registered intended labels before running analysis.
3. Run the feature analyzers and keep the emitted `config_version` with each
   result record.
4. Compare predicted labels with intended labels and objective anchors such as
   measured words per minute for pace.
5. Adjust only `src/vocal_intel/config.py` when thresholds need to move.
6. Re-run the deterministic test suite and the real-audio validation checklist.
7. If thresholds change, increment `CONFIG_VERSION` and document the rationale.

## Current Limitation

The repository does not track private recordings, so the checked-in defaults are
not yet data-derived from real speakers. They remain deterministic synthetic
baselines until the real-audio validation set is collected outside version
control.
