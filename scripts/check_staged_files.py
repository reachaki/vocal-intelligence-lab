#!/usr/bin/env python3
"""Reject disallowed files from a commit.

By default this inspects the staged file list (``git diff --cached
--name-only``) and exits non-zero if any private audio, transcript, or
local-only file is staged. Intended for use as a pre-commit hook:

    python scripts/check_staged_files.py

Paths may also be passed as arguments, which is useful for testing:

    python scripts/check_staged_files.py recording.wav .local/notes.md
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Allow running from a source checkout without installation.
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from vocal_intel.privacy import find_disallowed  # noqa: E402


def staged_paths() -> list[str]:
    """Return the list of staged file paths."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = args or staged_paths()
    disallowed = find_disallowed(paths)
    if disallowed:
        print("Refusing to continue: disallowed files detected:", file=sys.stderr)
        for path in disallowed:
            print(f"  - {path}", file=sys.stderr)
        print(
            "Private audio, transcript, and local-only files must not be committed.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
