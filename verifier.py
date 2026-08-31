"""Small wrapper around the Dafny command-line verifier."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VerificationResult:
    """The information the agent needs from one Dafny verification run."""

    passed: bool
    return_code: int | None
    stdout: str
    stderr: str
    error: str | None = None
    warnings: list[str] | None = None


def _extract_warnings(stdout: str, stderr: str) -> list[str]:
    """Return warning lines from Dafny output without changing pass/fail logic."""
    output = "\n".join(part for part in (stdout, stderr) if part)
    return [
        line.strip()
        for line in output.splitlines()
        if re.search(r"\bWarning:", line)
    ]


def _dafny_command() -> str:
    """Return the configured Dafny executable or the project-local fallback."""
    configured_path = os.environ.get("DAFNY_BIN")
    if configured_path:
        return configured_path

    project_root = Path(__file__).resolve().parent
    local_windows_path = project_root / ".tools" / "dafny" / "dafny" / "Dafny.exe"
    if local_windows_path.exists():
        return str(local_windows_path)

    return "dafny"


def get_dafny_version() -> str:
    """Return the version text from the same Dafny executable we verify with."""
    command = _dafny_command()

    try:
        completed = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return f"unavailable: Dafny executable was not found: {command}"

    output = "\n".join(
        part for part in (completed.stdout, completed.stderr) if part
    ).strip()
    return output or f"unavailable: Dafny exited with code {completed.returncode}"


def verify_file(path: str | Path, timeout_seconds: int = 60) -> VerificationResult:
    """Run Dafny verification and return its complete result."""
    command = [_dafny_command(), "verify", str(path), "--allow-warnings"]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return VerificationResult(
            passed=False,
            return_code=None,
            stdout="",
            stderr="",
            error=f"Dafny executable was not found: {_dafny_command()}",
            warnings=[],
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        return VerificationResult(
            passed=False,
            return_code=None,
            stdout=stdout,
            stderr=stderr,
            error=f"Dafny verification timed out after {timeout_seconds} seconds",
            warnings=_extract_warnings(stdout, stderr),
        )

    return VerificationResult(
        passed=completed.returncode == 0,
        return_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        warnings=_extract_warnings(completed.stdout, completed.stderr),
    )
