# ADR 0001: Use Verifier-Guided Repair and Controlled Prompt Profiles

- Status: Accepted; amended 2026-08-31
- Date: 2026-08-29
- Scope: Dafny generation research prototype
- Decision owners: Project team

## Context

The prototype translates a natural-language requirement into Dafny, runs the
Dafny verifier, and optionally sends verifier feedback to the model for repair.
The research question is not only whether generated code compiles or verifies,
but whether its formal specification still represents the English requirement.

The project now has two instruction styles:

1. `general`: short instructions that request a complete Dafny program or
   repair intended to pass `dafny verify`.
2. `improved`: explicit success criteria requiring meaningful specifications,
   preservation of the English requirements, and no proof shortcuts such as
   `assume`, axioms, or `ensures true`.

The two styles must be evaluated under the same models, scenarios, verifier,
attempt limit, and logging behavior. Generated attempts must remain unchanged so
that failures and repairs can be inspected later.

## Decision

We will use one simple verifier-guided pipeline with the following rules:

1. Keep `general` and `improved` as explicit selectable prompt profiles.
2. Run both profiles against the same three requirements and configured models.
3. Give each run at most three model/verifier attempts.
4. On failure, send the original requirement, previous source, and complete
   verifier feedback to the same model.
5. Save every raw response and every extracted `.dfy` attempt without silently
   editing model output.
6. Store general and improved artifacts in separate directories.
7. Treat verifier warnings separately from verifier errors. Warnings are
   permitted during verification but are captured and reported.
8. Distinguish an LLM/SDK infrastructure error from a model-generated Dafny
   verification failure.
9. Perform a manual semantic review because Dafny proves implementation versus
   specification, not English requirement versus specification.
10. Report both verification efficiency and semantic specification quality.

## Why Programs Failed

The failures were caused by generated Dafny syntax or framing errors, not by the
English scenarios being impossible to verify.

### Current A/B Batch `20260829T184639Z`

| Profile | Model | Scenario | Failed attempt | Exact cause | Outcome |
| --- | --- | --- | ---: | --- | --- |
| General | `gpt-5.4-mini` | Bounded counter | 1 | Generated `invariant` directly in a class body. Dafny 4.11 expected the class to end there and reported `rbrace expected`. | Attempt 2 replaced it with a `Valid()` predicate and verified. |
| General | `gpt-5.6-luna` | Bounded counter | 1 | Used the same unsupported class-level `invariant` form. | Attempt 2 moved the invariant into method contracts and verified. |
| General | `gpt-5.6-luna` | Authorized access | 1 | Omitted statement terminators, producing several `invalid AssignStatement` parse errors. | Attempt 2 added terminators and verified. |
| Improved | `gpt-5.4-mini` | Bounded counter | 1 | Used an unsupported class-level `invariant`. | Failed. |
| Improved | `gpt-5.4-mini` | Bounded counter | 2 | Kept the unsupported invariant and added unnecessary field semicolons. | Attempt 3 used a `Valid()` predicate and verified. |
| Improved | `gpt-5.6-luna` | Bounded counter | 1 | Methods modified `counter` without `modifies this`. Dafny rejected the heap update. | Attempt 2 added the frame clauses and verified. |
| Improved | `gpt-5.6-luna` | Authorized access | 1 | Omitted statement terminators, causing four parse errors. | Failed. |
| Improved | `gpt-5.6-luna` | Authorized access | 2 | Tried to repair the empty set as `set {}`, which is not Dafny syntax. | Failed. |
| Improved | `gpt-5.6-luna` | Authorized access | 3 | Changed the empty set to `set<string>{}`, which is also not Dafny syntax. The correct expression is `{}` when its type is known from context. | Unverified after the three-attempt limit. |

The final unresolved failure is therefore a repair-loop failure. The verifier
gave syntax feedback, but the model made nearby guesses instead of returning to
the known Dafny empty-set literal `{}`.

### Earlier Benchmark Batch `20260829T175916Z`

| Model | Scenario | Failed attempt | Exact cause | Outcome |
| --- | --- | ---: | --- | --- |
| `gpt-5.4-mini` | Authorized access | 1 | Put a `reads this` clause on a method. Dafny forbids method reads clauses unless the optional `--reads-clauses-on-methods` flag is enabled. | Repair removed/restructured the clause and verified. |
| `gpt-5.4-mini` | Bounded counter | 1 | Used unsupported class-level `invariant` syntax. | Repair verified. |
| `gpt-5.6-luna` | Account transfer | 1 | Omitted assignment terminators, producing `invalid AssignStatement` parse errors. | Repair verified. |
| `gpt-5.6-luna` | Bounded counter | 1 | Modified fields without a `modifies` clause. | Repair added framing and verified. |

