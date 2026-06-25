# Progress

This document tracks the current state of the project: the active phase, the validation performed, known limitations, and the next approval gate.

## Current phase

Phase 12 — Conversation policy engine (policy core; in review).

Phase 11 (the unified feature summary and versioned output schema) and the continuous-integration workflow are merged to `main`.

Phase 12 adds `src/vocal_intel/policy.py`, a deterministic rule-based conversation-timing policy, with provisional thresholds in the versioned configuration and a reference document in `docs/CONVERSATION_POLICY.md`.

## Validation performed

- Deterministic unit tests assert each policy output (`wait`, `respond`, `clarify`, and the conservative `not_enough_evidence` default) for hand-authored feature inputs, including the gate edge cases and the band-boundary operators.
- New unit tests cover validation of the conversation-policy thresholds in the versioned configuration.
- The existing test suite still passes; there is no change to the summarize output or the output schema.

## Known limitations

- The policy thresholds and the whole-file pause-to-timing mapping are provisional, pending the real-audio validation run.
- The policy core is not yet wired into the command-line output; that is a later step.
- `interrupt_politely` and `challenge` are reserved and not implemented.

## Next approval gate

Review and merge of the Phase 12 policy-core change.
