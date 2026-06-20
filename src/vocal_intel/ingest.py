"""Audio ingestion: inspect local audio files and report basic metadata.

Phase 1 reads metadata only. WAV is the supported and validated format; other
formats may work where the underlying audio library supports them, but they are
not yet verified. No feature extraction (loudness, pause, pitch, voice activity,
or pace) is performed at this stage.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

import soundfile as sf


class AudioIngestionError(Exception):
    """Base class for audio ingestion problems."""


class AudioFileNotFoundError(AudioIngestionError):
    """Raised when the requested audio file does not exist or is not a file."""


class UnreadableAudioError(AudioIngestionError):
    """Raised when a file exists but cannot be read as audio."""


@dataclass(frozen=True)
class AudioMetadata:
    """Basic, read-only metadata for a local audio file."""

    path: str
    duration_seconds: float
    sample_rate: int
    channels: int
    frames: int
    format: str | None
    subtype: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def inspect_audio(path: str | os.PathLike) -> AudioMetadata:
    """Return metadata for a local audio file.

    Raises:
        AudioFileNotFoundError: if the path is missing or is not a regular file.
        UnreadableAudioError: if the file exists but cannot be parsed as audio
            (for example an empty, corrupt, or unsupported file).
    """
    p = Path(path)
    if not p.exists():
        raise AudioFileNotFoundError(f"Audio file not found: {p}")
    if not p.is_file():
        raise AudioFileNotFoundError(f"Not a file: {p}")

    try:
        info = sf.info(str(p))
    except Exception as exc:  # libsndfile raises a range of errors
        raise UnreadableAudioError(f"Could not read audio file: {p} ({exc})") from exc

    sample_rate = int(info.samplerate)
    frames = int(info.frames)
    duration = frames / sample_rate if sample_rate else 0.0

    return AudioMetadata(
        path=str(p),
        duration_seconds=round(float(duration), 6),
        sample_rate=sample_rate,
        channels=int(info.channels),
        frames=frames,
        format=getattr(info, "format", None),
        subtype=getattr(info, "subtype", None),
    )
