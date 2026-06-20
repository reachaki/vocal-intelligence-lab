"""Tests for audio ingestion (Phase 1).

Fixtures are tiny WAV files generated with the standard library into pytest's
temporary directory, so the suite needs no committed audio.
"""

from __future__ import annotations

import json
import math
import wave
from pathlib import Path

import pytest

from vocal_intel import cli
from vocal_intel.ingest import (
    AudioFileNotFoundError,
    UnreadableAudioError,
    inspect_audio,
)

SAMPLE_RATE = 16000
CHANNELS = 1
DURATION_S = 0.25


def _write_wav(path: Path, *, sample_rate=SAMPLE_RATE, channels=CHANNELS, duration_s=DURATION_S) -> int:
    """Write a tiny silent 16-bit PCM WAV and return its frame count."""
    n_frames = int(round(sample_rate * duration_s))
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(2)  # 16-bit PCM
        writer.setframerate(sample_rate)
        writer.writeframes(b"\x00\x00" * n_frames * channels)
    return n_frames


def test_inspect_returns_expected_metadata(tmp_path):
    wav = tmp_path / "clip.wav"
    n_frames = _write_wav(wav)

    meta = inspect_audio(wav)

    assert meta.sample_rate == SAMPLE_RATE
    assert meta.channels == CHANNELS
    assert meta.frames == n_frames
    assert math.isclose(meta.duration_seconds, n_frames / SAMPLE_RATE, rel_tol=1e-6)
    assert meta.path.endswith("clip.wav")
    assert (meta.format or "").upper() == "WAV"


def test_inspect_missing_file_raises(tmp_path):
    with pytest.raises(AudioFileNotFoundError):
        inspect_audio(tmp_path / "does_not_exist.wav")


def test_inspect_directory_raises(tmp_path):
    with pytest.raises(AudioFileNotFoundError):
        inspect_audio(tmp_path)


def test_inspect_corrupt_file_raises(tmp_path):
    bogus = tmp_path / "broken.wav"
    bogus.write_bytes(b"this is not audio")
    with pytest.raises(UnreadableAudioError):
        inspect_audio(bogus)


def test_cli_inspect_outputs_json(tmp_path, capsys):
    wav = tmp_path / "sample.wav"
    _write_wav(wav)

    rc = cli.main(["inspect", str(wav)])

    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["sample_rate"] == SAMPLE_RATE
    assert data["channels"] == CHANNELS
    assert data["path"].endswith("sample.wav")


def test_cli_inspect_missing_file_returns_error(tmp_path, capsys):
    rc = cli.main(["inspect", str(tmp_path / "nope.wav")])

    assert rc == 1
    assert "error" in capsys.readouterr().err.lower()
