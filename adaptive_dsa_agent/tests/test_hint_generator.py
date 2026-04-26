"""Tests for counterfactual follow-up generation."""

from __future__ import annotations

import unittest

from app.interaction.hint_generator import HintGenerator


class CounterfactualTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hg = HintGenerator()

    def test_uses_question_defined_counterfactual_prompt(self) -> None:
        q = {
            "id": "x1",
            "title": "Two Sum",
            "tags": ["hash_map"],
            "counterfactual_prompts": ["What if the stream never ends?"],
        }
        out = self.hg.generate_counterfactual(q, {"score": 1.0})
        self.assertEqual(out, "What if the stream never ends?")

    def test_fallback_counterfactual_from_tags(self) -> None:
        q = {
            "id": "x2",
            "title": "Two Sum",
            "tags": ["hash_map"],
        }
        out = self.hg.generate_counterfactual(q, {"score": 0.8})
        self.assertIn("memory", out.lower())


if __name__ == "__main__":
    unittest.main()
