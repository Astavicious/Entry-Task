# Dafny Generation Benchmark Prototype

This project is a small research prototype for testing whether a Codex model can turn
short English requirements into Dafny programs that pass formal verification.

The main architecture decision, exact failure analysis, experiment rationale,
and recent change history are recorded in
[`docs/adr/0001-verifier-guided-prompt-profile-benchmark.md`](docs/adr/0001-verifier-guided-prompt-profile-benchmark.md).

The pipeline is intentionally simple:

```text
English requirement
  -> Codex model generates Dafny
  -> generated text is saved exactly
  -> Dafny source is extracted
  -> dafny verify runs with --allow-warnings
  -> if verification fails, verifier output is sent back for repair
  -> stop after at most three attempts
```

The goal is not to prove that the model fully understands the English requirement.
Dafny proves that the implementation satisfies the Dafny specification. A separate
manual review checks whether the specification still matches the English.

## Files

- `agent.py` runs one scenario with one explicitly requested model.
- `llm.py` starts a fresh read-only Codex thread and extracts Dafny source.
- `verifier.py` wraps the Dafny CLI and captures stdout, stderr, return code, and warnings.
- `prompts.py` contains the unchanged generation and repair prompts.
- `benchmark.py` runs the controlled multi-model benchmark and prints summary tables.
- `benchmark_config.json` lists the models, scenarios, and repetition count.
- `requirements/` contains the three English scenarios.
- `generated/` stores raw model responses and extracted `.dfy` files.
- `results/benchmark/` stores benchmark JSON files.
- `results/*.json` and old files in `generated/` are historical GPT-5.5 pilot results.

## Model Choice

The default benchmark uses the simplest available Codex model set for this project:

```json
[
  "gpt-5.4-mini",
  "gpt-5.6-luna",
  "gpt-5.4"
]
```

This keeps the comparison lightweight. The point is to see whether smaller or cheaper
models can solve these Dafny tasks before spending runs on larger models.

Do not invent model names. If a configured model is unavailable, the benchmark records
an infrastructure error and stops rather than treating it as a Dafny generation failure.

## Run One Scenario

Use the repository virtual environment:

```powershell
.\.venv\Scripts\python.exe agent.py requirements\bounded_counter.txt --model gpt-5.4-mini --run-id demo_bounded_counter
```

The same command shape works for the other scenarios:

```powershell
.\.venv\Scripts\python.exe agent.py requirements\authorized_access.txt --model gpt-5.4-mini --run-id demo_authorized_access
.\.venv\Scripts\python.exe agent.py requirements\account_transfer.txt --model gpt-5.4-mini --run-id demo_account_transfer
```

Each run writes:

```text
generated/<run-id>/<scenario>_attempt_<n>.raw.txt
generated/<run-id>/<scenario>_attempt_<n>.dfy
results/benchmark/<run-id>.json
```

## Run The Benchmark

The default config runs:

```text
3 models x 3 scenarios x 1 repetition = 9 runs
```

Run it with:

```powershell
.\.venv\Scripts\python.exe benchmark.py
```

The benchmark now compares two prompt profiles over the same models and
requirements:

- `general` uses short, general generation and repair instructions.
- `improved` uses explicit success criteria, specification-preservation rules,
  and bans proof shortcuts.

Their outputs are kept separate in `generated/general`, `generated/improved`,
`results/benchmark/general`, and `results/benchmark/improved`.

To run one requirement with one profile:

```powershell
.\.venv\Scripts\python.exe agent.py requirements\bounded_counter.txt --model gpt-5.4-mini --prompt-profile general
.\.venv\Scripts\python.exe agent.py requirements\bounded_counter.txt --model gpt-5.4-mini --prompt-profile improved
```

To change models or repetitions, edit `benchmark_config.json`. Keep `repetitions` at
`1` unless you intentionally want more runs.

To print tables from existing JSON files without calling models again:

```powershell
.\.venv\Scripts\python.exe benchmark.py --summarize-only
```

Smoke-test JSON files are excluded from normal summaries. To include them:

```powershell
.\.venv\Scripts\python.exe benchmark.py --summarize-only --include-smoke
```

## Benchmark Results

Batch `20260829T175916Z` ran the default configuration:

```text
3 models x 3 scenarios x 1 repetition = 9 runs
```

Per-run verification results:

