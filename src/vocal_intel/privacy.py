"""Staged-file privacy checks.

These helpers keep private audio, transcripts, and local-only working files out
of version control. The logic is intentionally simple and dependency-free so it
can run as a pre-commit hook and as part of the test suite.
"""

from __future__ import annotations

from collections.abc import Iterable

# File extensions that indicate raw or private audio.
AUDIO_EXTENSIONS = (
    ".wav",
    ".mp3",
    ".m4a",
    ".flac",
    ".ogg",
    ".caf",
    ".aiff",
    ".aac",
)

# File extensions that indicate a private transcript or caption export. These
# are transcript-specific formats only; general text extensions such as ``.txt``
# are deliberately not blocked because the repo holds legitimate text files.
TRANSCRIPT_EXTENSIONS = (
    ".vtt",
    ".srt",
    ".ass",
    ".sbv",
    ".ttml",
)

# Path prefixes that must never be committed.
DISALLOWED_PREFIXES = (
    ".local/",
    "recordings/",
    "data/raw/",
    "data/processed/",
    "models/",
)

# Directory names that hold private transcript or meeting material. These match
# as an exact path segment anywhere in the path (e.g. ``docs/transcripts/x.md``),
# so a source file such as ``transcript.py`` is not affected.
DISALLOWED_DIR_NAMES = (
    "transcripts",
    "transcript",
    "meeting-notes",
    "meeting_notes",
)


def _normalise(path: str) -> str:
    """Normalise a path for matching without losing a leading dot directory."""
    cleaned = path.strip()
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned


def is_disallowed(path: str) -> bool:
    """Return True if *path* must not be committed."""
    cleaned = _normalise(path)
    if not cleaned:
        return False
    lower = cleaned.lower()
    if lower.endswith(AUDIO_EXTENSIONS) or lower.endswith(TRANSCRIPT_EXTENSIONS):
        return True
    if lower.endswith(".private.md"):
        return True
    if any(segment in DISALLOWED_DIR_NAMES for segment in lower.split("/")):
        return True
    for prefix in DISALLOWED_PREFIXES:
        if cleaned == prefix.rstrip("/") or cleaned.startswith(prefix):
            return True
    return False


def find_disallowed(paths: Iterable[str]) -> list[str]:
    """Return the subset of *paths* that must not be committed."""
    return [p for p in paths if p and is_disallowed(p)]
