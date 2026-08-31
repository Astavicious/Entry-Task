# Clean Minimal Dafny Experiment

This repository contains a small research prototype that translates an English
requirement into Dafny, runs `dafny verify`, and sends verifier feedback back to
the same model for at most two repair attempts.

The clean experiment asks one focused question:

> With the model, scenario text, attempt limit, and execution environment held
> constant, does an explicit verification-oriented prompt profile perform
> differently from a short general profile?

The architecture decision, methodological correction, and chronological change
history are recorded in
[`docs/adr/0001-verifier-guided-prompt-profile-benchmark.md`](docs/adr/0001-verifier-guided-prompt-profile-benchmark.md).

## Source Of Truth

`Task.md` is authoritative. The three files under `requirements/` are the exact
scenario inputs derived from it:

- `bounded_counter.txt`
- `authorized_access.txt`
- `account_transfer.txt`

The agent does not maintain a second hard-coded requirement rubric. Semantic
review is performed separately against `Task.md` and documented in a readable
review report.

## Pipeline

```text
requirement file
  -> select general or improved prompt instructions
  -> start a Codex thread in a fresh isolated directory
  -> save the raw response
  -> extract and save the Dafny program
  -> run dafny verify
  -> on failure, return verifier feedback for repair
  -> stop after PASS or three total attempts
  -> save a minimal JSON result
```

The modules have deliberately narrow responsibilities:

- `agent.py`: one generation-and-repair run and artifact logging.
- `llm.py`: Codex SDK invocation, isolated working directory, and source extraction.
- `verifier.py`: Dafny CLI execution and structured verifier output.
- `prompts.py`: the two generation and repair instruction profiles.
- `benchmark.py`: the controlled six-run matrix and aggregate metrics.

Every model invocation receives a fresh temporary `cwd` outside this repository.
The directory starts empty and contains no project `AGENTS.md`, requirements,
source code, or prior outputs. The Codex sandbox is read-only. This prevents the
repository's instructions and artifacts from becoming an uncontrolled source of
scenario guidance.

## Run One Scenario

Use the project virtual environment and always name the model and profile:

```powershell
.\.venv\Scripts\python.exe agent.py requirements\bounded_counter.txt --model gpt-5.4-mini --prompt-profile general
.\.venv\Scripts\python.exe agent.py requirements\bounded_counter.txt --model gpt-5.4-mini --prompt-profile improved
```

The same command shape works with the other two files in `requirements/`.
Generated responses and Dafny files are saved under `generated/<profile>/`;
minimal run records are saved under `results/benchmark/<profile>/`.

## Run The Controlled Experiment

The active configuration is the smallest meaningful A/B comparison:

```text
3 scenarios x 2 prompt profiles x 1 model x 1 repetition = 6 runs
```

All runs use `gpt-5.4-mini`, and the only intended experimental variable is the
prompt profile:

- `general`: concise instructions to produce or repair a Dafny program.
- `improved`: explicit success criteria, preservation rules, and a ban on proof
  shortcuts.

Run the configured benchmark:

```powershell
.\.venv\Scripts\python.exe benchmark.py
```

Recompute the report from saved JSON without calling the model:

```powershell
.\.venv\Scripts\python.exe benchmark.py --summarize-only
```

Run static checks and focused tests:

```powershell
.\.venv\Scripts\python.exe -m py_compile agent.py llm.py verifier.py prompts.py benchmark.py tests\test_minimal_agent.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Clean Results

Final evidence comes from batch `20260831T163605Z` only:

| Profile | Runs | Verified@1 | Verified@3 | Repair success | Total attempts |
|---|---:|---:|---:|---:|---:|
| General | 3 | 2/3 | 3/3 | 1/1 | 5 |
| Improved | 3 | 2/3 | 3/3 | 1/1 | 5 |

Per-scenario behavior:

| Profile | Scenario | Attempt 1 | Final | Attempts |
|---|---|---|---|---:|
| General | Bounded counter | PASS | VERIFIED | 1 |
| General | Authorized access | PASS | VERIFIED | 1 |
| General | Account transfer | FAIL | VERIFIED | 3 |
| Improved | Bounded counter | FAIL | VERIFIED | 3 |
| Improved | Authorized access | PASS | VERIFIED | 1 |
| Improved | Account transfer | PASS | VERIFIED | 1 |

The aggregate verifier result is a tie. The profiles failed on different tasks,
which is useful qualitative evidence, but one repetition is too small for a claim
that either prompt is generally superior.

Manual review found all six final programs represented the Task requirements under
documented reasonable interpretations. It found no `assume`, axioms, trivial
`ensures true`, proof disabling, or repair-time specification weakening. See:

- `results/benchmark/20260831T163605Z_comparison.md`
- `results/benchmark/20260831T163605Z_semantic_review.md`
- `results/benchmark/20260831T163605Z_manifest.json`

## How To Interpret PASS

```text
Dafny PASS = the implementation satisfies its Dafny specification.
Dafny PASS != the specification necessarily captures the English requirement.
```

That is why the experiment reports verifier metrics and a separate human semantic
review. Assumptions such as interpreting "increment" as adding exactly one are
recorded as interpretations rather than silently promoted to supplied requirements.

## Preserved Pilot

The previous 18-run batch remains intact under `archive/pilot-20260829/`. It is
historical pilot evidence, not the final A/B experiment, because:

1. repository `AGENTS.md` contained scenario-specific guidance that Codex could
   receive through its working-directory context; and
2. the old manual-review rubric duplicated and strengthened some requirements
   outside the text sent to the model.

Its verifier measurements remain factual for those original inputs. The clean
experiment corrects the methodology instead of rewriting or deleting that history.

## Limitations

- One model and one repetition do not support statistical generalization.
- The scenarios are small and can produce ceiling effects by attempt three.
- Human semantic review is necessary and can involve reasonable interpretation.
- Codex model base instructions and the empty global `AGENTS.md` are unavoidable
  common context, but they are shared by both profiles.
- Runtime is not treated as a robust comparative metric in a six-run experiment.

No Git remote is configured and this work is intentionally not pushed.
