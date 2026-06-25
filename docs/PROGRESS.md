# Progress

This document tracks the current state of the project: the active phase, the validation performed, known limitations, and the next approval gate.

## Current phase

No phase is currently in review.

Phase 11 (the unified feature summary and versioned output schema), the continuous-integration workflow, Phase 12 (the deterministic policy core in `src/vocal_intel/policy.py`), Phase 12b (the opt-in `recommend` command), and Phase 13a (the opt-in `transcript-info` command) are merged to `main`.

Phase 13a added a new, opt-in `transcript-info` command that reads a user-supplied local plain-text file (`.txt` or `.md`, UTF-8) and emits a separate `transcript_metadata` document (`schema_version` 1.0) carrying neutral structural counts only: `character_count`, `word_count`, and `line_count`, plus the source path and format. The transcript text itself is never included in the output, no content analysis or inference is performed, and the document does not affect the conversation recommendation. The `summarize` (1.0) and `recommend` (1.1) documents are unchanged.

## Validation performed

- New deterministic tests pin the `transcript_metadata` document shape and field order against a committed golden manifest, pin exact character, word, and line counts for fixed synthetic inputs (including a multibyte code point, a CRLF line ending, and whitespace-only text), and confirm error parity with the other commands (missing file, unsupported extension, non-UTF-8 content, and an oversize file).
- Safety tests confirm the transcript text never leaks into the output, that the new module imports none of the audio, summary, recommendation, or policy code, and that the output carries no inference vocabulary or fields.
- The existing test suite still passes; the `summarize` (1.0) and `recommend` (1.1) outputs are unchanged.

## Known limitations

- The `transcript-info` command accepts only local plain-text `.txt`/`.md` files; structured caption and subtitle formats are out of scope.
- The transcript counts are structural only; they make no linguistic or behavioural claim and do not influence any recommendation.
- The policy thresholds and the whole-clip pause-to-timing mapping are provisional, pending the real-audio validation run.
- The `uncertainty` and `confidence` fields remain reserved and are not estimated; `interrupt_politely` and `challenge` are reserved and not produced.

## Next approval gate

None open. The next phase has not been selected.
