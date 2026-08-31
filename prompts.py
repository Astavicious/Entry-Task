"""General and improved prompts for Dafny generation and repair."""

GENERAL_GENERATION_INSTRUCTIONS = """
Generate a complete Dafny program from the natural-language requirement.
Implement the requested behavior and make the program intended to pass
`dafny verify`.

Return only the complete Dafny source code in one fenced `dafny` block.
""".strip()

GENERAL_REPAIR_INSTRUCTIONS = """
Repair the Dafny program using the verifier feedback so that it passes
`dafny verify`.

Return only the complete corrected Dafny source code in one fenced `dafny`
block.
""".strip()

IMPROVED_GENERATION_INSTRUCTIONS = """
Generate a complete Dafny program from the natural-language requirement.

Success means:

- the program is intended to pass `dafny verify`;
- every meaningful English requirement is represented by an explicit
  Dafny specification where appropriate;
- the implementation satisfies those specifications.

Use requires, ensures, invariants, old(...), predicates, and other Dafny
features when appropriate.

Do not omit or weaken requirements to obtain verification.
Do not use assume, axioms, trivial specifications such as `ensures true`,
or other shortcuts that bypass the intended proof.

If the requirement is ambiguous, make the smallest reasonable assumption
while preserving its intent.

Return only the complete Dafny source code in one fenced `dafny` block.
""".strip()

IMPROVED_REPAIR_INSTRUCTIONS = """
Repair the Dafny program using the verifier feedback.

Success means:

- the corrected program passes `dafny verify`;
- all original natural-language requirements remain represented;
- existing meaningful specifications are preserved or strengthened.

Fix the implementation or proof annotations needed to resolve the verifier
failure.

Do not remove or weaken requirements.
Do not use assume, axioms, `ensures true`, or other proof shortcuts.

Return only the complete corrected Dafny source code in one fenced `dafny`
block.
""".strip()

PROMPT_PROFILES = {
    "general": (
        GENERAL_GENERATION_INSTRUCTIONS,
        GENERAL_REPAIR_INSTRUCTIONS,
    ),
    "improved": (
        IMPROVED_GENERATION_INSTRUCTIONS,
        IMPROVED_REPAIR_INSTRUCTIONS,
    ),
}


def generation_prompt(requirement: str, profile: str = "general") -> str:
    """Build the initial generation prompt from an English requirement."""
    generation_instructions, _ = PROMPT_PROFILES[profile]
    return (
        f"{generation_instructions}\n\n"
        f"Natural-language requirement:\n{requirement}"
    )


def repair_prompt(
    requirement: str,
    previous_source: str,
    verifier_feedback: str,
    profile: str = "general",
) -> str:
    """Build a repair prompt containing the complete previous context."""
    _, repair_instructions = PROMPT_PROFILES[profile]
    return (
        f"{repair_instructions}\n\n"
        f"Original natural-language requirement:\n{requirement}\n\n"
        f"Previous Dafny source:\n{previous_source}\n\n"
        f"Dafny verifier feedback:\n{verifier_feedback}"
    )
