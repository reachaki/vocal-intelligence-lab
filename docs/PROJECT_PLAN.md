# Project Plan

## Project name

Vocal Intelligence Lab

## Purpose

Vocal Intelligence Lab is a local-first research and engineering prototype for analysing speech beyond transcript text.

Most voice systems reduce speech to words. This project explores the extra information inside spoken communication: loudness, pitch, pace, rhythm, pauses, hesitation, intensity, and turn-taking signals.

The long-term aim is to produce structured vocal context that can help conversational systems decide whether to wait, respond, clarify, interrupt politely, or challenge the speaker.

## Core question

Can a local tool extract enough useful information from audio to improve conversation timing and interpretation beyond plain transcript text?

## Scope

This project is not trying to build a full speech-to-text model or a full conversational AI model.

It focuses on:

- audio ingestion
- audio metadata
- audio preprocessing and canonicalisation
- vocal feature extraction
- voice activity detection
- pause detection
- speech energy analysis
- pitch and loudness profiles
- threshold calibration and configuration
- transcript-aware interpretation
- conversation timing policy
- a versioned output schema
- local demos
- testable outputs

## Non-goals

- Training a massive foundation model
- Building a production voice assistant
- Replacing speech-to-text systems
- Building a paid API service
- Requiring cloud GPU infrastructure
- Storing private user recordings in the repository

## Hardware target

The early prototype must run on:

- Apple Silicon M1 MacBook Air
- local Python environment
- no dedicated NVIDIA GPU
- no paid cloud dependency

## Roadmap principles

- Build in small phases, each committed separately.
- Every phase ships at least one meaningful validation method.
- Deterministic fixtures and shared building blocks come before the features that depend on them.
- Qualitative labels are derived from a single versioned configuration, not scattered constants.
- All JSON output conforms to one versioned schema.
- Private recordings and local-only files stay out of version control.

## Development phases

### Phase 0 — Project foundation

Set up the Python package, test framework, CLI entry point, and a clean project structure.

Deliverables:
- importable Python package
- basic CLI shell
- pytest smoke test
- documented Python version and a pinned dependency lock
- repository ignore rules and a staged-file privacy check
- clean README update

Validation:
- package imports successfully
- the audio stack imports and loads a generated sample
- tests pass locally
- the privacy check rejects audio files and local-only files from staging

### Phase 1 — Audio ingestion

Accept a local audio file and return basic metadata.

Deliverables:
- CLI command for inspecting audio
- duration
- sample rate
- channel count
- waveform shape
- file format handling notes
- clear errors for unsupported or malformed files

Validation:
- test with a synthetic generated WAV
- test with one real short recording
- test rejection of an empty or unreadable file

### Phase 2 — Synthetic audio fixtures

Provide deterministic audio generators so feature phases can be tested without external files.

Deliverables:
- synthetic audio generation helpers
- silence and tone fixtures
- quiet and loud fixtures
- pause-gap fixtures
- simple pitch fixtures
- fixtures usable directly by later feature tests

Validation:
- fixtures generate without external files
- generated fixtures have known, documented properties (duration, level, gap positions)

### Phase 3 — Audio preprocessing and canonicalisation

Convert arbitrary input audio into a consistent internal form before feature extraction.

Deliverables:
- mono downmix
- resampling to a fixed target sample rate (for example 16 kHz)
- DC-offset removal
- optional peak normalisation that preserves meaningful loudness features
- a duration guard with a documented supported-length ceiling
- a documented note on what is and is not normalised

Validation:
- equivalent feature-relevant output for the same utterance loaded at two sample rates
- equivalent output for the same utterance at two input gains where loudness is normalised
- the duration guard warns above the configured ceiling

### Phase 4 — Real-audio validation protocol

Define the repeatable real-audio protocol before the feature phases that depend on it.

Deliverables:
- a documented sample set: normal, soft, loud, fast, slow, expressive, and thinking-pause speech, plus a clean-versus-noisy pair
- pre-registered expected labels recorded at capture time
- objective anchors where practical (for example measured words per minute, or a target level offset)
- a manual result template with discrete fields
- instructions for producing and storing local-only samples

