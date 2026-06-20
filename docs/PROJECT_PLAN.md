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
- vocal feature extraction
- pause detection
- speech energy analysis
- pitch and loudness profiles
- transcript-aware interpretation
- conversation timing policy
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

## Development phases

### Phase 0 — Project foundation

Set up the Python package, test framework, CLI entry point, and clean project structure.

Deliverables:
- importable Python package
- basic CLI shell
- pytest smoke test
- clean README update

Validation:
- package imports successfully
- tests pass locally

### Phase 1 — Audio ingestion

Accept a local audio file and return basic metadata.

Deliverables:
- CLI command for inspecting audio
- duration
- sample rate
- channel count
- waveform shape
- file format handling notes

Validation:
- test with synthetic generated WAV
- test with one real short recording

### Phase 2 — Loudness and energy analysis

Extract energy-related speech features.

Deliverables:
- RMS loudness
- peak loudness
- loudness over time
- quiet/loud section detection
- simple loudness labels

Validation:
- synthetic quiet/loud audio tests
- real soft vs loud voice comparison

### Phase 3 — Silence and pause detection

Detect silence regions and possible thinking pauses.

Deliverables:
- silence thresholding
- pause duration list
- short/medium/long pause labels
- pause summary

Validation:
- synthetic audio with known silence intervals
- real recording with deliberate pauses

### Phase 4 — Pitch analysis

Estimate pitch behaviour over time.

Deliverables:
- pitch contour extraction
- pitch stability estimate
- animated vs flat delivery label
- rising/falling pitch trend

Validation:
- synthetic tones where possible
- real expressive vs monotone speech sample

### Phase 5 — Speech pace estimation

Estimate speaking speed using signal-level heuristics.

Deliverables:
- speech segment count
- onset/energy-based pace estimate
- slow/normal/fast label
- limitations documented

Validation:
- real slow and fast reading samples
- compare estimated labels manually

### Phase 6 — Unified feature summary

Combine extracted audio features into a structured summary.

Deliverables:
- JSON output schema
- duration
- loudness profile
- pause profile
- pitch profile
- pace estimate
- confidence/limitations field

Validation:
- CLI produces stable JSON
- tests check required fields

### Phase 7 — Conversation policy engine

Create a rule-based policy for conversation timing.

Possible outputs:
- wait
- respond
- clarify
- interrupt_politely
- challenge

Deliverables:
- policy module
- documented rules
- explainable reason field

Validation:
- unit tests for each policy output
- manual examples with sample feature inputs

### Phase 8 — Transcript integration

Allow optional transcript text alongside audio features.

Deliverables:
- transcript input option
- unfinished phrase detection
- filler word detection
- uncertainty indicators
- combined audio/text reasoning

Validation:
- examples with and without transcript
- tests for unfinished text cases

### Phase 9 — Local recording utility

Add a simple local microphone recording workflow.

Deliverables:
- short audio recording command if feasible
- saves local WAV files outside Git
- clear privacy warning
- no recordings committed

Validation:
- record 5-second sample
- inspect with Phase 1 command

### Phase 10 — Synthetic audio test suite

Generate artificial test audio for reliable automated tests.

Deliverables:
- synthetic audio generation helpers
- quiet/loud samples
- silence gap samples
- simple pitch samples

Validation:
- tests run without external files
- predictable output ranges

### Phase 11 — Real sample validation protocol

Create a repeatable manual validation protocol using local recordings.

Sample set:
- normal voice
- soft voice
- loud voice
- fast speech
- slow speech
- dramatic/expressive speech
- speech with long thinking pauses

Deliverables:
- documented protocol
- expected observations
- manual result template

Validation:
- complete at least one local validation run

### Phase 12 — Dataset format

Define a small labelled example format.

Deliverables:
- JSONL schema
- fields for audio path, transcript, extracted features, human label, desired behaviour
- example entries with placeholder paths

Validation:
- schema validation tests
- example file passes validation

### Phase 13 — Baseline classifier

Train a small classical ML model on extracted feature rows.

Deliverables:
- scikit-learn baseline
- train/evaluate script
- model card notes
- clear warning about tiny dataset limitations

Validation:
- toy dataset training test
- evaluation metrics printed

### Phase 14 — Evaluation reporting

Add basic evaluation tools.

Deliverables:
- accuracy
- confusion matrix
- wrong example inspection
- small report output

Validation:
- evaluation script works on toy dataset

### Phase 15 — Chunked audio simulation

Process audio in chunks to simulate live conversation.

Deliverables:
- chunk processor
- partial feature updates
- evolving policy recommendation
- simulation CLI

Validation:
- run on a recorded sample
- observe policy changes over time

### Phase 16 — Live microphone prototype

Attempt live local microphone analysis.

Deliverables:
- live mode if feasible
- chunk-based audio capture
- rolling feature summary
- console output

Validation:
- manual live demo
- fallback documented if microphone library issues occur

### Phase 17 — Conversation event timeline

Represent audio as a timeline of events.

Events may include:
- speech_started
- speech_ended
- loudness_increase
- long_pause_detected
- possible_thinking_pause
- possible_interruption_point

Deliverables:
- event model
- event timeline JSON
- CLI output option

Validation:
- tests from synthetic audio
- manual real recording check

### Phase 18 — External model interface

Produce a clean JSON object that another system could consume.

Deliverables:
- stable output schema
- recommendation field
- evidence field
- uncertainty field
- no dependency on a specific external provider

Validation:
- schema tests
- example output in docs

### Phase 19 — Documentation polish

Make the project understandable to a public technical audience.

Deliverables:
- improved README
- architecture notes
- validation notes
- example commands
- limitations section

Validation:
- fresh clone setup instructions reviewed

### Phase 20 — Public demo milestone

Create a simple end-to-end demo.

Deliverables:
- inspect an audio file
- extract features
- produce feature summary
- produce conversation recommendation
- show example JSON

Validation:
- run demo command locally
- include expected output example

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
