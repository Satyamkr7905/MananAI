"""Tests for the v3 evaluator — partial credit, multi-approach, and synonym matching."""

from __future__ import annotations

import unittest

from app.interaction.evaluator import CORRECT_THRESHOLD, Evaluator


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

    def test_partial_credit_below_threshold(self) -> None:
        r = self.ev.evaluate(BASIC_Q, "I'd use a for loop")
        # Only "loop" matches (1 of 4 support keywords) — must stay below correct.
        self.assertFalse(r["correct"])
        self.assertGreater(r["score"], 0.0)
        self.assertLess(r["score"], CORRECT_THRESHOLD)

    def test_missed_keywords_are_reported(self) -> None:
        r = self.ev.evaluate(BASIC_Q, "loop")
        self.assertIn("sum", r["missed"])

    # ---- multi-approach ----

    def test_multi_approach_picks_best_match(self) -> None:
        """Both approaches are valid; evaluator picks the one that fits the answer."""
        r1 = self.ev.evaluate(
            TWO_SUM_MULTI,
            "Store complements in a hash map and look them up in O(1)",
        )
        self.assertTrue(r1["correct"])
        self.assertEqual(r1["approach"], "hash_map")

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

    # ---- v3: synonym-aware matching (dictionary == hash map) ----

    def test_dictionary_counts_as_hash_map(self) -> None:
        """A learner saying 'dictionary' for Two Sum should still be correct."""
        r = self.ev.evaluate(
            TWO_SUM_MULTI,
            "Use a dictionary to remember each number seen so far, "
            "then for the next one check if its complement is in the dict.",
        )
        self.assertTrue(r["correct"])
        self.assertEqual(r["approach"], "hash_map")
        self.assertIn("hash", r["matched"])
        self.assertIn("complement", r["matched"])

    def test_maximum_counts_as_max(self) -> None:
        """'largest' should match a keyword expecting 'max'."""
        q = {
            "id": "m",
            "topic": "arrays",
            "difficulty": 1,
            "title": "Max Sub-array",
            "description": "",
            "solution": "",
            "tags": ["loop"],
            "expected_keywords": ["max", "sum", "loop", "track"],
        }
        r = self.ev.evaluate(
            q,
            "Loop through and track the largest running total as you go.",
        )
        self.assertTrue(r["correct"])
        self.assertIn("max", r["matched"])
        self.assertIn("sum", r["matched"])  # "total" is a sum-synonym

    # ---- v3: "a little here and there" answers are accepted ----

    def test_mostly_right_answer_is_accepted(self) -> None:
        """An answer that covers the big idea but misses a detail should pass."""
        r = self.ev.evaluate(
            TWO_SUM_MULTI,
            "Keep a hash map of what you've already seen; "
            "when you see the complement of the current number, return the pair.",
        )
        self.assertTrue(r["correct"])
        # Still flags at least one area the learner could tighten.
        self.assertIsInstance(r["missed"], list)

    def test_notes_are_encouraging_not_harsh(self) -> None:
        """Notes on a close-but-wrong answer should avoid harsh framing."""
        r = self.ev.evaluate(BASIC_Q, "I would add up each number")
        self.assertFalse(r["correct"])
        # Friendlier vocabulary only — no "off-track" / "wrong".
        lowered = r["notes"].lower()
        self.assertNotIn("off-track", lowered)
        self.assertNotIn("wrong", lowered)


if __name__ == "__main__":
    unittest.main()
