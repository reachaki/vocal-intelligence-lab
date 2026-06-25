"""Neutral metadata for a user-supplied local text transcript.

This module reads one local plain-text file and assembles a small, neutral
metadata document made of structural counts only: how many characters, words,
and lines the file contains. It performs no content analysis and makes no
inference of any kind, and it never includes the transcript text itself in the
output.

The document is a distinct, separately versioned document
(``document_type`` ``"transcript_metadata"``, ``schema_version`` ``"1.0"``). It
is not part of the audio feature-summary schema family and it does not influence
the conversation recommendation. This module is deliberately self-contained: it
imports none of the audio, summary, recommendation, or policy code, so transcript
metadata can never affect those documents.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DOCUMENT_TYPE = "transcript_metadata"
SCHEMA_VERSION = "1.0"

# Plain-text inputs only. Structured caption/subtitle formats (for example
# ``.vtt``/``.srt``/``.ass``) are intentionally out of scope for this document.
ALLOWED_EXTENSIONS = (".txt", ".md")

# Hard cap on input size in bytes, checked before decoding, so an arbitrary or
# pathological file cannot exhaust memory. Real plain-text transcripts are far
# smaller than this.
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MiB

LIMITATIONS_TEXT = (
    "Neutral structural counts of a user-supplied local text file. No content "
    "analysis and no inference are performed, and the transcript text is not "
    "included in this output."
)


class TranscriptMetaError(ValueError):
    """Raised when a transcript metadata document cannot be assembled."""


@dataclass(frozen=True, eq=False)
class TranscriptMetadata:
    """One text file's neutral structural counts in the v1 document form."""

    source_path: str | None
    source_format: str | None
    character_count: int
    word_count: int
    line_count: int

    def to_dict(self) -> dict:
        """Return the document as a nested ordered dict.

        Key insertion order here IS the document field order. An intended change
        requires bumping ``SCHEMA_VERSION`` and regenerating the golden manifest
        in the same change.
        """
        return {
            "document_type": DOCUMENT_TYPE,
            "schema_version": SCHEMA_VERSION,
            "source": {
                "path": self.source_path,
                "format": self.source_format,
            },
            "character_count": int(self.character_count),
            "word_count": int(self.word_count),
            "line_count": int(self.line_count),
            "limitations": LIMITATIONS_TEXT,
        }

    def to_json(self) -> str:
        """Serialize :meth:`to_dict` with the pinned deterministic settings.

        Identical settings to the ``summarize`` and ``recommend`` serializers, so
        every document in the repository formats with the same rules.
        """
        return json.dumps(
            self.to_dict(),
            indent=2,
            ensure_ascii=True,
            sort_keys=False,
            separators=(",", ": "),
        )


def _counts(text: str) -> tuple[int, int, int]:
    """Return ``(character_count, word_count, line_count)`` for *text*.

    Counts are taken over the raw decoded string with no normalisation:

    - ``character_count`` is the number of Unicode code points (``len``).
    - ``word_count`` is the number of whitespace-separated tokens
      (``str.split()``); this is a structural token count, not a linguistic one.
    - ``line_count`` is the number of lines (``str.splitlines()``).
    """
    return (len(text), len(text.split()), len(text.splitlines()))


def metadata_from_text(
    text: str, *, path: str | None = None, fmt: str | None = None
) -> TranscriptMetadata:
    """Assemble metadata from already-decoded *text*. Pure and free of I/O."""
    character_count, word_count, line_count = _counts(text)
    return TranscriptMetadata(
        source_path=path,
        source_format=fmt,
        character_count=character_count,
        word_count=word_count,
        line_count=line_count,
    )


def _normalise_format(suffix: str) -> str | None:
    """Return the lower-cased extension without its leading dot, or ``None``."""
    cleaned = suffix.lower().lstrip(".")
    return cleaned or None


def metadata_from_file(path) -> TranscriptMetadata:
    """Load a local plain-text file and assemble its :class:`TranscriptMetadata`.

    Raises :class:`TranscriptMetaError` for a missing path, a non-file path, an
    unsupported extension, an oversize file, or content that is not valid UTF-8
    text. ``source.path`` is the input path as a string.
    """
    p = Path(path)
    if not p.exists():
        raise TranscriptMetaError(f"transcript file not found: {path}")
    if not p.is_file():
        raise TranscriptMetaError(f"transcript path is not a file: {path}")

    suffix = p.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(ALLOWED_EXTENSIONS)
        shown = suffix or "(none)"
        raise TranscriptMetaError(
            f"unsupported transcript format {shown}: expected one of {allowed}"
        )

    size = p.stat().st_size
    if size > MAX_FILE_BYTES:
        raise TranscriptMetaError(
            f"transcript file too large: {size} bytes (max {MAX_FILE_BYTES})"
        )

    raw = p.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TranscriptMetaError(
            f"transcript file is not valid UTF-8 text: {path}"
        ) from exc

    return metadata_from_text(text, path=str(path), fmt=_normalise_format(suffix))


__all__ = [
    "ALLOWED_EXTENSIONS",
    "DOCUMENT_TYPE",
    "LIMITATIONS_TEXT",
    "MAX_FILE_BYTES",
    "SCHEMA_VERSION",
    "TranscriptMetadata",
    "TranscriptMetaError",
    "metadata_from_file",
    "metadata_from_text",
]