These repeated causes show that the repair loop is useful, but also that a small
Dafny-specific syntax reference or deterministic lint step could reduce wasted
model calls.

## Why Some Verified Results Still Need Review

A `PASS` means Dafny proved that the implementation satisfies the written Dafny
contracts. It does not mean those contracts fully express the English request.

One observed example is the general `gpt-5.6-luna` account transfer. Its code
subtracts the amount from the source and adds it to the destination, and Dafny
proves non-negativity and conservation. However, its postconditions omit the two
exact state-change formulas:

```dafny
ensures source.balance == old(source.balance) - amount
ensures destination.balance == old(destination.balance) + amount
```

The improved transfer includes those contracts. This is evidence that the
improved prompt can produce stronger specification coverage even when raw
verification rates do not improve.

## Warning Policy and Workarounds

Warnings do not fail a run. They are captured because they still reveal quality
issues.

Observed warnings and their safe cleanups:

- `source != null` or `destination != null` is redundant when the variable type
  is non-nullable `Account`. Remove the condition. Use `Account?` only when null
  is intentionally part of the design.
- A semicolon after a Dafny field declaration is deprecated style. Remove it.
- `old(...)` around an expression that does not dereference mutable heap state
  has no effect. Remove the unnecessary `old` while retaining it around mutable
  fields where pre-state comparison is required.

Generated benchmark artifacts remain unchanged. A warning-clean demo copy may
be created separately so the recorded model output is never rewritten.

## A/B Experiment Result

| Metric | General | Improved |
| --- | ---: | ---: |
| Runs | 9 | 9 |
| Verified on attempt 1 | 6/9 | 6/9 |
| Verified within 3 attempts | 9/9 | 8/9 |
| Repair successes/opportunities | 3/3 | 2/3 |
| Total attempts | 12 | 14 |
| Mean attempts | 1.33 | 1.56 |
| Warnings across all attempts | 1 | 3 |
| Total elapsed time | 289.50 s | 448.26 s |
| Mean elapsed time | 32.17 s | 49.81 s |

Decision interpretation:

- Keep the general prompt as the default because it was simpler, faster, and
  fully reliable in this one-repetition batch.
- Keep the improved prompt as an experimental profile because it better states
  semantic contracts and bans proof shortcuts.
- Do not claim that one prompt is universally better from nine runs per profile.
  More repetitions are required for a stable comparison.

## Changes Made During the Recent Work

### Environment and Verification

- Confirmed the project-local Python environment works with Python 3.12.13.
- Confirmed bundled Dafny 4.11.0 works even though `dafny` is not on the system
  `PATH`.
- Added a verifier executable lookup using `DAFNY_BIN`, then the bundled
  `.tools` executable, then the system command.
- Added Dafny version capture for reproducibility.
- Kept verification in `subprocess.run` with captured stdout, stderr, return
  code, timeout, and explicit error records.
- Added `--allow-warnings` so benign warnings do not become false failures.
- Added warning extraction and per-attempt warning counts.

### LLM Integration

- Kept LLM code isolated in `llm.py`.
- Added explicit model selection for every Codex SDK thread.
- Used the SDK read-only sandbox for generation calls.
- Added Windows home-directory environment forwarding required by the SDK.
- Added structured response metadata for duration, usage, and model information
  when exposed by the SDK.
- Preserved deterministic extraction of exactly one fenced `dafny` block and
  preserved the raw response when extraction is ambiguous.

### Agent and Repair Loop

- Kept `MAX_ATTEMPTS = 3`.
- Saved both raw responses and extracted Dafny files for every attempt.
- Added unique run IDs and isolated run directories to prevent overwrites.
- Added explicit model and prompt-profile CLI options.
- Added timing, environment, usage, verifier output, warning, and final-status
  fields to result JSON.
- Classified SDK/process failures as `INFRASTRUCTURE_ERROR` rather than model
  verification failures.
- Added manual-review templates with requirement-level scoring and checks for
  omitted requirements, weakening, assumptions, trivial contracts, and `assume`.
- Expanded the review checklist to include exact increment/reset and transfer
  state-change requirements from `AGENTS.md`.

### Prompt Design

