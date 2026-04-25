"""Tests for the v2 evaluator — partial credit and multi-approach scoring."""

from __future__ import annotations

import unittest

from app.interaction.evaluator import Evaluator


BASIC_Q = {
    "id": "x",
    "topic": "arrays",
    "difficulty": 1,
    "title": "Sum",
    "description": "",
    "solution": "",
    "tags": ["loop"],
    "expected_keywords": ["loop", "sum", "total", "add"],
}

TWO_SUM_MULTI = {
    "id": "ts",
    "topic": "arrays",
    "difficulty": 3,
    "title": "Two Sum",
    "description": "",
    "solution": "",
    "tags": ["hash_map"],
    "expected_keywords": ["complement", "hash"],
    "approaches": [
        {"name": "hash_map",
         "core": ["hash", "complement"],
         "keywords": ["hash", "map", "complement", "target", "seen"]},
        {"name": "sort_two_pointer",
         "core": ["sort", "two pointer"],
         "keywords": ["sort", "two pointer", "left", "right", "target"]},
    ],
}


class EvaluatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ev = Evaluator()

    def test_empty_answer_scores_zero(self) -> None:
        r = self.ev.evaluate(BASIC_Q, "")
        self.assertFalse(r["correct"])
        self.assertEqual(r["score"], 0.0)

    def test_give_up_short_circuits(self) -> None:
        r = self.ev.evaluate(BASIC_Q, "idk")
        self.assertFalse(r["correct"])
        self.assertEqual(r["error_type"], "unknown")

    def test_full_answer_correct(self) -> None:
        r = self.ev.evaluate(BASIC_Q, "use a loop to add each element to a running total sum")
        self.assertTrue(r["correct"])
        self.assertGreater(r["score"], 0.65)
        self.assertIn("loop", r["matched"])

    def test_partial_credit_between_0_and_1(self) -> None:
        r = self.ev.evaluate(BASIC_Q, "I'd use a for loop")
        # Matches "loop" only -> score low-mid, not correct, but > 0.
        self.assertFalse(r["correct"])
        self.assertGreater(r["score"], 0.0)
        self.assertLess(r["score"], 0.65)

    def test_missed_keywords_are_reported(self) -> None:
        r = self.ev.evaluate(BASIC_Q, "loop")
        self.assertIn("sum", r["missed"])

    # ---- multi-approach ----

    def test_multi_approach_picks_best_match(self) -> None:
        """Both approaches are valid; evaluator picks the one that fits the answer."""
        # Hash-map phrasing should match the hash_map approach.
        r1 = self.ev.evaluate(
            TWO_SUM_MULTI,
            "Store complements in a hash map and look them up in O(1)",
        )
        self.assertTrue(r1["correct"])
        self.assertEqual(r1["approach"], "hash_map")

        # Sort + two-pointer phrasing should match the other approach.
        r2 = self.ev.evaluate(
            TWO_SUM_MULTI,
            "Sort the array then use two pointers left/right moving toward target",
        )
        self.assertTrue(r2["correct"])
        self.assertEqual(r2["approach"], "sort_two_pointer")

    def test_brute_force_tagged_as_time_complexity_issue(self) -> None:
        r = self.ev.evaluate(TWO_SUM_MULTI, "Just use a brute force nested for loop")
        self.assertFalse(r["correct"])
        self.assertEqual(r["error_type"], "time_complexity_issue")


if __name__ == "__main__":
    unittest.main()
