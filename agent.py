"""Command-line agent that generates and verifies Dafny programs."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from llm import extract_dafny_source, generate_response_with_metadata
from prompts import PROMPT_PROFILES, generation_prompt, repair_prompt
from verifier import VerificationResult, get_dafny_version, verify_file


MAX_ATTEMPTS = 3
GENERATED_DIR = Path("generated")
BENCHMARK_RESULTS_DIR = Path("results") / "benchmark"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_PROMPT_PROFILE = "general"


SCENARIO_REQUIREMENTS = {
    "bounded_counter": [
        "The counter must never be negative.",
        "The counter must never exceed a configurable maximum.",
        "Increment adds one when the old counter is below the maximum; otherwise it leaves the counter unchanged.",
        "Reset sets the counter to zero.",
    ],
    "authorized_access": [
        "An unauthorized request must never result in authorized access.",
        "Granting authorization should update the authorization state correctly.",
        "Revoking authorization should update the authorization state correctly.",
    ],
    "account_transfer": [
        "The transfer amount must not be negative.",
        "The transfer amount must not exceed the source account's balance.",
        "A successful transfer must leave both accounts with non-negative balances.",
        "A successful transfer must set the source balance to its old balance minus the amount.",
        "A successful transfer must set the destination balance to its old balance plus the amount.",
        "A successful transfer must preserve the combined balance of the two accounts.",
    ],
}


def _save_text(path: Path, text: str) -> None:
    """Save text without changing its newline characters."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text)


def _save_json(path: Path, data: dict) -> None:
    """Write one readable experiment result file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def _package_version(package_name: str) -> str | None:
    """Return an installed package version, or None when unavailable."""
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _environment_metadata() -> dict:
    """Collect lightweight metadata for reproducing an experiment."""
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "dafny_version": get_dafny_version(),
        "openai_codex_version": _package_version("openai-codex"),
        "codex_model_env": os.environ.get("CODEX_MODEL"),
    }


def _feedback_from(result: VerificationResult) -> str:
    """Combine all verifier details for the next repair prompt."""
    parts = []

    if result.stdout:
        parts.append(result.stdout)
    if result.stderr:
        parts.append(result.stderr)
    if result.error:
        parts.append(result.error)

    return "\n".join(parts) or "Dafny verification failed without additional output."


def _make_run_id(requirement_path: Path, model: str) -> str:
    """Create a readable run ID when the caller does not provide one."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_model = model.replace("/", "_").replace(":", "_")
    return f"{timestamp}_{safe_model}_{requirement_path.stem}"


def _manual_review_template(scenario_name: str) -> dict:
    """Create human-controlled review fields for later semantic scoring."""
    requirements = SCENARIO_REQUIREMENTS.get(scenario_name, [])
    max_score = len(requirements) * 2
    return {
        "status": "PENDING",
        "scale": {
            "COVERED": 2,
            "WEAKENED": 1,
            "MISSING": 0,
        },
        "requirements": [
            {
                "requirement": requirement,
                "score": None,
                "label": None,
                "notes": "",
            }
            for requirement in requirements
        ],
        "unjustified_requires": [],
        "unrequested_assumptions": [],
        "vacuous_or_trivial_specifications": [],
        "suspicious_assume_usage": [],
        "requirements_weakened_during_repair": [],
        "normalized_coverage": None,
        "max_score": max_score,
        "notes": [],
    }


def _verification_record(result: VerificationResult) -> dict:
    """Convert one Dafny verifier result into JSON-friendly data."""
    warnings = result.warnings or []
    return {
        "verification": "PASS" if result.passed else "FAIL",
        "passed": result.passed,
        "return_code": result.return_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "error": result.error,
        "warnings": warnings,
        "warning_count": len(warnings),
    }


