"""Run and summarize the controlled Dafny generation benchmark."""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from agent import MAX_ATTEMPTS, run_agent


DEFAULT_CONFIG = Path("benchmark_config.json")
RESULTS_DIR = Path("results") / "benchmark"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def _safe_model_id(model: str) -> str:
    return model.replace("/", "_").replace(":", "_")


def _batch_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _manual_review_complete(result: dict) -> bool:
    return result.get("manual_review", {}).get("status") == "COMPLETE"


def _coverage(result: dict) -> float | None:
    review = result.get("manual_review", {})
    if review.get("normalized_coverage") is not None:
        return review["normalized_coverage"]
    requirements = review.get("requirements", [])
    scores = [item.get("score") for item in requirements]
    if not requirements or any(score is None for score in scores):
        return None
    max_score = review.get("max_score") or len(requirements) * 2
    if max_score == 0:
        return None
    return sum(scores) / max_score


def _has_review_problems(result: dict) -> bool:
    review = result.get("manual_review", {})
    problem_fields = [
        "unjustified_requires",
        "unrequested_assumptions",
        "vacuous_or_trivial_specifications",
        "suspicious_assume_usage",
        "requirements_weakened_during_repair",
    ]
    if any(review.get(field) for field in problem_fields):
        return True
    return any(
        item.get("label") in {"WEAKENED", "MISSING"} or item.get("score") in {0, 1}
        for item in review.get("requirements", [])
    )


def _faithful(result: dict) -> bool | None:
    if not _manual_review_complete(result):
        return None
    return (
        result.get("final_result") == "VERIFIED"
        and _coverage(result) == 1
        and not _has_review_problems(result)
    )


def _first_attempt_passed(result: dict) -> bool:
    attempts = result.get("attempts", [])
    return bool(attempts and attempts[0].get("passed"))


def _final_verified(result: dict) -> bool:
    return result.get("final_result") == "VERIFIED"


def _warning_count(result: dict) -> int:
    return sum(attempt.get("warning_count", 0) for attempt in result.get("attempts", []))


def _repair_success(result: dict) -> bool | None:
    attempts = result.get("attempts", [])
    if not attempts or attempts[0].get("passed"):
        return None
    return _final_verified(result)


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "PENDING"
    return "YES" if value else "NO"


def _format_number(value: float | int | None) -> str:
    if value is None:
        return "PENDING"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [
        max(len(str(row[index])) for row in [headers, *rows])
        for index in range(len(headers))
    ]
    header_line = " | ".join(
        str(header).ljust(widths[index]) for index, header in enumerate(headers)
    )
    divider = " | ".join("-" * width for width in widths)
    print(header_line)
    print(divider)
    for row in rows:
        print(
            " | ".join(
                str(value).ljust(widths[index])
                for index, value in enumerate(row)
            )
        )


def _per_run_rows(results: list[dict]) -> list[list[str]]:
    rows = []
    for result in results:
        rows.append(
            [
                result.get("prompt_profile", ""),
                result.get("requested_model", ""),
                result.get("scenario", ""),
                "PASS" if _first_attempt_passed(result) else result.get("first_attempt_result", ""),
                result.get("final_result", ""),
                str(result.get("attempt_count", "")),
                _format_bool(_faithful(result)),
                _format_number(_coverage(result)),
                str(_warning_count(result)),
                _format_number(result.get("total_elapsed_seconds")),
            ]
        )
    return rows


def _rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{numerator}/{denominator}"


def _per_model_rows(results: list[dict]) -> list[list[str]]:
    rows = []
    groups = sorted({
        (
            result.get("prompt_profile", ""),
            result.get("requested_model", ""),
        )
        for result in results
    })
    for prompt_profile, model in groups:
        model_results = [
            result for result in results
            if result.get("requested_model") == model
            and result.get("prompt_profile", "") == prompt_profile
        ]
        verified = [result for result in model_results if _final_verified(result)]
        review_complete = [
            result for result in model_results if _manual_review_complete(result)
        ]
        faithful = [result for result in review_complete if _faithful(result)]
        repair_attempts = [
            result for result in model_results if _repair_success(result) is not None
        ]
        repair_successes = [
            result for result in repair_attempts if _repair_success(result)
        ]
        successful_attempt_counts = [
            result.get("attempt_count", MAX_ATTEMPTS)
            for result in verified
        ]
        coverages = [
            value for value in (_coverage(result) for result in review_complete)
            if value is not None
        ]
        rows.append(
            [
                prompt_profile,
                model,
                str(len(model_results)),
                _rate(sum(_first_attempt_passed(result) for result in model_results), len(model_results)),
                _rate(len(verified), len(model_results)),
                _rate(sum(_first_attempt_passed(result) for result in faithful), len(review_complete)),
                _rate(len(faithful), len(review_complete)),
                _rate(len(repair_successes), len(repair_attempts)),
                _format_number(
                    statistics.median(successful_attempt_counts)
                    if successful_attempt_counts
                    else None
                ),
                _format_number(
                    statistics.mean(coverages)
                    if coverages
                    else None
                ),
            ]
        )
    return rows


