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
- JSON schema contains required fields
- no private files are staged

### 2. Unit tests

Used to test deterministic logic.

Examples:
- audio metadata extraction
- pause duration calculation
- label thresholds
- policy decisions from fixed feature input

### 3. Synthetic audio tests

Used when real audio would make tests unstable.

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

These files must stay local and must not be committed.

### 5. Manual interpretation review

For each real sample, compare the output against human expectation.

Example review:

- File: local only
- Scenario: slow speech with long thinking pauses
- Expected: wait or do_not_interrupt
- Actual: wait
- Pass/fail: pass
- Notes: pause detected correctly, pace slightly underestimated

## Minimum validation per phase

Each phase must include at least one meaningful validation method.

Examples:

- Phase 1: inspect synthetic WAV and one real WAV
- Phase 2: compare soft vs loud recordings
- Phase 3: detect known silence gaps
- Phase 4: compare monotone vs expressive speech
- Phase 7: test every policy output
- Phase 15: simulate chunked audio timeline

## Privacy rule

Raw personal recordings must not be committed.

Allowed:
- synthetic audio generated in tests
- tiny generated test fixtures if needed
- text examples
- JSON schema examples

Not allowed:
- private voice recordings
- phone recordings
- personal conversation audio
- transcripts of private conversations

## Definition of done

A phase is not complete unless:

1. The code runs.
2. Relevant tests pass.
3. A demo or manual check has been performed where appropriate.
4. Limitations are documented.
5. Git status is clean after commit.