def run_agent(
    requirement_path: Path,
    *,
    model: str,
    prompt_profile: str = DEFAULT_PROMPT_PROFILE,
    run_id: str | None = None,
    repetition: int | None = None,
) -> bool:
    """Generate, verify, and repair one natural-language requirement."""
    requirement = requirement_path.read_text(encoding="utf-8")
    scenario_name = requirement_path.stem
    resolved_run_id = run_id or _make_run_id(requirement_path, model)
    run_generated_dir = GENERATED_DIR / prompt_profile / resolved_run_id
    result_path = (
        BENCHMARK_RESULTS_DIR / prompt_profile / f"{resolved_run_id}.json"
    )
    run_started = time.perf_counter()

    experiment = {
        "run_id": resolved_run_id,
        "scenario": scenario_name,
        "requirement_path": str(requirement_path),
        "repetition": repetition,
        "requested_model": model,
        "prompt_profile": prompt_profile,
        "actual_model": None,
        "model_metadata": {
            "type": None,
            "tier": None,
            "architecture": None,
            "parameter_count": None,
        },
        "environment": _environment_metadata(),
        "attempts": [],
        "first_attempt_result": None,
        "final_result": None,
        "attempt_count": 0,
        "total_elapsed_seconds": None,
        "tokens": None,
        "credits": None,
        "cost": None,
        "manual_review": _manual_review_template(scenario_name),
    }
    previous_source = ""
    verifier_feedback = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n=== Attempt {attempt} ===")

        if attempt == 1:
            print(f"Generating Dafny with model: {model}")
            prompt = generation_prompt(requirement, prompt_profile)
            prompt_kind = "generation"
        else:
            print(f"Generating repair with model: {model}")
            prompt = repair_prompt(
                requirement,
                previous_source,
                verifier_feedback,
                prompt_profile,
            )
            prompt_kind = "repair"

        generation_started = time.perf_counter()
        try:
            llm_result = generate_response_with_metadata(prompt, model)
        except Exception as exc:
            elapsed = time.perf_counter() - generation_started
            print(f"LLM error: {exc}")
            experiment["attempts"].append(
                {
                    "attempt": attempt,
                    "prompt_kind": prompt_kind,
                    "raw_response": None,
                    "dafny_source": None,
                    "raw_path": None,
                    "source_path": None,
                    "generation_elapsed_seconds": elapsed,
                    "llm_duration_ms": None,
                    "usage": None,
                    "verification_elapsed_seconds": None,
                    "verification": "ERROR",
                    "passed": False,
                    "return_code": None,
                    "stdout": "",
                    "stderr": "",
                    "error": str(exc),
                    "warnings": [],
                    "warning_count": 0,
                }
            )
            experiment["attempt_count"] = attempt
            experiment["total_elapsed_seconds"] = time.perf_counter() - run_started
            if attempt == 1:
                experiment["first_attempt_result"] = "ERROR"
            experiment["final_result"] = "INFRASTRUCTURE_ERROR"
            experiment["infrastructure_error"] = str(exc)
            _save_json(result_path, experiment)
            print(f"Results saved to: {result_path}")
            print("Final result: INFRASTRUCTURE_ERROR")
            return False

        generation_elapsed = time.perf_counter() - generation_started
        if llm_result.actual_model is not None:
            experiment["actual_model"] = llm_result.actual_model
        if llm_result.usage is not None:
            experiment["tokens"] = llm_result.usage

        raw_response = llm_result.final_response
        dafny_source = extract_dafny_source(raw_response)
        raw_path = run_generated_dir / f"{scenario_name}_attempt_{attempt}.raw.txt"
        source_path = run_generated_dir / f"{scenario_name}_attempt_{attempt}.dfy"
        _save_text(raw_path, raw_response)
        _save_text(source_path, dafny_source)

        print(f"Raw response saved to: {raw_path}")
        print(f"Dafny source saved to: {source_path}")
        print("\nGenerated Dafny source:")
        print(dafny_source)

        print("Running Dafny verifier...")
        verification_started = time.perf_counter()
        result = verify_file(source_path)
        verification_elapsed = time.perf_counter() - verification_started

        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(result.stderr, end="" if result.stderr.endswith("\n") else "\n")
        if result.error:
            print(result.error)

        attempt_record = {
            "attempt": attempt,
            "prompt_kind": prompt_kind,
            "raw_response": raw_response,
            "dafny_source": dafny_source,
            "raw_path": str(raw_path),
            "source_path": str(source_path),
            "generation_elapsed_seconds": generation_elapsed,
            "llm_duration_ms": llm_result.duration_ms,
            "usage": llm_result.usage,
            "verification_elapsed_seconds": verification_elapsed,
        }
        attempt_record.update(_verification_record(result))
        experiment["attempts"].append(attempt_record)
        experiment["attempt_count"] = attempt
        if attempt == 1:
            experiment["first_attempt_result"] = (
                "PASS" if result.passed else "FAIL"
            )

        if result.passed:
            experiment["final_result"] = "VERIFIED"
            experiment["total_elapsed_seconds"] = time.perf_counter() - run_started
            _save_json(result_path, experiment)
            print("PASS")
            print(f"\nFinal result: VERIFIED\nAttempts: {attempt}")
            print(f"Results saved to: {result_path}")
            return True

        print("FAIL")
        previous_source = dafny_source
        verifier_feedback = _feedback_from(result)

        if attempt < MAX_ATTEMPTS:
            print("\nVerifier feedback:")
            print(verifier_feedback)

    experiment["final_result"] = "UNVERIFIED"
    experiment["total_elapsed_seconds"] = time.perf_counter() - run_started
    _save_json(result_path, experiment)
    print(f"\nFinal result: UNVERIFIED\nAttempts: {MAX_ATTEMPTS}")
    print(f"Results saved to: {result_path}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate and verify Dafny code from a requirement file."
    )
    parser.add_argument("requirement", type=Path)
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Codex model to request explicitly. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--prompt-profile",
        choices=sorted(PROMPT_PROFILES),
        default=DEFAULT_PROMPT_PROFILE,
        help=(
            "Instruction profile to use. "
            f"Default: {DEFAULT_PROMPT_PROFILE}"
        ),
    )
    parser.add_argument(
        "--run-id",
        help="Unique ID for generated artifacts and benchmark JSON.",
    )
    parser.add_argument(
        "--repetition",
        type=int,
        help="Optional repetition number recorded in benchmark metadata.",
    )
    args = parser.parse_args()

    if not args.requirement.is_file():
        parser.error(f"Requirement file not found: {args.requirement}")

    return 0 if run_agent(
        args.requirement,
        model=args.model,
        prompt_profile=args.prompt_profile,
        run_id=args.run_id,
        repetition=args.repetition,
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
