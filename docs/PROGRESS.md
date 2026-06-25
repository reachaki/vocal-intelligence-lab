# Progress

This document tracks the current state of the project: the active phase, the validation performed, known limitations, and the next approval gate.

## Current phase

Phase 12b — Conversation recommendation output (in review).

Phase 11 (the unified feature summary and versioned output schema), the continuous-integration workflow, and Phase 12 (the deterministic policy core in `src/vocal_intel/policy.py`) are merged to `main`.

Phase 12b wires the policy core into a new, opt-in `recommend` command. The command emits a `schema_version` 1.1 document that carries the same feature blocks as the summary plus the policy's recommendation, reason, and evidence. The `summarize` command is unchanged and still emits its `schema_version` 1.0 document.

## Validation performed

- New deterministic tests assert the 1.1 document shape and field order against a committed golden manifest, pin the exact reason and evidence wording for the classified recommendations, confirm the conservative `not_enough_evidence` default end-to-end through the command line, and assert that the feature blocks are byte-equal to the summary output.
- A regression test confirms the `summarize` output stays byte-stable and that its reserved recommendation fields remain empty.
- The existing test suite still passes; there is no change to the summarize output or to the 1.0 output schema.

## Known limitations

- The policy thresholds and the whole-clip pause-to-timing mapping are provisional, pending the real-audio validation run.
- The `uncertainty` and `confidence` fields remain reserved and are not estimated.
- `interrupt_politely` and `challenge` are reserved and not produced.

## Next approval gate

Review and merge of the Phase 12b recommendation-output change.
