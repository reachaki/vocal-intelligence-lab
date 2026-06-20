"""Smoke tests for the package foundation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import vocal_intel
from vocal_intel import cli

SRC = str(Path(__file__).resolve().parent.parent / "src")


def test_package_imports_and_has_version():
    assert isinstance(vocal_intel.__version__, str)
    assert vocal_intel.__version__


def test_cli_version_subcommand_returns_zero(capsys):
    assert cli.main(["version"]) == 0
    assert "vocal-intel" in capsys.readouterr().out


def test_cli_no_args_prints_help(capsys):
    assert cli.main([]) == 0
    assert "usage" in capsys.readouterr().out.lower()


def test_cli_help_flag_exits_zero():
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0


def test_cli_runs_as_module():
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-m", "vocal_intel", "--version"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert "vocal-intel" in result.stdout