Validation:
- the protocol document is reviewed
- at least one sample is captured and labelled using the template

### Phase 5 — Loudness and energy analysis

Extract energy-related speech features.

Deliverables:
- RMS loudness
- peak loudness
- loudness over time
- quiet/loud section detection
- simple loudness labels

Validation:
- synthetic quiet/loud fixture tests with a documented numeric tolerance
- real soft vs loud comparison against the pre-registered labels

### Phase 6 — Voice activity detection and noise-floor estimation

Provide a single shared speech/non-speech segmentation and an adaptive noise floor, reused by pause detection, pace estimation, and the event timeline.

Deliverables:
- a noise-floor estimate (for example ambient or percentile based)
- a relative, noise-aware speech threshold
- speech/non-speech segmentation with minimum-duration smoothing
- a segment list consumed by later phases

Validation:
- synthetic speech-in-silence with known onset and offset times, within a documented tolerance
- stable segmentation across a clean and an added-noise version of the same clip

### Phase 7 — Silence and pause detection

Detect silence regions and possible thinking pauses from the shared segmentation.

Deliverables:
- pause regions derived from the speech segmentation
- pause duration list
- short/medium/long pause labels
- pause summary

Validation:
- synthetic audio with known silence intervals, boundaries within a documented tolerance
- real connected speech with marked pauses, reporting missed and spurious pauses

### Phase 8 — Pitch analysis

Estimate pitch behaviour over time with explicit handling of unvoiced frames.

Deliverables:
- pitch contour extraction with explicit voiced/unvoiced handling
- a documented fundamental-frequency search range
- pitch stability estimate over voiced frames only
- animated vs flat delivery label
- rising/falling pitch trend

Validation:
- synthetic tones of known fundamental within a documented tolerance
- a real expressive vs monotone sample, including a rising vs falling check (question vs statement)

### Phase 9 — Speech pace estimation

Estimate speaking speed using signal-level heuristics over the speech-active regions.

Deliverables:
- speech-active duration from the segmentation
- a syllable-rate estimate normalised by speech-active time
- slow/normal/fast label
- documented method and limitations

Validation:
- real samples read from a known script, compared against measured words per minute
- the estimate correlates with the measured rate, not only ordered correctly

### Phase 10 — Threshold calibration and versioned configuration

Centralise the numeric cut-points behind every qualitative label.

Deliverables:
- a single versioned configuration file for all label thresholds
- data-driven cut-points derived from the real-sample set
- a configuration version stamped into outputs
- a documented calibration procedure

Validation:
- labelled samples map to their intended labels using the configuration
- a threshold change requires only a configuration edit

### Phase 11 — Unified feature summary and versioned output schema

Combine extracted audio features into a structured summary defined by a single versioned schema.

Deliverables:
- a single versioned JSON output schema with a schema_version field
- duration
- loudness profile
- pause profile
- pitch profile
- pace estimate
- a confidence and limitations field
- reserved recommendation, evidence, and uncertainty fields

Validation:
- the CLI produces stable JSON that validates against the schema
- a schema and version regression test fails on unintended field changes

### Phase 12 — Conversation policy engine

Create a rule-based policy for conversation timing.

Outputs implemented in this phase:
- wait
- respond
- clarify
- not_enough_evidence (conservative default when signals are weak or ambiguous)

Reserved for a future, separately scoped iteration (not implemented):
- interrupt_politely
- challenge

Deliverables:
- policy module
- documented rules
- explainable reason field
- thresholds sourced from the versioned configuration and marked provisional until the real-validation run
- outputs are strictly signal-level, carry an explainable reason, and make no inference about the speaker

Validation:
- unit tests for each policy output
- manual examples with sample feature inputs

### Phase 13 — Transcript integration

Allow optional transcript text alongside audio features.

Deliverables:
- optional transcript input supplied by file path or standard input
- unfinished phrase detection
- filler word detection
- uncertainty indicators
- combined audio/text reasoning
- a requirement that committed examples use synthetic placeholder text

Validation:
- examples with and without transcript
- tests for unfinished text cases

