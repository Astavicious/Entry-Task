"""Codex integration and deterministic extraction of Dafny source."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from openai_codex import Codex, Sandbox
from openai_codex.client import CodexConfig


@dataclass
class LLMResult:
    """Raw model response plus metadata exposed by the Codex SDK."""

    final_response: str
    actual_model: str | None
    usage: dict[str, Any] | None
    duration_ms: int | None


def _to_plain_data(value: object) -> object:
    """Convert SDK models into JSON-friendly values where possible."""
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return value


def generate_response(prompt: str, model: str) -> str:
    """Run one read-only Codex thread with an explicit model."""
    return generate_response_with_metadata(prompt, model).final_response


def _codex_environment() -> dict[str, str]:
    """Provide home-directory variables expected by the Codex runtime."""
    env = {}
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        env["USERPROFILE"] = userprofile
        env.setdefault("HOME", userprofile)
    for key in ("HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA"):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def generate_response_with_metadata(prompt: str, model: str) -> LLMResult:
    """Run one read-only Codex thread and return response metadata."""
    if "HOME" not in os.environ and "USERPROFILE" in os.environ:
        os.environ["HOME"] = os.environ["USERPROFILE"]
    with Codex(CodexConfig(env=_codex_environment())) as codex:
        thread = codex.thread_start(model=model, sandbox=Sandbox.read_only)
        result = thread.run(prompt)
        return LLMResult(
            final_response=result.final_response or "",
            actual_model=None,
            usage=_to_plain_data(result.usage),
            duration_ms=result.duration_ms,
        )


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
