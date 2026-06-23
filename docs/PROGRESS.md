# Progress

This document tracks the current state of the project: the active phase, the latest implementation commit, the most recent review, the validation performed, known limitations, and the next approval gate.

## Current phase

Phase 11 — Unified feature summary and versioned output schema (implemented; pending review).

## Latest implementation commit

`1c4fb54` — Add versioned threshold configuration (merged to `main` via the Phase 10 pull request).

Phase 11 adds `src/vocal_intel/summary.py`, a `summarize` CLI subcommand, the
`docs/OUTPUT_SCHEMA.md` reference, and the `tests/data/schema_manifest_v1.json`
drift fixture on the `phase-11-unified-feature-summary` branch.

## Latest review status

In review — pull request to be opened into `main`.

## Validation performed

- One config object is threaded through loudness, voice activity, pauses, pitch, and pace so the document's `config_version` matches every feature's stamped version.
- The summary combines existing feature outputs only; it adds no new signal-processing math.
- Output is deterministic: numpy scalars are coerced to native Python types, non-finite values become `null`, floats are rounded to six decimals, and serialisation uses fixed insertion-ordered settings.
- A golden field-path manifest and an order-sensitive drift test guard the schema against accidental add, remove, rename, or reorder.
- Reserved recommendation, reason, evidence, and uncertainty fields are emitted as fixed empty sentinels with no logic behind them.
- The `summarize` command exits 0 with JSON on valid input and exits 1 with an `error:` message on a missing, empty, or corrupt file, reusing the existing ingestion errors.
- `inspect` output is unchanged; test suite passes (`pytest`); the command-line shell runs (`python -m vocal_intel --version`, `--help`).
- The staged-file check rejects private audio and local-only files.

## Known limitations

- Threshold values remain provisional because private real-audio recordings are not tracked in the repository.
- The documented calibration procedure is ready for real-sample measurements, but checked-in values still preserve deterministic synthetic baselines.
- A unified versioned summary schema is now emitted, but the conversation policy and recommendation fields are reserved and empty.
- Feature-extraction libraries (for example librosa, scipy, scikit-learn) are not installed yet; they are introduced in later phases.

## Next approval gate

Review and merge of the Phase 11 pull request, then Phase 12 — conversation policy and recommendation.
