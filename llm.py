"""Codex integration and deterministic extraction of Dafny source."""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from openai_codex import Codex, Sandbox
from openai_codex.client import CodexConfig


PROJECT_ROOT = Path(__file__).resolve().parent


def _codex_environment() -> dict[str, str]:
    """Provide home-directory variables required by the Codex runtime."""
    env = {}
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        env["USERPROFILE"] = userprofile
        env.setdefault("HOME", userprofile)
    for key in ("HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA"):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


@contextmanager
def isolated_codex_cwd() -> Iterator[Path]:
    """Yield an empty temporary directory outside the project."""
    with tempfile.TemporaryDirectory(prefix="dafny-agent-codex-") as directory:
        path = Path(directory).resolve()
        if path == PROJECT_ROOT or PROJECT_ROOT in path.parents:
            raise RuntimeError("Codex isolation directory must be outside the project")
        if any(path.iterdir()):
            raise RuntimeError("Codex isolation directory must start empty")
        yield path


def generate_response(prompt: str, model: str) -> str:
    """Run one read-only Codex thread outside the repository context."""
    if "HOME" not in os.environ and "USERPROFILE" in os.environ:
        os.environ["HOME"] = os.environ["USERPROFILE"]

    with isolated_codex_cwd() as cwd:
        config = CodexConfig(cwd=str(cwd), env=_codex_environment())
        with Codex(config) as codex:
            thread = codex.thread_start(
                cwd=str(cwd),
                model=model,
                sandbox=Sandbox.read_only,
            )
            result = thread.run(prompt)
            return result.final_response or ""


def extract_dafny_source(raw_response: str) -> str:
    """Extract exactly one fenced Dafny block, otherwise preserve the response."""
    lines = raw_response.splitlines(keepends=True)
    opening_lines = [
        index
        for index, line in enumerate(lines)
        if line.strip() == "```dafny"
    ]

    if len(opening_lines) != 1:
        return raw_response

    source_start = opening_lines[0] + 1
    for index in range(source_start, len(lines)):
        if lines[index].strip() == "```":
            return "".join(lines[source_start:index])
    return raw_response
