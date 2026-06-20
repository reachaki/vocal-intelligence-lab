"""Command-line interface for Vocal Intelligence Lab.

Phase 0 provides a minimal CLI shell only. Audio inspection and analysis
commands are added in later phases.
"""

from __future__ import annotations

import argparse

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
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        print(f"vocal-intel {__version__}")
        return 0

    # No subcommand given: show help as a friendly default.
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