### Phase 14 — Local recording utility

Add a simple local microphone recording workflow.

Deliverables:
- a short audio recording command if feasible
- recordings written only to an ignored local directory
- a clear privacy notice
- a documented command to delete local recordings
- no recordings committed

Validation:
- record a short sample
- inspect it with the ingestion command
- confirm recordings are ignored by version control

### Phase 15 — Synthetic test-suite expansion

Extend the deterministic fixtures into a broad automated test suite.

Deliverables:
- expanded edge-case fixtures
- parametrised ranges
- coverage for preprocessing, segmentation, and feature thresholds

Validation:
- tests run without external files
- documented expected output ranges with numeric tolerances

### Phase 16 — Real-sample validation run

Execute the Phase 4 protocol across all features.

Deliverables:
- a full run of the protocol against every feature
- completed result templates
- a saved local results summary for run-to-run comparison

Validation:
- complete at least one full local validation run
- record pass/fail against the pre-registered labels

### Phase 17 — Dataset format

Define a small labelled example format.

Deliverables:
- a JSONL schema that references the versioned output schema
- fields for audio path, transcript, extracted features, human label, desired behaviour
- example entries with placeholder paths and placeholder transcript text

Validation:
- schema validation tests
- the example file passes validation

### Phase 18 — Baseline classifier

Train a small classical ML model on extracted feature rows.

Deliverables:
- a scikit-learn baseline
- a train/evaluate script with a held-out split
- a majority-class baseline comparison
- model card notes
- a clear warning about small-dataset limitations

Validation:
- a toy dataset training test using a train/test split
- evaluation metrics printed with per-class support and the baseline comparison

### Phase 19 — Evaluation reporting

Add basic evaluation tools.

Deliverables:
- accuracy
- confusion matrix
- wrong example inspection
- a small report output

Validation:
- the evaluation script works on the toy dataset

### Phase 20 — Chunked audio simulation

Process audio in chunks to simulate live conversation.

Deliverables:
- a chunk processor
- partial feature updates
- an evolving policy recommendation
- a file-based replay path through the chunk pipeline
- a simulation CLI

Validation:
- run on a recorded sample
- observe policy changes over time
- chunked output reasonably matches whole-file processing of the same file

### Phase 21 — Live microphone prototype

Attempt live local microphone analysis.

Deliverables:
- a live mode if feasible, reusing the chunk processor
- chunk-based audio capture
- a rolling feature summary
- a documented latency target
- console output

Validation:
- a manual live demo
- measured per-chunk processing time below the chosen update interval
- a documented fallback to file replay if microphone capture is unavailable

### Phase 22 — Conversation event timeline

Represent audio as a timeline of events.

Events may include:
- speech_started
- speech_ended
- loudness_increase
- long_pause_detected
- possible_thinking_pause
- possible_interruption_point

Deliverables:
- an event model
- an event timeline JSON that uses the versioned schema
- a CLI output option

Validation:
- tests from synthetic audio
- comparison against a human-marked timeline on a real recording, reporting matched, missed, and spurious events

### Phase 23 — External interface and schema freeze

Produce a clean, stable JSON object that another system could consume.

Deliverables:
- a frozen, versioned output schema for external consumers
- recommendation field
- evidence field
- uncertainty field
- no dependency on a specific external provider

Validation:
- schema tests
- an example output in the docs

### Phase 24 — Documentation polish

Make the project understandable to a public technical audience.

Deliverables:
- an improved README
- architecture notes
- validation notes
- example commands
- a limitations section

Validation:
- fresh clone setup instructions reviewed in a clean environment

### Phase 25 — Public demo milestone

Create a simple end-to-end demo.

Deliverables:
- inspect an audio file
- extract features
- produce a feature summary
- produce a conversation recommendation
- show example JSON

Validation:
- run the demo command locally
- include an expected output example

## Long-term extensions

Possible future directions:

- better speech-to-text integration
- emotion recognition research
- turn-taking prediction
- speaker diarisation
- mobile recording app
- web dashboard
- Core ML optimisation
- larger labelled dataset
- cloud GPU experiments
- multimodal conversation assistant research
