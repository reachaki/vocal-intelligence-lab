"""Tests for the neutral transcript-metadata document (Phase 13a).

The ``transcript-info`` command reads one local plain-text file and emits a small
metadata document (``document_type`` ``"transcript_metadata"``,
``schema_version`` ``"1.0"``) made of structural counts only. These tests pin the
document shape and ordering against a committed golden manifest, pin exact counts
for fixed synthetic inputs, confirm error parity with the other CLI commands, and
guard the safety properties: the transcript text never leaks into the output, the
module stays isolated from the audio/summary/recommendation/policy code, and no
inference vocabulary appears in the output.

All fixtures are synthetic placeholder text written into pytest's temporary
directory, so the suite commits no transcript files.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from vocal_intel import cli, transcript_meta
from vocal_intel.summary import field_paths
from vocal_intel.transcript_meta import (
    LIMITATIONS_TEXT,
    TranscriptMetaError,
    metadata_from_file,
    metadata_from_text,
)

TOP_LEVEL_KEYS = [
    "document_type",
    "schema_version",
    "source",
    "character_count",
    "word_count",
    "line_count",
    "limitations",
]
SOURCE_KEYS = ["path", "format"]

MANIFEST_PATH = (
    Path(__file__).resolve().parent / "data" / "schema_manifest_transcript_1_0.json"
)


def _write(path: Path, content: str) -> Path:
    """Write *content* as exact UTF-8 bytes (no newline translation)."""
    path.write_bytes(content.encode("utf-8"))
    return path


def _pinned_dumps(d: dict) -> str:
    return json.dumps(
        d,
        indent=2,
        ensure_ascii=True,
        sort_keys=False,
        separators=(",", ": "),
    )


# --- 1. shape / order -----------------------------------------------------


def test_document_top_level_keys_exact_and_ordered():
    d = metadata_from_text("hello world").to_dict()

    assert list(d.keys()) == TOP_LEVEL_KEYS
    assert list(d["source"].keys()) == SOURCE_KEYS
    assert d["document_type"] == "transcript_metadata"
    assert d["schema_version"] == "1.0"


def test_field_paths_match_golden_manifest_ordered():
    d = metadata_from_text("hello world", path="x.txt", fmt="txt").to_dict()
    live = field_paths(d)
    golden = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    # Order-sensitive: catches add, remove, rename, and reorder.
    assert live == golden
    assert len(golden) == 8


# --- 2. deterministic counts on fixed synthetic inputs --------------------


@pytest.mark.parametrize(
    "content, expected",
    [
        ("", (0, 0, 0)),
        ("hello", (5, 1, 1)),
        ("alpha beta\ngamma\n", (17, 3, 2)),
        ("a\U0001F399b", (3, 1, 1)),  # one multibyte code point counts as one char
        ("a\r\nb", (4, 2, 2)),  # CRLF: the \r is one code point
        ("a\nb", (3, 2, 2)),  # LF counterpart of the CRLF case
        ("   \n\t", (5, 0, 2)),  # whitespace-only: zero words, two lines
    ],
)
def test_counts_are_exact_for_fixed_inputs(content, expected):
    meta = metadata_from_text(content)
    assert (meta.character_count, meta.word_count, meta.line_count) == expected


def test_from_file_counts_and_source_fields(tmp_path):
    f = _write(tmp_path / "notes.txt", "alpha beta\ngamma\n")
    meta = metadata_from_file(str(f))
    d = meta.to_dict()

    assert d["character_count"] == 17
    assert d["word_count"] == 3
    assert d["line_count"] == 2
    assert d["source"]["path"] == str(f)
    assert d["source"]["format"] == "txt"


def test_markdown_extension_reports_md_format(tmp_path):
    f = _write(tmp_path / "summary.md", "# Title\n\ntwo words\n")
    d = metadata_from_file(str(f)).to_dict()
    assert d["source"]["format"] == "md"


# --- 3. determinism / byte-stability --------------------------------------


def test_serialized_output_is_byte_identical_across_calls():
    first = metadata_from_text("a b c\n").to_json()
    second = metadata_from_text("a b c\n").to_json()
    assert first == second


def test_serialized_output_round_trips_as_json():
    serialized = metadata_from_text("a b c\n", path="x.txt", fmt="txt").to_json()
    json.loads(serialized)
    assert "NaN" not in serialized
    assert "Infinity" not in serialized


def test_emitted_counts_are_native_ints():
    d = metadata_from_text("a b c").to_dict()
    for key in ("character_count", "word_count", "line_count"):
        assert type(d[key]) is int


# --- 4. safety: no transcript text leaks into the output ------------------


def test_transcript_body_does_not_leak_into_output(tmp_path):
    sentinel = "ZZQSENTINELWORD42"
    f = _write(tmp_path / "private.txt", f"some {sentinel} text here\n")
    serialized = metadata_from_file(str(f)).to_json()

    # The path is echoed by design, but the file BODY must never appear.
    assert sentinel not in serialized
    assert "some" not in serialized
    assert "text here" not in serialized


def test_module_is_isolated_from_audio_and_policy_code():
    source = Path(transcript_meta.__file__).read_text(encoding="utf-8")
    # Tripwire against scope creep: this module must never reach into the audio,
    # summary, recommendation, or policy code, so transcript metadata can never
    # influence those documents.
    for forbidden in (
        "vocal_intel.summary",
        "vocal_intel.recommend",
        "vocal_intel.policy",
        "vocal_intel.ingest",
        "vocal_intel.preprocess",
        "vocal_intel.loudness",
        "vocal_intel.pitch",
        "vocal_intel.pace",
        "vocal_intel.pauses",
        "vocal_intel.vad",
        "vocal_intel.config",
        "import numpy",
    ):
        assert forbidden not in source, forbidden


def test_module_imports_are_a_closed_stdlib_allowlist():
    # Stronger than the substring tripwire above: parse the import graph and
    # require every imported module to be on a closed standard-library allowlist,
    # and forbid dynamic-import escape hatches. This makes it structurally
    # impossible for the transcript-metadata code to reach the audio, summary,
    # recommendation, or policy code (so it can never influence a conversation
    # recommendation), even via a dynamic import a substring scan would miss.
    #
    # An intended new standard-library import must be added to ``allowed`` in the
    # same change; a third-party or in-package import must never appear here.
    source = Path(transcript_meta.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # A relative import (level > 0) would pull in sibling package modules.
            assert node.level == 0, "transcript_meta must not use relative imports"
            imported_roots.add((node.module or "").split(".")[0])

    allowed = {"__future__", "json", "dataclasses", "pathlib"}
    assert imported_roots <= allowed, sorted(imported_roots - allowed)

    # No dynamic-import escape hatches that a static import scan cannot see.
    assert "importlib" not in source
    assert "__import__" not in source


_INFERENCE_WORDS = [
    "emotion",
    "intent",
    "sentiment",
    "deception",
    "personality",
    "dominance",
    "confidence",
    "mood",
    "feeling",
    "filler",
    "unfinished",
    "hesitat",
    "likely",
    "probably",
    "recommend",
]


def test_output_contains_no_inference_vocabulary():
    d = metadata_from_text("alpha beta gamma\n", path="x.txt", fmt="txt").to_dict()
    haystack = _pinned_dumps(d).lower()
    for word in _INFERENCE_WORDS:
        assert word not in haystack, word


def test_limitations_text_is_pinned():
    d = metadata_from_text("hello").to_dict()
    assert d["limitations"] == LIMITATIONS_TEXT


def test_key_set_is_a_closed_neutral_allowlist():
    # The document must carry only these neutral keys; nothing inference-shaped
    # may be added without an intended schema change.
    d = metadata_from_text("hello").to_dict()
    assert set(d.keys()) == set(TOP_LEVEL_KEYS)
    assert set(d["source"].keys()) == set(SOURCE_KEYS)


# --- 5. errors mirror the other CLI commands ------------------------------


def test_missing_file_raises(tmp_path):
    with pytest.raises(TranscriptMetaError):
        metadata_from_file(str(tmp_path / "nope.txt"))


def test_directory_path_raises(tmp_path):
    with pytest.raises(TranscriptMetaError):
        metadata_from_file(str(tmp_path))


def test_unsupported_extension_raises(tmp_path):
    f = _write(tmp_path / "clip.wav", "not really audio")
    with pytest.raises(TranscriptMetaError):
        metadata_from_file(str(f))


def test_non_utf8_file_raises(tmp_path):
    bad = tmp_path / "broken.txt"
    bad.write_bytes(b"\xff\xfe\x00\x01")
    with pytest.raises(TranscriptMetaError):
        metadata_from_file(str(bad))


def test_oversize_file_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(transcript_meta, "MAX_FILE_BYTES", 4)
    f = _write(tmp_path / "big.txt", "0123456789")
    with pytest.raises(TranscriptMetaError):
        metadata_from_file(str(f))


# --- 6. CLI integration ---------------------------------------------------


def test_cli_transcript_info_valid_file_returns_zero(tmp_path, capsys):
    f = _write(tmp_path / "clip.txt", "alpha beta\ngamma\n")

    rc = cli.main(["transcript-info", str(f)])

    assert rc == 0
    d = json.loads(capsys.readouterr().out)
    assert list(d.keys()) == TOP_LEVEL_KEYS
    assert d["document_type"] == "transcript_metadata"
    assert d["schema_version"] == "1.0"
    assert d["character_count"] == 17
    assert d["word_count"] == 3
    assert d["line_count"] == 2
    assert d["source"]["path"].endswith("clip.txt")
    assert d["source"]["format"] == "txt"


def test_cli_transcript_info_missing_path_returns_one_empty_stdout(tmp_path, capsys):
    rc = cli.main(["transcript-info", str(tmp_path / "nope.txt")])

    captured = capsys.readouterr()
    assert rc == 1
    assert "error:" in captured.err
    assert captured.out == ""


def test_cli_transcript_info_unsupported_extension_returns_one(tmp_path, capsys):
    f = _write(tmp_path / "clip.wav", "data")
    rc = cli.main(["transcript-info", str(f)])

    captured = capsys.readouterr()
    assert rc == 1
    assert "error:" in captured.err
    assert captured.out == ""


def test_cli_transcript_info_non_utf8_returns_one(tmp_path, capsys):
    bad = tmp_path / "broken.txt"
    bad.write_bytes(b"\xff\xfe\x00\x01")
    rc = cli.main(["transcript-info", str(bad)])

    captured = capsys.readouterr()
    assert rc == 1
    assert "error:" in captured.err
    assert captured.out == ""


def test_transcript_info_appears_in_help(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    help_text = capsys.readouterr().out.lower()
    assert "transcript-info" in help_text


def test_cli_lazy_import_keeps_transcript_module_out_of_top_level():
    parser_source = Path(cli.__file__).read_text(encoding="utf-8")
    # The transcript_meta import lives inside the runner, not at module top, so
    # version/help do not pull it in.
    assert "from vocal_intel import transcript_meta" in parser_source
    top_section = parser_source.split("def _run_transcript_info", 1)[0]
    assert "import transcript_meta" not in top_section


# --- 7. existing privacy guard is unaffected ------------------------------


def test_privacy_guard_still_protects_transcript_artefacts():
    from vocal_intel.privacy import is_disallowed

    # The metadata command accepts local .txt/.md inputs, but the staged-file
    # guard must still block transcript-shaped artefacts from being committed.
    assert is_disallowed("call.vtt")
    assert is_disallowed("notes/transcripts/session.txt")
    assert is_disallowed("meeting-notes/standup.md")
    # A plain text file is still allowed (the guard stays narrow).
    assert not is_disallowed("notes.txt")
