"""Run and summarize the minimal controlled Dafny benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from agent import MAX_ATTEMPTS, run_agent
from prompts import PROMPT_PROFILES
from verifier import get_dafny_version


DEFAULT_CONFIG = Path("benchmark_config.json")
RESULTS_DIR = Path("results") / "benchmark"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="",
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_model_id(model: str) -> str:
    return model.replace("/", "_").replace(":", "_")


def _batch_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _manifest(batch: str, config: dict) -> dict:
    scenarios = []
    for configured_path in config["scenarios"]:
        path = Path(configured_path)
        text = path.read_text(encoding="utf-8")
        scenarios.append(
            {
                "path": str(path),
                "sha256": _sha256(text),
            }
        )

    profiles = {}
    for name in config["prompt_profiles"]:
        generation, repair = PROMPT_PROFILES[name]
        profiles[name] = {
            "generation_instructions": generation,
            "generation_sha256": _sha256(generation),
            "repair_instructions": repair,
            "repair_sha256": _sha256(repair),
        }

    global_agents = Path.home() / ".codex" / "AGENTS.md"
    global_text = global_agents.read_text(encoding="utf-8") if global_agents.exists() else ""
    return {
        "batch_id": batch,
        "status": "RUNNING",
        "design": {
            "models": config["models"],
            "prompt_profiles": config["prompt_profiles"],
            "scenarios": scenarios,
            "repetitions": config["repetitions"],
            "max_attempts": MAX_ATTEMPTS,
        },
        "prompt_profiles": profiles,
        "isolation": {
            "repository_cwd_isolated": True,
            "thread_cwd": "fresh temporary directory outside repository",
            "project_agents_loaded": False,
            "global_agents_path": str(global_agents),
            "global_agents_sha256": _sha256(global_text),
            "global_agents_empty": not global_text.strip(),
        },
        "dafny_version": get_dafny_version(),
    }


def _first_passed(result: dict) -> bool:
    attempts = result.get("attempts", [])
    return bool(attempts and attempts[0].get("passed"))


def _repair_outcome(result: dict) -> bool | None:
    if _first_passed(result):
        return None
    return result.get("final_result") == "VERIFIED"


def _summarize(results: list[dict]) -> dict:
    by_profile = {}
    for profile in sorted({result["prompt_profile"] for result in results}):
        profile_results = [
            result for result in results if result["prompt_profile"] == profile
        ]
        repairs = [
            outcome
            for outcome in (_repair_outcome(result) for result in profile_results)
            if outcome is not None
        ]
        by_profile[profile] = {
            "runs": len(profile_results),
            "verified_at_1": sum(_first_passed(result) for result in profile_results),
            "verified_within_3": sum(
                result["final_result"] == "VERIFIED" for result in profile_results
            ),
            "repair_successes": sum(repairs),
            "repair_opportunities": len(repairs),
            "total_attempts": sum(result["attempt_count"] for result in profile_results),
            "warning_count": sum(
                len(attempt.get("warnings", []))
                for result in profile_results
                for attempt in result.get("attempts", [])
            ),
        }
    return by_profile


def _report(batch: str, results: list[dict], aggregate: dict) -> str:
    lines = [
        "# Clean General vs Improved Prompt Comparison",
        "",
        f"Batch: `{batch}`",
        "",
        "Codex ran in a fresh temporary directory outside the repository for every",
        "model call. The repository `AGENTS.md` was not in the model context.",
        "",
        "## Per-Run Results",
        "",
        "| Profile | Scenario | Attempt 1 | Final | Attempts | Warnings |",
        "|---|---|---|---|---:|---:|",
    ]
    for result in sorted(results, key=lambda item: (item["prompt_profile"], item["scenario"])):
        warning_count = sum(
            len(attempt.get("warnings", [])) for attempt in result["attempts"]
        )
        lines.append(
            f"| {result['prompt_profile']} | {result['scenario']} | "
            f"{result['first_attempt_result']} | {result['final_result']} | "
            f"{result['attempt_count']} | {warning_count} |"
        )

    lines.extend(
        [
            "",
            "## Aggregate Results",
            "",
            "| Profile | Runs | Verified@1 | Verified@3 | Repair Success | Total Attempts |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for profile in sorted(aggregate):
        data = aggregate[profile]
        repair_rate = (
            f"{data['repair_successes']}/{data['repair_opportunities']}"
            if data["repair_opportunities"]
            else "n/a"
        )
        lines.append(
            f"| {profile} | {data['runs']} | {data['verified_at_1']}/{data['runs']} | "
            f"{data['verified_within_3']}/{data['runs']} | {repair_rate} | "
            f"{data['total_attempts']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "These six runs are an exploratory comparison, not a statistically stable",
            "estimate. Dafny PASS and semantic faithfulness are reviewed separately.",
            "",
        ]
    )
    return "\n".join(lines)


def _print_summary(results: list[dict], aggregate: dict) -> None:
    print("\nProfile | Scenario | Attempt 1 | Final | Attempts")
    print("--------|----------|-----------|-------|---------")
    for result in sorted(results, key=lambda item: (item["prompt_profile"], item["scenario"])):
        print(
            f"{result['prompt_profile']} | {result['scenario']} | "
            f"{result['first_attempt_result']} | {result['final_result']} | "
            f"{result['attempt_count']}"
        )
    print("\nAggregate:")
    for profile in sorted(aggregate):
        print(f"{profile}: {aggregate[profile]}")


def run_benchmark(config_path: Path, *, summarize_only: bool) -> int:
    config = _load_json(config_path)
    batch = config.get("batch_id") or _batch_id()
    manifest_path = RESULTS_DIR / f"{batch}_manifest.json"

    if summarize_only:
        paths = sorted(RESULTS_DIR.glob("*/*.json"))
        results = [_load_json(path) for path in paths]
        aggregate = _summarize(results)
        _print_summary(results, aggregate)
        return 0

    manifest = _manifest(batch, config)
    _save_json(manifest_path, manifest)
    result_paths = []

    for profile in config["prompt_profiles"]:
        for model in config["models"]:
            for repetition in range(1, int(config["repetitions"]) + 1):
                for configured_scenario in config["scenarios"]:
                    scenario = Path(configured_scenario)
                    run_id = (
                        f"{batch}_{profile}_{_safe_model_id(model)}_"
                        f"{scenario.stem}_r{repetition}"
                    )
                    print(f"\n### {profile}: {scenario.stem} with {model}")
                    run_agent(
                        scenario,
                        model=model,
                        prompt_profile=profile,
                        run_id=run_id,
                    )
                    result_path = RESULTS_DIR / profile / f"{run_id}.json"
                    result_paths.append(result_path)
                    result = _load_json(result_path)
                    if result["final_result"] == "INFRASTRUCTURE_ERROR":
                        manifest["status"] = "STOPPED_INFRASTRUCTURE_ERROR"
                        manifest["result_paths"] = [str(path) for path in result_paths]
                        _save_json(manifest_path, manifest)
                        return 1

    results = [_load_json(path) for path in result_paths]
    aggregate = _summarize(results)
    summary = {
        "batch_id": batch,
        "status": "COMPLETE",
        "result_paths": [str(path) for path in result_paths],
        "aggregate": aggregate,
    }
    _save_json(RESULTS_DIR / f"{batch}_summary.json", summary)
    (RESULTS_DIR / f"{batch}_comparison.md").write_text(
        _report(batch, results, aggregate),
        encoding="utf-8",
        newline="",
    )
    manifest["status"] = "COMPLETE"
    manifest["result_paths"] = summary["result_paths"]
    _save_json(manifest_path, manifest)
    _print_summary(results, aggregate)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the six-case Dafny benchmark.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    return run_benchmark(args.config, summarize_only=args.summarize_only)


if __name__ == "__main__":
    raise SystemExit(main())
