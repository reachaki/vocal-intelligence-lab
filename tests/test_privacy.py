"""Unit tests for the staged-file privacy checks."""

from __future__ import annotations

from vocal_intel.privacy import find_disallowed, is_disallowed


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


def test_find_disallowed_filters_the_list():
    paths = ["src/vocal_intel/cli.py", "secret.wav", ".local/x.md"]
    assert find_disallowed(paths) == ["secret.wav", ".local/x.md"]
