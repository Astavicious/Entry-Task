from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agent
import llm
from prompts import generation_prompt
from verifier import VerificationResult


class MinimalAgentTests(unittest.TestCase):
    def test_isolated_cwd_is_empty_and_outside_project(self) -> None:
        with llm.isolated_codex_cwd() as cwd:
            self.assertNotEqual(cwd, llm.PROJECT_ROOT)
            self.assertNotIn(llm.PROJECT_ROOT, cwd.parents)
            self.assertFalse((cwd / "AGENTS.md").exists())
            self.assertEqual(list(cwd.iterdir()), [])

    def test_codex_receives_the_same_isolated_cwd(self) -> None:
        captured = {}

        class FakeResult:
            final_response = "response"

        class FakeThread:
            def run(self, prompt: str) -> FakeResult:
                captured["prompt"] = prompt
                return FakeResult()

        class FakeCodex:
            def __init__(self, config) -> None:
                captured["config_cwd"] = config.cwd

            def __enter__(self):
                return self

            def __exit__(self, *args) -> None:
                return None

            def thread_start(self, **kwargs) -> FakeThread:
                captured["thread_cwd"] = kwargs["cwd"]
                path = Path(kwargs["cwd"])
                self_outer.assertFalse((path / "AGENTS.md").exists())
                self_outer.assertNotIn(llm.PROJECT_ROOT, path.parents)
                return FakeThread()

        self_outer = self
        with patch("llm.Codex", FakeCodex):
            self.assertEqual(llm.generate_response("hello", "test-model"), "response")
        self.assertEqual(captured["config_cwd"], captured["thread_cwd"])
        self.assertEqual(captured["prompt"], "hello")

    def test_profiles_share_identical_requirement_text(self) -> None:
        requirement = "Requirement text\n"
        general = generation_prompt(requirement, "general")
        improved = generation_prompt(requirement, "improved")
        suffix = f"Natural-language requirement:\n{requirement}"
        self.assertTrue(general.endswith(suffix))
        self.assertTrue(improved.endswith(suffix))
        self.assertNotEqual(general, improved)

    def test_agent_saves_minimal_result_and_artifacts(self) -> None:
        passed = VerificationResult(True, 0, "verified", "", warnings=[])
        response = "```dafny\nmethod Main() {}\n```\n"
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            os.chdir(directory)
            try:
                requirement = Path("case.txt")
                requirement.write_text("Do the task.\n", encoding="utf-8")
                with patch("agent.generate_response", return_value=response), patch(
                    "agent.verify_file", return_value=passed
                ):
                    self.assertTrue(
                        agent.run_agent(
                            requirement,
                            model="test-model",
                            prompt_profile="general",
                            run_id="test-run",
                        )
                    )

                result_path = Path("results/benchmark/general/test-run.json")
                result = json.loads(result_path.read_text(encoding="utf-8"))
                self.assertEqual(result["final_result"], "VERIFIED")
                self.assertEqual(result["attempt_count"], 1)
                for removed in ("environment", "model_metadata", "manual_review", "cost"):
                    self.assertNotIn(removed, result)
                attempt = result["attempts"][0]
                self.assertTrue(Path(attempt["raw_path"]).is_file())
                self.assertTrue(Path(attempt["source_path"]).is_file())
                self.assertNotIn("raw_response", attempt)
                self.assertNotIn("dafny_source", attempt)
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
