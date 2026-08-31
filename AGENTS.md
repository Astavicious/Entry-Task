# AI Agent for Verified Dafny Code

## Goal

Build a small prototype that converts a natural-language requirement into Dafny code and verifies it.

Pipeline:

```text
Requirement
    ↓
LLM generates Dafny
    ↓
Dafny verifier
    ↓
PASS / FAIL
    ↓
If FAIL → send verifier feedback to LLM
    ↓
Repair and verify again
```

Keep the implementation simple and easy to explain.

---

## Tech Stack

* Python
* Dafny CLI
* LLM/Codex
* `subprocess` for running Dafny
* Simple files/JSON for experiment results

Do not add unnecessary frameworks, databases, GUIs, or multi-agent systems.

---

## Step 1 — Environment

Confirm:

```bash
dafny --version
```

and verify a simple program:

```bash
dafny verify test.dfy
```

Also confirm the Python environment works.

---

## Step 2 — Project Structure

Use a minimal structure:

```text
dafny-agent/
├── agent.py
├── llm.py
├── verifier.py
├── prompts.py
├── requirements/
│   ├── bounded_counter.txt
│   ├── authorized_access.txt
│   └── account_transfer.txt
├── generated/
├── results/
└── README.md
```

Keep modules small and readable.

---

## Step 3 — Basic Generation

Implement:

```text
requirement
→ LLM
→ Dafny source code
→ save as .dfy
```

The prompt should tell the LLM to:

* translate the requirement into Dafny specifications;
* use `requires`, `ensures`, `old`, invariants, etc. when appropriate;
* implement the required behavior;
* generate code intended to pass `dafny verify`;
* return only Dafny source code;
* not weaken specifications just to make verification easier.

---

## Step 4 — Dafny Verification

Create a verifier wrapper using:

```python
subprocess.run(...)
```

Run:

```bash
dafny verify generated_file.dfy
```

Capture:

* return code;
* stdout;
* stderr;
* PASS / FAIL.

Return a simple structured result.

---

## Step 5 — Repair Loop

If verification fails:

```text
Original requirement
+
Previous Dafny code
+
Dafny verifier error
        ↓
       LLM
        ↓
Corrected Dafny
        ↓
Verify again
```

Use:

```python
MAX_ATTEMPTS = 3
```

Save every generated attempt.

Never silently modify LLM output.

The repair prompt must explicitly say:

> Preserve all original requirements. Do not remove, weaken, or replace meaningful specifications merely to make verification pass.

---

## Step 6 — Required Test Cases

### Bounded Counter

Properties:

```text
0 <= counter <= maximum
```

Increment:

```text
if old(counter) < maximum:
    counter = old(counter) + 1
else:
    counter = old(counter)
```

Reset:

```text
counter = 0
```

---

### Authorized Access

Required properties:

```text
access granted → user is authorized
```

Grant:

```text
user becomes authorized
```

Revoke:

```text
user becomes unauthorized
```

A set of authorized users is a reasonable implementation.

---

### Account Transfer

Required conditions:

```text
amount >= 0
amount <= source balance
```

After successful transfer:

```text
source >= 0
destination >= 0
```

State changes:

```text
newSource = oldSource - amount
newDestination = oldDestination + amount
```

Conservation property:

```text
newSource + newDestination
=
oldSource + oldDestination
```

---

## Step 7 — Experiment Logging

For each scenario record:

```text
Scenario
Attempt number
Generated code
Verification PASS/FAIL
Verifier output
Final result
Number of attempts
```

Create a final table like:

| Scenario          | First Attempt | Final Result | Attempts |
| ----------------- | ------------- | ------------ | -------: |
| Bounded Counter   | ?             | ?            |        ? |
| Authorized Access | ?             | ?            |        ? |
| Account Transfer  | ?             | ?            |        ? |

Do not invent results. Populate them from actual runs.

---

## Step 8 — Manual Specification Check

A Dafny verification PASS is not enough.

For every final program manually check:

* Is every English requirement represented?
* Did the model omit a requirement?
* Did repair weaken a specification?
* Did the model replace meaningful conditions with trivial ones?
* Does the specification still match the original requirement?

Important distinction:

```text
Dafny PASS
=
implementation satisfies specification

Dafny PASS
≠
specification necessarily matches the original English perfectly
```

Record any such problems in the experiment notes.

---

## Step 9 — Research Notes

Briefly investigate:

* LLM code generation;
* LLM generation of formally verified code;
* verifier/compiler-feedback repair;
* Dafny and SMT-based verification.

Keep this short. The implementation and experiments are the priority.

Record only useful references and observations for the presentation.

---

## Step 10 — Final Demo

The CLI should be simple.

Example:

```bash
python agent.py requirements/bounded_counter.txt
```

Desired output:

```text
=== Attempt 1 ===
Generating Dafny...

Running Dafny verifier...

FAIL

Verifier feedback:
...

=== Attempt 2 ===
Generating repair...

Running Dafny verifier...

PASS

Final result: VERIFIED
Attempts: 2
```

The same command structure should work for all three scenarios.

---

## Definition of Done

* [ ] Dafny works locally
* [ ] Python can call the LLM
* [ ] LLM generates Dafny code
* [ ] Generated code is saved
* [ ] Python runs `dafny verify`
* [ ] PASS/FAIL is detected
* [ ] Verifier errors are captured
* [ ] Errors can be returned to the LLM
* [ ] Maximum three attempts
* [ ] Every attempt is saved
* [ ] All three required scenarios are tested
* [ ] Results are recorded
* [ ] Final specifications are manually checked
* [ ] Demo works from the command line
* [ ] README explains architecture and results

---

## Implementation Rules for Codex

1. Keep the code minimal.
2. Prefer plain Python.
3. Do not introduce frameworks unless required.
4. Keep LLM logic separate from verifier logic.
5. Make all important behavior easy to read.
6. Preserve generated attempts and verifier output.
7. Do not hide errors.
8. Do not automatically weaken Dafny specifications.
9. Use a maximum of three verification attempts.
10. Optimize for a research prototype that can be explained line-by-line in an interview.