- Replaced the single prompt pair with `general` and `improved` profiles.
- Made `general` the default profile.
- Added the supplied improved generation criteria.
- Added the supplied improved repair criteria.
- Ensured repair prompts include the original requirement, previous source, and
  complete verifier feedback.

### Benchmarking and Results

- Added `benchmark_config.json` with three models, three scenarios, two prompt
  profiles, and one repetition.
- Added a benchmark runner for controlled model/scenario/profile execution.
- Added per-run and per-model summary tables based only on saved JSON results.
- Added verification-attempt, repair-success, warning, timing, and manual-review
  metrics.
- Filtered `--summarize-only` to actual profile run JSON files so reports and old
  unprofiled experiments are not misread as current runs.
- Ran an initial 9-run multi-model benchmark.
- Ran a 9-run general versus 9-run improved A/B benchmark.
- Saved general and improved artifacts in separate generated/result directories.
- Added machine-readable and Markdown comparison reports.
- Preserved smoke tests, earlier results, failed attempts, and archived
  infrastructure/warning experiments rather than deleting evidence.

### Documentation and Validation

- Expanded `README.md` with architecture, setup, commands, model selection,
  experiment results, warning explanations, manual review guidance, and an
  interview-friendly explanation of the pipeline.
- Added commands for selecting `general` or `improved` on a single scenario.
- Validated Python files with `py_compile` after changes.
- Re-ran summary generation and checked aggregate values directly against all 18
  A/B result files.
- Added this ADR to preserve the design rationale, failure analysis, trade-offs,
  and recent change history.

## Alternatives Considered

### Use only the improved prompt

Rejected for now. It produced stronger contracts but was slower and had one
unrepaired syntax failure in the observed batch.

### Use only the general prompt

Rejected as the sole research condition. It verified reliably, but one transfer
result omitted meaningful postconditions, so it does not test whether explicit
prompt constraints improve specification quality.

### Automatically edit known Dafny mistakes

Rejected for benchmark outputs. Automatic edits would hide what the model
actually generated and make repair-success measurements unreliable. A future
preflight diagnostic may identify common mistakes, but any correction must be
recorded as a separate transformation or attempt.

### Add more agents or frameworks

Rejected because the task calls for a small, explainable prototype. One model,
one verifier wrapper, and one bounded repair loop are sufficient for the current
research question.

## Consequences

Positive consequences:

- Runs are reproducible and directly comparable.
- Failed output remains available for analysis.
- Verification failures, warnings, infrastructure failures, and semantic-review
  failures are distinct concepts.
- The prototype remains plain Python and can be explained line by line.

Negative consequences:

- Two prompt profiles and detailed logging add a small amount of code.
- Manual semantic review is still required.
- One repetition is too small for statistical conclusions.
- The repair loop can repeat incorrect syntax because it has no deterministic
  Dafny grammar checker beyond the verifier itself.

## Follow-Up Decisions

Future work should consider:

1. Run at least five repetitions per model/profile/scenario.
2. Add a recorded, non-mutating preflight diagnostic for known mistakes such as
   class-level invariants, missing `modifies`, and malformed empty sets.
3. Add a compact Dafny syntax reference to repair prompts only, then evaluate it
   as a third controlled prompt profile.
4. Complete requirement-level manual review fields for each result before using
   `Faithful@1`, `Faithful@3`, or coverage metrics in a presentation.
5. Keep warning-clean demo files separate from immutable benchmark artifacts.

## Amendment: Clean Minimal Experiment (2026-08-31)

### Discovery

The original A/B batch had two methodological limitations discovered during
final review.

First, `llm.py` started Codex threads without an explicit working directory.
The SDK inherited the repository working directory, and Codex incorporates
applicable `AGENTS.md` files into its model context. The repository `AGENTS.md`
contained scenario-specific interpretations and specification guidance.
Consequently, both the general and improved conditions could receive guidance
outside their explicit prompts. This confounded the intended prompt-profile
comparison.

Second, the then-current `agent.py` contained a separate
`SCENARIO_REQUIREMENTS` dictionary for manual review. It expanded the Task
wording with exact increment, reset, and balance-update interpretations. The
saved A/B result JSON still contained the original Task-aligned checklists, but
the later aggregate inspection applied the stronger rubric. In particular, the
claim that one general transfer omitted supplied exact balance-update
postconditions was too strong: those formulas were a reasonable interpretation
of transfer, not explicit Task bullets.

### Impact on Pilot Batch `20260829T184639Z`

