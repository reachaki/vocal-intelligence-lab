# Real-Audio Validation Protocol

This protocol defines how the project is validated against real speech. Automated tests on synthetic signals confirm that functions run correctly, but they cannot show that vocal interpretation is useful on real voices. This document describes a small, repeatable manual procedure for recording, labelling, and checking real-audio samples.

Recordings are local-only and are never committed (see [Storage, privacy, and retention](#storage-privacy-and-retention)).

## Sample set

Record the following categories. Each is a short clip (roughly five to fifteen seconds) of a single speaker reading or speaking naturally.

| Category | Description |
| --- | --- |
| `normal` | Ordinary speaking voice and pace. |
| `soft` | Deliberately quiet delivery. |
| `loud` | Deliberately loud delivery. |
| `fast` | Faster-than-usual delivery. |
| `slow` | Slower-than-usual delivery. |
| `expressive` | Animated delivery with clear pitch variation. |
| `thinking_pauses` | Natural speech containing deliberate thinking pauses. |

Where feasible, also record a clean-versus-noisy pair: the same utterance once in a quiet room and once with background noise. The noise condition is recorded as `clean` or `noisy`.

## Pre-registered labels (recorded at capture time)

Before producing any analysis output, write down what each clip is intended to represent. Pre-registering the expectation keeps validation honest: the expected label is fixed before any tool produces a result.

For each clip, record:

- `sample_id` — a stable identifier, for example `2026-06-20-normal-clean`.
- `category` — one of the sample categories above.
- `noise_condition` — `clean` or `noisy`.
- `intended_loudness` — `soft`, `normal`, or `loud`.
- `intended_pace` — `slow`, `normal`, or `fast`.
- `expressivity` (optional) — `flat`, `normal`, or `expressive`.
- `expected_pause_count` — the number of deliberate pauses intended.
- `expected_recommendation` (optional) — the conversation recommendation a correct system should produce.

## Objective anchors

Where practical, capture a measurable reference so a label is graded against a number, not only an impression:

- **Duration** — the measured length of the clip in seconds.
- **Pace** — read a script with a known word count, then compute words per minute from the word count and the measured duration. A helper is provided as `vocal_intel.protocol.words_per_minute`.
- **Loudness** — record the capture conditions (microphone, distance, and input gain) and the intended scenario (soft / normal / loud) so the absolute level is interpretable.
- **Pauses** — note the intended number and approximate positions of pauses.

## Result template

Use the template in [`docs/templates/real-audio-result-template.md`](templates/real-audio-result-template.md) for each clip. It uses discrete fields so results can be compared across runs. A result is a **pass** when the produced label matches the pre-registered label exactly, or within one ordinal step on an ordered scale (for example `soft` / `normal` / `loud`).

The discrete record format is also checked by `vocal_intel.protocol.validate_result_record`, which confirms the required fields are present and the labels are drawn from the allowed sets.

## Storage, privacy, and retention

- Store recordings and their label and result files under `recordings/` in the project root. This directory is ignored by version control; confirm with `git check-ignore recordings/`.
- Never commit recordings, label files, or result files. Audio file types and the `recordings/` directory are covered by the repository ignore rules and by the staged-file check (`scripts/check_staged_files.py`).
- Keep recordings on the local machine only. Exclude the `recordings/` directory from cloud sync and system backups.
- Retain recordings only as long as needed for validation, then delete them (for example by clearing the contents of `recordings/`).
- Do not record other people without their clear consent. Prefer single-speaker self-recordings.

## Running a validation pass

1. Record the sample set into `recordings/`.
2. Pre-register the labels for each clip before producing any output.
3. Produce the tool output for each clip (the feature and recommendation outputs are added in later phases).
4. Fill in the result template, comparing the produced labels against the pre-registered labels.
5. Record a verdict per clip and summarise the pass and fail counts.

A validation pass is complete when at least one clip has been recorded, labelled, and checked against the template.
