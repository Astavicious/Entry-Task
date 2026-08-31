# Research Task: Build an AI Agent That Generates Verified Dafny Code

## The Goal

AI coding tools can turn natural-language requirements into code very quickly. But generated code is not necessarily correct: it may look reasonable while violating an important requirement.

**Dafny** is a programming language with built-in formal verification. A Dafny program can include specifications such as preconditions, postconditions, and invariants, and the Dafny verifier can mathematically check whether the implementation satisfies them.

Your task is to explore:

> **How well can an AI agent turn a short natural-language requirement into Dafny code that passes formal verification?**

This is an open-ended research task. We are interested in your approach, what you learn, and how you iterate—not in a perfect solution.

You should spend **up to six hours** on the task.

---

## What We Would Like You to Do

### 1. Research

Start by briefly investigating existing approaches for:

- generating code with LLMs;
- generating or repairing formally verified code;
- using compiler/verifier feedback to improve generated code.

You do not need to do an exhaustive literature review. A few useful references and observations are enough.

### 2. Build a Small Prototype

Build an AI-assisted pipeline that:

1. takes a natural-language requirement as input;
2. asks an AI model/agent to generate Dafny code;
3. runs the Dafny verifier on the generated code;
4. reports whether verification succeeded; and
5. optionally uses verifier errors to improve the code and try again.

You are free to decide how the agent works.

For example, your agent could:

- generate code once and verify it;
- generate → verify → fix → verify again;
- use multiple prompts or agents or tools or skills or workflows;
- ask a human for input;
- use an MCP server, coding-agent framework, or LLM API.

Keep the prototype small. We care more about the **research idea and evaluation** than about building a polished product. You may also use AI assistance while building your prototype.

---

## Test Cases

Run your pipeline on all three scenarios below.

You may make reasonable assumptions where the requirements are ambiguous.

### 1. Bounded Counter

Implement a counter with operations to increment and reset it.

Requirements:

- The counter must never be negative.
- The counter must never exceed a configurable maximum.
- If an increment would exceed the maximum, the counter should remain unchanged.

### 2. Authorized Access

Implement a system that grants access to a protected resource only when the requesting user is authorized.

Requirements:

- An unauthorized request must never result in an authorized access.
- Granting authorization should update the authorization state correctly.
- Revoking authorization should update the authorization state correctly.

### 3. Account Transfer

Implement a transfer operation between two accounts.

Requirements:

- The transfer amount must not be negative.
- The transfer amount must not exceed the source account's balance.
- A successful transfer must leave both accounts with non-negative balances.
- A successful transfer must preserve the combined balance of the two accounts.

Use these scenarios to test your approach and improve your agent.

---

### Optional: Codex SDK

The [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk) can be used to call Codex programmatically from your machine. This may allow you to build the prototype without managing an LLM API key yourself.

---

## What to Prepare for the Interview

Please prepare:

### 1. Short Presentation

Explain:

- what you built;
- how the pipeline works;
- your main design decisions;
- what you learned from the experiments;
- what worked and what did not.

### 2. Live Demo

Run your pipeline live on the three scenarios:

1. Bounded Counter
2. Authorized Access
3. Account Transfer

Show the generated Dafny code and whether it passes verification.

During the discussion, we may ask you to explain your choices and how you would improve the system with more time.

---

## Suggested Resources

These may help you get started:

- [Dafny](https://github.com/dafny-lang/dafny)
- [Proof-carrying code](https://en.wikipedia.org/wiki/Proof-carrying_code)
- [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk)
- [Model Context Protocol](https://learn.chatgpt.com/docs/mcp-server)
- [Building Reliable Agentic AI Systems](https://martinfowler.com/articles/reliable-llm-bayer.html)
- [Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html)

Good luck, and have fun exploring the problem!
