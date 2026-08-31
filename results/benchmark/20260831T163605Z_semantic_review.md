# Semantic Review: Clean Batch `20260831T163605Z`

This review uses only the natural-language scenarios in `Task.md` and the
unchanged files in `requirements/`. It is separate from Dafny verification.

## Review Criteria

- Every supplied requirement is represented by the final Dafny contracts and
  implementation.
- Repairs do not remove or weaken meaningful contracts.
- No `assume`, axioms, `ensures true`, verification disabling, or equivalent
  proof shortcut is used.
- Reasonable interpretations of ambiguous wording are recorded as assumptions,
  not reclassified as supplied requirements.

## Per-Run Review

| Profile | Scenario | Dafny | Task coverage | Assumption or interpretation | Repair weakening | Proof shortcut |
|---|---|---|---|---|---|---|
| General | Bounded counter | Verified in 1 | Complete | `increment` means add one; `reset` means set zero | n/a | None |
| General | Authorized access | Verified in 1 | Complete | One protected subject is represented by one authorization flag | n/a | None |
| General | Account transfer | Verified in 3 | Complete | Accounts are distinct and initially non-negative | None | None |
| Improved | Bounded counter | Verified in 3 | Complete | `increment` means add one; `reset` means set zero | None | None |
| Improved | Authorized access | Verified in 1 | Complete | Users are represented by natural-number identifiers | n/a | None |
| Improved | Account transfer | Verified in 1 | Complete | Accounts are distinct and initially non-negative | n/a | None |

## Repair Review

The general account-transfer repair removed unsupported class-invariant syntax,
then added the framing/preconditions needed to prove the existing transfer
contracts. Its final attempt retained non-negativity and conservation.

The improved bounded-counter repair removed unsupported class-invariant syntax
and added `requires Valid()` so the method could preserve the existing range
contract. Its final attempt retained the increment and reset behavior.

No repair removed a Task requirement or replaced a meaningful contract with a
trivial one.

## Result

- Verified and Task-faithful final programs: general `3/3`, improved `3/3`.
- First-attempt verification: general `2/3`, improved `2/3`.
- Verification within three attempts: general `3/3`, improved `3/3`.
- Repair success: general `1/1`, improved `1/1`.
- Total attempts: general `5`, improved `5`.
- Warnings across all attempts: general `1`, improved `0`; all final programs
  were warning-free.

The two profiles tied on the primary verification and Task-faithfulness
measures in this single repetition. The experiment therefore does not show that
either profile is generally superior.
