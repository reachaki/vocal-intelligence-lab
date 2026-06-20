"""Staged-file privacy checks.

These helpers keep private audio and local-only working files out of version
control. The logic is intentionally simple and dependency-free so it can run as
a pre-commit hook and as part of the test suite.
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

# Path prefixes that must never be committed.
DISALLOWED_PREFIXES = (
    ".local/",
    "recordings/",
    "data/raw/",
    "data/processed/",
    "models/",
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
    if lower.endswith(AUDIO_EXTENSIONS):
        return True
    if lower.endswith(".private.md"):
        return True
    for prefix in DISALLOWED_PREFIXES:
        if cleaned == prefix.rstrip("/") or cleaned.startswith(prefix):
            return True
    return False


def find_disallowed(paths: Iterable[str]) -> list[str]:
    """Return the subset of *paths* that must not be committed."""
    return [p for p in paths if p and is_disallowed(p)]
