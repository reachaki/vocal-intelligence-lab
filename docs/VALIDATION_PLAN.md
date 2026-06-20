# Validation Plan

## Principle

This project must be verified with both automated tests and real behaviour checks.

Unit tests can prove that functions run correctly, but they cannot prove that vocal interpretation is useful. Real audio validation is required for meaningful progress.

## Validation layers

### 1. Static checks

Used to catch simple project problems.

Examples:
- package imports
- CLI command exists
- the output JSON validates against the versioned schema
- the versioned schema has not drifted unexpectedly
- no audio files are staged
- no local-only files are staged

### 2. Unit tests

Used to test deterministic logic.

Examples:
- audio metadata extraction
- pause duration calculation
- label thresholds
- policy decisions from fixed feature input

### 3. Synthetic audio tests

Used when real audio would make tests unstable. Because the inputs are generated, their properties are known exactly, so each test compares output against the known value within a documented numeric tolerance.

Examples:
- generated silence
- generated tone
- generated quiet/loud sections
- generated pause gaps

### 4. Real audio checks

Used to test whether the tool works on actual speech.

Required local samples:
- normal speech
- soft speech
- loud speech
- fast speech
- slow speech
- expressive speech
- speech with deliberate thinking pauses
- a clean and a noisy version of the same utterance

Each sample carries a pre-registered expected label set, recorded at capture time before the tool is run. Where practical an objective anchor is recorded too, for example measured words per minute for pace or a target level offset for loudness. A result passes when the output matches the pre-registered label exactly or within one ordinal step.

These files must stay local and must not be committed.

### 5. Manual interpretation review

For each real sample, compare the output against the pre-registered expectation using discrete fields so reviews are aggregatable across runs. Where possible the same sample is graded on two separate sittings to check repeatability, and a second reviewer is used when available.

Example review:

- File: local only
- Scenario: slow speech with long thinking pauses
- Expected recommendation: wait
- Actual recommendation: wait
- Match: yes
- Notes: pause detected correctly, pace slightly underestimated

## Minimum validation per phase

Each phase must include at least one meaningful validation method, with an objective pass criterion where the inputs allow one.

Examples:

- Phase 1: inspect a synthetic WAV and one real WAV, and reject a malformed file
- Phase 3: produce equivalent output across sample rates and input gains
- Phase 5: compare soft vs loud recordings within a numeric tolerance
- Phase 6: check segment boundaries on synthetic speech-in-silence
- Phase 7: detect known silence gaps within a boundary tolerance
- Phase 8: compare monotone vs expressive speech and check a rising vs falling case
- Phase 9: compare the estimate against measured words per minute
- Phase 11: validate output against the versioned schema
- Phase 12: test every policy output
- Phase 16: complete at least one full local run against pre-registered labels
- Phase 20: simulate a chunked audio timeline

## Privacy validation rules

Raw personal recordings and local-only working files must not be committed. These rules are enforced by checks, not by habit.

Allowed in version control:
- synthetic audio generated in tests
- tiny generated test fixtures if needed
- text examples with placeholder content
- JSON schema examples

Not allowed in version control:
- private voice recordings
- phone recordings
- personal conversation audio
- transcripts of private conversations
- any local-only working files

Enforcement:
- repository ignore rules cover audio file types, the local recordings directory, generated data directories, and local-only working files
- a staged-file check rejects audio files and local-only files before commit
- committed transcript examples must use synthetic placeholder text
- local recordings are written to an ignored directory and excluded from cloud and system backups
- a documented command removes all local recordings

## Definition of done

A phase is not complete unless:

1. The code runs.
2. Relevant tests pass against their documented acceptance criteria.
3. Any phase that produces real-speech behaviour includes a real or pre-labelled validation result.
4. Limitations are documented, naming any capability that was not validated in this phase.
5. The output validates against the current versioned schema.
6. Version control is clean after commit, with no audio or local-only files staged.