| Model | Scenario | Attempt 1 | Final | Attempts | Faithful | Coverage | Warnings | Time |
|------|----------|-----------|-------|---------:|----------|----------|---------:|-----:|
| gpt-5.4 | Account Transfer | PASS | VERIFIED | 1 | PENDING | PENDING | 2 | 18.21 |
| gpt-5.4 | Authorized Access | PASS | VERIFIED | 1 | PENDING | PENDING | 0 | 26.57 |
| gpt-5.4 | Bounded Counter | PASS | VERIFIED | 1 | PENDING | PENDING | 2 | 18.02 |
| gpt-5.4-mini | Account Transfer | PASS | VERIFIED | 1 | PENDING | PENDING | 0 | 94.83 |
| gpt-5.4-mini | Authorized Access | FAIL | VERIFIED | 2 | PENDING | PENDING | 0 | 33.42 |
| gpt-5.4-mini | Bounded Counter | FAIL | VERIFIED | 2 | PENDING | PENDING | 0 | 125.28 |
| gpt-5.6-luna | Account Transfer | FAIL | VERIFIED | 2 | PENDING | PENDING | 0 | 80.32 |
| gpt-5.6-luna | Authorized Access | PASS | VERIFIED | 1 | PENDING | PENDING | 0 | 22.94 |
| gpt-5.6-luna | Bounded Counter | FAIL | VERIFIED | 2 | PENDING | PENDING | 0 | 26.55 |

Per-model verification results:

| Model | Runs | Verified@1 | Verified@3 | Faithful@1 | Faithful@3 | Repair Success | Median Attempts | Mean Coverage |
|------|-----:|-----------:|-----------:|------------|------------|---------------:|----------------:|---------------|
| gpt-5.4 | 3 | 3/3 | 3/3 | n/a | n/a | n/a | 1 | PENDING |
| gpt-5.4-mini | 3 | 1/3 | 3/3 | n/a | n/a | 2/2 | 2 | PENDING |
| gpt-5.6-luna | 3 | 1/3 | 3/3 | n/a | n/a | 2/2 | 2 | PENDING |

Interpretation before manual review:

- All three models reached Dafny verification within three attempts.
- `gpt-5.4` had the best first-attempt verification rate in this run.
- `gpt-5.4-mini` and `gpt-5.6-luna` both benefited from verifier-feedback repair.
- The scenarios are still fairly small; if manual review finds all requirements covered,
  the final result shows a ceiling effect for final verification.
- Faithfulness and coverage are pending until a human checks the generated specifications.

## Manual Review

A Dafny PASS is not enough. After each run, open the JSON file in
`results/benchmark/` and fill the `manual_review` section.

Use this scale:

```text
COVERED = 2
WEAKENED = 1
MISSING = 0
```

For each English requirement, ask:

- Is this requirement represented in the Dafny specification?
- Was it weakened during repair?
- Did the model add an unjustified `requires` clause?
- Did the model add an assumption not present in the English?
- Did it use a trivial or vacuous specification?
- Did it use suspicious `assume` statements?

Then set:

```json
"status": "COMPLETE"
```

and fill:

```json
"normalized_coverage": 1.0
```

only when every meaningful requirement is fully covered.

## Scenario Explanation

### Bounded Counter

What the English asks for:

- The counter is always at least zero.
- The counter is always at most the configured maximum.
- Increment either adds one or leaves the counter unchanged when already at the maximum.
- Reset sets the counter back to zero.

What to look for in Dafny:

- A state invariant such as `0 <= counter <= maximum`.
- A constructor that requires the maximum to be non-negative.
- `Increment` postconditions using `old(counter)` and `old(maximum)`.
- `Reset` postconditions proving `counter == 0`.

### Authorized Access

What the English asks for:

- A request from an unauthorized user must not grant access.
- Granting authorization updates the authorization state.
- Revoking authorization updates the authorization state.

What to look for in Dafny:

- A set of authorized users is a reasonable implementation.
- `RequestAccess` should connect `granted` to membership in that set.
- `GrantAuthorization` should ensure the user is in the set afterward.
- `RevokeAuthorization` should ensure the user is not in the set afterward.

### Account Transfer

What the English asks for:

- The amount is non-negative.
- The amount does not exceed the source balance.
- Both balances are non-negative after the transfer.
- The combined balance is preserved.

What to look for in Dafny:

- Preconditions like `amount >= 0` and `amount <= source.balance`.
- Postconditions for both new balances.
- A conservation postcondition:

```dafny
ensures source.balance + destination.balance ==
        old(source.balance) + old(destination.balance)
```

## Warning Workaround

The historical GPT-5.5 pilot produced two warnings for account transfer because it used:

```dafny
requires source != null
requires destination != null
```

In modern Dafny, parameters declared as `Account` are already non-null. So those checks
are redundant. The clean version is to remove those two preconditions and keep:

```dafny
requires source != destination
```

This does not weaken the English requirement because the English did not say the transfer
must accept nullable accounts.

Do not edit generated model outputs during the benchmark. Record warnings as part of the
result. Explain them during the presentation as successful verification with redundant
null checks.

## How To Explain The Task

In the interview, explain it in this order:

1. The problem is that generated code can look correct but miss requirements.
2. Dafny lets us write executable code plus formal specifications.
3. The prototype asks a model for Dafny, verifies it, and feeds verifier errors back once
   or twice if needed.
4. The benchmark isolates every model/scenario run so artifacts cannot overwrite each other.
5. The measured result is not only `PASS` or `FAIL`; manual requirement coverage matters too.
6. If all simple scenarios pass on the first attempt, that is still useful because it shows a
   ceiling effect: the tasks are too easy to separate model quality.
