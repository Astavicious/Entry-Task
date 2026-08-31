# Project Instructions

This repository contains a small research prototype for generating and
verifying Dafny code.

Keep the implementation simple and readable. Use plain Python, the Codex SDK,
the Dafny CLI, and `subprocess`. Do not add frameworks, databases, GUIs, or
unrelated functionality.

The files in `requirements/` are the sole source of scenario requirements. Do
not add scenario-specific behavior, formal interpretations, or solution hints
to this file.

Preserve every raw model response, extracted Dafny program, and verifier output.
Do not edit generated model output before verification. Allow at most three
generation and repair attempts per run.
