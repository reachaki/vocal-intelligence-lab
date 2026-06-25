"""Command-line interface for Vocal Intelligence Lab.

The CLI is built up phase by phase. It currently provides a ``version`` command,
an ``inspect`` command that reports metadata for a local audio file, a
``summarize`` command that emits the unified versioned feature summary as JSON,
a ``recommend`` command that emits the opt-in conversation-recommendation
document as JSON, and a ``transcript-info`` command that reports neutral
structural metadata for a local text transcript as JSON.
"""

from __future__ import annotations

import argparse
import json
import sys

from vocal_intel import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="vocal-intel",
        description="Local-first vocal feature analysis (research prototype).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"vocal-intel {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("version", help="Print the installed version.")

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect a local audio file and print its metadata as JSON.",
    )
    inspect_parser.add_argument(
        "path",
        help="Path to a local audio file (WAV is supported and validated).",
    )

    summarize_parser = subparsers.add_parser(
        "summarize",
        help="Summarise a local audio file's vocal features as versioned JSON.",
    )
    summarize_parser.add_argument(
        "path",
        help="Path to a local audio file (WAV is supported and validated).",
    )

    recommend_parser = subparsers.add_parser(
        "recommend",
        help="Recommend a conversation-timing action for a local audio file as versioned JSON.",
    )
    recommend_parser.add_argument(
        "path",
        help="Path to a local audio file (WAV is supported and validated).",
    )

    transcript_parser = subparsers.add_parser(
        "transcript-info",
        help="Report neutral structural metadata for a local text transcript as JSON.",
    )
    transcript_parser.add_argument(
        "path",
        help="Path to a local plain-text transcript file (.txt or .md, UTF-8).",
    )
    return parser


def _run_inspect(path: str) -> int:
    # Imported lazily so version/help do not require the audio stack.
    from vocal_intel.ingest import AudioIngestionError, inspect_audio

    try:
        metadata = inspect_audio(path)
    except AudioIngestionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(metadata.to_dict(), indent=2))
    return 0


def _run_summarize(path: str) -> int:
    # Imported lazily so version/help do not require the audio stack.
    from vocal_intel.ingest import AudioIngestionError
    from vocal_intel import summary

    try:
        feature_summary = summary.summarize_file(path)
    except AudioIngestionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            feature_summary.to_dict(),
            indent=2,
            ensure_ascii=True,
            sort_keys=False,
            separators=(",", ": "),
        )
    )
    return 0


def _run_recommend(path: str) -> int:
    # Imported lazily so version/help do not require the audio stack.
    from vocal_intel.ingest import AudioIngestionError
    from vocal_intel import recommend

    # Assemble the full document before printing anything, so a post-ingest
    # failure cannot leave a partial document on stdout.
    try:
        document = recommend.recommend_file(path)
    except AudioIngestionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(recommend.to_json(document))
    return 0


def _run_transcript_info(path: str) -> int:
    # Imported lazily so version/help do not require the transcript module.
    from vocal_intel import transcript_meta

    try:
        metadata = transcript_meta.metadata_from_file(path)
    except transcript_meta.TranscriptMetaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(metadata.to_json())
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        print(f"vocal-intel {__version__}")
        return 0
    if args.command == "inspect":
        return _run_inspect(args.path)
    if args.command == "summarize":
        return _run_summarize(args.path)
    if args.command == "recommend":
        return _run_recommend(args.path)
    if args.command == "transcript-info":
        return _run_transcript_info(args.path)

    # No subcommand given: show help as a friendly default.
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