def summarize(result_paths: list[Path]) -> None:
    results = [_load_json(path) for path in result_paths]
    results.sort(
        key=lambda result: (
            result.get("requested_model", ""),
            result.get("prompt_profile", ""),
            result.get("scenario", ""),
            result.get("repetition") or 0,
        )
    )

    print("\nPer-run results")
    _print_table(
        [
            "Prompt",
            "Model",
            "Scenario",
            "Attempt 1",
            "Final",
            "Attempts",
            "Faithful",
            "Coverage",
            "Warnings",
            "Time",
        ],
        _per_run_rows(results),
    )

    print("\nPer-model results")
    _print_table(
        [
            "Prompt",
            "Model",
            "Runs",
            "Verified@1",
            "Verified@3",
            "Faithful@1",
            "Faithful@3",
            "Repair Success",
            "Median Attempts",
            "Mean Coverage",
        ],
        _per_model_rows(results),
    )


def _summary_input_paths(*, include_smoke: bool) -> list[Path]:
    paths = []
    for path in sorted(RESULTS_DIR.glob("*/*.json")):
        name = path.name
        if name.endswith("_summary.json"):
            continue
        if not include_smoke and name.startswith("smoke_"):
            continue
        if "attempts" not in _load_json(path):
            continue
        paths.append(path)
    return paths


def run_benchmark(config_path: Path, *, summarize_only: bool, include_smoke: bool) -> int:
    config = _load_json(config_path)
    models = config["models"]
    prompt_profiles = config.get("prompt_profiles", ["general"])
    scenarios = [Path(path) for path in config["scenarios"]]
    repetitions = int(config.get("repetitions", 1))
    batch = config.get("batch_id") or _batch_id()
    result_paths: list[Path] = []

    if summarize_only:
        result_paths = _summary_input_paths(include_smoke=include_smoke)
        summarize(result_paths)
        return 0

    for repetition in range(1, repetitions + 1):
        for prompt_profile in prompt_profiles:
            for model in models:
                for scenario in scenarios:
                    run_id = (
                        f"{batch}_{prompt_profile}_{_safe_model_id(model)}_"
                        f"{scenario.stem}_r{repetition}"
                    )
                    print(
                        f"\n### Running {scenario.stem} with {model}, "
                        f"{prompt_profile} prompt (repetition {repetition})"
                    )
                    run_agent(
                        scenario,
                        model=model,
                        prompt_profile=prompt_profile,
                        run_id=run_id,
                        repetition=repetition,
                    )
                    result_path = (
                        RESULTS_DIR / prompt_profile / f"{run_id}.json"
                    )
                    result = _load_json(result_path)
                    result_paths.append(result_path)

                    if result.get("final_result") == "INFRASTRUCTURE_ERROR":
                        print("\nStopping benchmark because an infrastructure error occurred.")
                        summarize(result_paths)
                        _save_json(
                            RESULTS_DIR / f"{batch}_summary.json",
                            {
                                "batch_id": batch,
                                "status": "STOPPED_INFRASTRUCTURE_ERROR",
                                "result_paths": [str(path) for path in result_paths],
                            },
                        )
                        return 1

    summarize(result_paths)
    _save_json(
        RESULTS_DIR / f"{batch}_summary.json",
        {
            "batch_id": batch,
            "status": "COMPLETE",
            "result_paths": [str(path) for path in result_paths],
        },
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the controlled multi-model Dafny benchmark."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Benchmark configuration JSON. Default: {DEFAULT_CONFIG}",
    )
    parser.add_argument(
        "--summarize-only",
        action="store_true",
        help="Summarize existing results/benchmark JSON files without new LLM runs.",
    )
    parser.add_argument(
        "--include-smoke",
        action="store_true",
        help="Include smoke-test JSON files when using --summarize-only.",
    )
    args = parser.parse_args()
    return run_benchmark(
        args.config,
        summarize_only=args.summarize_only,
        include_smoke=args.include_smoke,
    )


if __name__ == "__main__":
    raise SystemExit(main())
