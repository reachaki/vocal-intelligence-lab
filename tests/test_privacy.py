"""Unit tests for the staged-file privacy checks."""

from __future__ import annotations

from vocal_intel.privacy import (
    AUDIO_EXTENSIONS,
    DISALLOWED_DIR_NAMES,
    DISALLOWED_PREFIXES,
    TRANSCRIPT_EXTENSIONS,
    find_disallowed,
    is_disallowed,
)


def test_audio_files_are_rejected():
    for path in [
        "a.wav",
        "sub/dir/b.MP3",
        "c.m4a",
        "d.flac",
        "e.ogg",
        "f.caf",
        "g.aiff",
        "h.aac",
    ]:
        assert is_disallowed(path), path


def test_local_only_files_are_rejected():
    assert is_disallowed(".local/WORK_INSTRUCTIONS.md")
    assert is_disallowed("notes.private.md")
    assert is_disallowed("recordings/today.wav")
    assert is_disallowed("data/raw/sample.bin")
    assert is_disallowed("data/processed/features.npy")
    assert is_disallowed("models/baseline.pkl")


def test_transcript_files_are_rejected():
    for path in [
        "call.vtt",
        "sub/dir/meeting.SRT",
        "captions.ass",
    ]:
        assert is_disallowed(path), path


def test_transcript_and_meeting_directories_are_rejected():
    for path in [
        "transcripts/2026-06-25.txt",
        "transcript/raw.md",
        "meeting-notes/standup.md",
        "docs/transcripts/call.md",
        "notes/meeting-notes/sync.md",
    ]:
        assert is_disallowed(path), path


def test_additional_caption_transcript_formats_are_rejected():
    for path in [
        "call.sbv",
        "subs/episode.TTML",
        "exports/meeting.ttml",
    ]:
        assert is_disallowed(path), path


def test_meeting_notes_underscore_directory_is_rejected():
    for path in [
        "meeting_notes/standup.md",
        "notes/meeting_notes/sync.md",
    ]:
        assert is_disallowed(path), path


def test_normal_source_files_are_allowed():
    for path in [
        "src/vocal_intel/__init__.py",
        "README.md",
        "tests/test_smoke.py",
        "docs/PROJECT_PLAN.md",
        "pyproject.toml",
        "scripts/check_staged_files.py",
    ]:
        assert not is_disallowed(path), path


def test_legitimate_text_and_named_files_are_not_overblocked():
    # The guard must stay narrow: general text files and source modules whose
    # names merely contain "transcript" must not be blocked.
    for path in [
        "requirements.txt",
        "docs/notes.txt",
        "docs/transcription_overview.md",
        "src/vocal_intel/transcript.py",
        "tests/test_transcript_helpers.py",
        # Exact-segment dir matching only: a file merely named like a blocked
        # directory (not a directory) stays allowed, and ".sub"/".md" are not
        # caption formats.
        "docs/meeting_notes.md",
        "docs/meeting_notes_overview.md",
        "subtitles.sub",
    ]:
        assert not is_disallowed(path), path


def test_find_disallowed_filters_the_list():
    paths = ["src/vocal_intel/cli.py", "secret.wav", ".local/x.md"]
    assert find_disallowed(paths) == ["secret.wav", ".local/x.md"]


# --- self-coverage: every declared rule is actually enforced ---------------
#
# These meta-tests iterate the guard's own declared tuples, so any future entry
# is automatically covered: adding an extension or directory name that is not
# actually enforced (or removing the enforcement while leaving the declaration)
# will fail here. The non-empty guards keep the loops from passing vacuously.


def test_declared_tuples_are_non_empty():
    assert AUDIO_EXTENSIONS
    assert TRANSCRIPT_EXTENSIONS
    assert DISALLOWED_PREFIXES
    assert DISALLOWED_DIR_NAMES


def test_every_declared_audio_extension_is_enforced():
    for ext in AUDIO_EXTENSIONS:
        assert is_disallowed("clip" + ext), ext
        assert is_disallowed("a/b/clip" + ext.upper()), ext  # case-insensitive


def test_every_declared_transcript_extension_is_enforced():
    for ext in TRANSCRIPT_EXTENSIONS:
        assert is_disallowed("export" + ext), ext
        assert is_disallowed("a/b/export" + ext.upper()), ext  # case-insensitive


def test_every_declared_disallowed_dir_name_is_enforced():
    for name in DISALLOWED_DIR_NAMES:
        assert is_disallowed(name + "/file.md"), name
        assert is_disallowed("nested/" + name + "/file.md"), name


def test_every_declared_disallowed_prefix_is_enforced():
    for prefix in DISALLOWED_PREFIXES:
        assert is_disallowed(prefix + "x"), prefix
        assert is_disallowed(prefix.rstrip("/")), prefix  # the bare directory name