The raw responses, Dafny programs, verifier outcomes, warning counts, attempts,
and runtimes remain factual for that pilot. They are preserved unchanged under
`archive/pilot-20260829/` and in the baseline Git commit.

The pilot is no longer treated as clean causal evidence about general versus
improved prompting. Its semantic transfer observation is retained only as a
strict-rubric observation, not as proof that the model ignored an explicit Task
requirement.

### Corrective Decision

1. `Task.md` and the unchanged `requirements/*.txt` files define the scenario
   inputs.
2. `AGENTS.md` contains only neutral repository engineering instructions.
3. `agent.py` performs generation, verification, repair, and minimal logging;
   it does not define requirements or perform semantic scoring.
4. Manual semantic review is a separate artifact based on the exact Task text.
5. Every Codex thread receives a fresh temporary `cwd` outside the repository,
   preventing project `AGENTS.md` from entering either condition.
6. Both `CodexConfig` and the Codex thread receive the same isolated temporary
   `cwd`. The thread remains read-only.
7. The clean experiment uses one model, three scenarios, two profiles, one
   repetition, and at most three attempts: six runs total.

### Minimal-Agent Changes

- Removed hard-coded scenario requirements and manual-review JSON templates.
- Removed per-run Python/SDK environment metadata and empty model type, tier,
  parameter, credits, and cost fields.
- Stopped duplicating full raw responses and Dafny sources inside result JSON;
  immutable artifact paths remain recorded.
- Kept PASS/FAIL, verifier output, warnings, attempt count, model, profile, and
  artifact paths.
- Added focused tests proving isolated thread `cwd`, profile requirement parity,
  minimal result shape, and artifact preservation.
- Added one batch manifest containing requirement hashes, exact prompt-profile
  instructions and hashes, Dafny version, and isolation evidence.

Two sandboxed preflight runs stopped before model inference because the Codex
runtime could not access the Windows home directory. Their error manifests are
preserved under `archive/isolation-home-preflight-20260831*`. The official run
used the user's authenticated outer environment while each Codex thread used
`Sandbox.read_only` and an isolated temporary directory. A later no-inference
startup probe confirmed that, outside the tool sandbox, the same isolated
directory can also be used as `CodexConfig.cwd`; the final implementation now
passes it to both SDK configuration and thread startup.

### Clean Batch `20260831T163605Z`

| Profile | Runs | Verified@1 | Verified@3 | Repair success | Total attempts | Warnings |
|---|---:|---:|---:|---:|---:|---:|
| General | 3 | 2/3 | 3/3 | 1/1 | 5 | 1 |
| Improved | 3 | 2/3 | 3/3 | 1/1 | 5 | 0 |

General bounded counter and authorized access verified on attempt 1. General
account transfer verified on attempt 3 after removing unsupported class-level
invariant syntax and adding the conditions needed to prove its contracts.

Improved authorized access and account transfer verified on attempt 1.
Improved bounded counter verified on attempt 3 after removing unsupported
class-level invariant syntax and adding `requires Valid()`.

All six final programs were warning-free. Manual review against the exact Task
text found all six final programs complete under explicitly recorded reasonable
assumptions. No proof shortcuts or repair weakening were found.

### Revised Interpretation

In this one-model, one-repetition clean batch, the profiles tied on
first-attempt verification, final verification, repair success, total attempts,
and Task faithfulness. The improved profile had no warnings across attempts,
while general had one warning in a failed intermediate attempt.

This is a small exploratory result. It supports the usefulness of
verifier-guided repair, but it does not establish that either prompt profile is
generally superior.

### Decision History

| Date | Change | Reason |
|---|---|---|
| 2026-08-29 | Added verifier-guided repair with maximum three attempts | Test whether Dafny feedback helps correct generated programs |
| 2026-08-29 | Added general and improved prompt profiles | Compare minimal instructions with explicit specification-preservation guidance |
| 2026-08-29 | Ran the 18-run pilot batch | Explore three models across both profiles and all scenarios |
| 2026-08-31 | Identified project-instruction leakage | `AGENTS.md` was part of the effective Codex context |
| 2026-08-31 | Identified duplicated/expanded manual-review rubric | `agent.py` could grade requirements not explicitly supplied in the Task |
| 2026-08-31 | Archived the pilot and simplified the agent | Preserve evidence while restoring a small, explainable prototype |
| 2026-08-31 | Isolated thread working directories and ran six clean cases | Make prompt profile the only intended experimental variable |
