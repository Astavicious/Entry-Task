"""Generate, verify, and repair one Dafny program."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from llm import extract_dafny_source, generate_response
from prompts import PROMPT_PROFILES, generation_prompt, repair_prompt
from verifier import VerificationResult, verify_file


MAX_ATTEMPTS = 3
GENERATED_DIR = Path("generated")
RESULTS_DIR = Path("results") / "benchmark"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_PROMPT_PROFILE = "general"


def _save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="",
    )


def _feedback_from(result: VerificationResult) -> str:
    parts = [part for part in (result.stdout, result.stderr, result.error) if part]
    return "\n".join(parts) or "Dafny verification failed without output."


def _run_id(requirement_path: Path, model: str, profile: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_model = model.replace("/", "_").replace(":", "_")
    return f"{timestamp}_{profile}_{safe_model}_{requirement_path.stem}"


def _verification_record(result: VerificationResult) -> dict:
    return {
        "verification": "PASS" if result.passed else "FAIL",
        "passed": result.passed,
        "return_code": result.return_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "error": result.error,
        "warnings": result.warnings or [],
    }


def run_agent(
    requirement_path: Path,
    *,
    model: str,
    prompt_profile: str = DEFAULT_PROMPT_PROFILE,
    run_id: str | None = None,
) -> bool:
    """Run one generation and verifier-guided repair loop."""
    requirement = requirement_path.read_text(encoding="utf-8")
    if not requirement.strip():
        raise ValueError(f"Requirement file is empty: {requirement_path}")

    scenario = requirement_path.stem
    resolved_run_id = run_id or _run_id(requirement_path, model, prompt_profile)
    artifact_dir = GENERATED_DIR / prompt_profile / resolved_run_id
    result_path = RESULTS_DIR / prompt_profile / f"{resolved_run_id}.json"
    record = {
        "run_id": resolved_run_id,
        "scenario": scenario,
        "requested_model": model,
        "prompt_profile": prompt_profile,
        "attempts": [],
        "first_attempt_result": None,
        "final_result": None,
        "attempt_count": 0,
    }

    previous_source = ""
    verifier_feedback = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n=== Attempt {attempt} ===")
        if attempt == 1:
            prompt = generation_prompt(requirement, prompt_profile)
            prompt_kind = "generation"
        else:
            prompt = repair_prompt(
                requirement,
                previous_source,
                verifier_feedback,
                prompt_profile,
            )
            prompt_kind = "repair"

        try:
            raw_response = generate_response(prompt, model)
        except Exception as exc:
            record["attempts"].append(
                {
                    "attempt": attempt,
                    "prompt_kind": prompt_kind,
                    "raw_path": None,
                    "source_path": None,
                    "verification": "ERROR",
                    "passed": False,
                    "return_code": None,
                    "stdout": "",
                    "stderr": "",
                    "error": str(exc),
                    "warnings": [],
                }
            )
            record["attempt_count"] = attempt
            record["first_attempt_result"] = record["first_attempt_result"] or "ERROR"
            record["final_result"] = "INFRASTRUCTURE_ERROR"
            _save_json(result_path, record)
            print(f"LLM infrastructure error: {exc}")
            return False

        source = extract_dafny_source(raw_response)
        raw_path = artifact_dir / f"{scenario}_attempt_{attempt}.raw.txt"
        source_path = artifact_dir / f"{scenario}_attempt_{attempt}.dfy"
        _save_text(raw_path, raw_response)
        _save_text(source_path, source)

        print(f"Generated files: {raw_path}, {source_path}")
        result = verify_file(source_path)
        attempt_record = {
            "attempt": attempt,
            "prompt_kind": prompt_kind,
            "raw_path": str(raw_path),
            "source_path": str(source_path),
        }
        attempt_record.update(_verification_record(result))
        record["attempts"].append(attempt_record)
        record["attempt_count"] = attempt

        if attempt == 1:
            record["first_attempt_result"] = "PASS" if result.passed else "FAIL"

        if result.passed:
            record["final_result"] = "VERIFIED"
            _save_json(result_path, record)
            print(f"PASS\nFinal result: VERIFIED\nAttempts: {attempt}")
            return True

        print("FAIL")
        previous_source = source
        verifier_feedback = _feedback_from(result)

    record["final_result"] = "UNVERIFIED"
    _save_json(result_path, record)
    print(f"Final result: UNVERIFIED\nAttempts: {MAX_ATTEMPTS}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate and verify Dafny from a requirement file."
    )
    parser.add_argument("requirement", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--prompt-profile",
        choices=sorted(PROMPT_PROFILES),
        default=DEFAULT_PROMPT_PROFILE,
    )
    parser.add_argument("--run-id")
    args = parser.parse_args()

    if not args.requirement.is_file():
        parser.error(f"Requirement file not found: {args.requirement}")

    return 0 if run_agent(
        args.requirement,
        model=args.model,
        prompt_profile=args.prompt_profile,
        run_id=args.run_id,
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
