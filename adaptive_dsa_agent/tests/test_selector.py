"""Tests for the question selector (v2).

Behaviors verified:
* topic filter is respected
* level-0 user is steered to easy questions (ZPD)
* higher skill promotes harder questions
* recently-asked questions are penalized
* weakness-matching questions are boosted
* strengths-matching tags are gently down-weighted (breadth over drill)
* scheduled reviews jump to the front
* reason string is informative
"""

from __future__ import annotations

import json
import random
import tempfile
import unittest
from pathlib import Path

from app.question_engine.question_bank import QuestionBank
from app.question_engine.selector import QuestionSelector
from app.user_model.user_state import UserState


FIXTURE = [
    {"id": "a1", "topic": "arrays", "difficulty": 1,
     "title": "A1", "description": "", "solution": "",
     "tags": ["loop"], "expected_keywords": ["loop"]},
    {"id": "a2", "topic": "arrays", "difficulty": 2,
     "title": "A2", "description": "", "solution": "",
     "tags": ["two_pointer", "off_by_one"], "expected_keywords": ["swap"]},
    {"id": "a3", "topic": "arrays", "difficulty": 3,
     "title": "A3", "description": "", "solution": "",
     "tags": ["hash_map"], "expected_keywords": ["map"]},
    {"id": "d1", "topic": "dp", "difficulty": 1,
     "title": "D1", "description": "", "solution": "",
     "tags": ["base_case"], "expected_keywords": ["fib"]},
]


class SelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = Path(self.tmp.name) / "questions.json"
        path.write_text(json.dumps(FIXTURE), encoding="utf-8")
        self.bank = QuestionBank(path=path)
        self.selector = QuestionSelector(self.bank, rng=random.Random(0))

    def test_respects_topic_filter(self) -> None:
        state = UserState(current_topic="dp")
        sel = self.selector.select(state)
        self.assertIsNotNone(sel)
        self.assertEqual(sel.question["topic"], "dp")

    def test_level_0_prefers_easiest_question(self) -> None:
        state = UserState(current_topic="arrays")
        sel = self.selector.select(state)
        self.assertEqual(sel.question["id"], "a1")

    def test_higher_skill_promotes_harder_questions(self) -> None:
        state = UserState(current_topic="arrays")
        row = state.topic("arrays")
        row.level = 2
        row.ema_accuracy = 0.75  # solid — target difficulty ~3.25
        sel = self.selector.select(state)
        self.assertEqual(sel.question["id"], "a3")

    def test_recently_asked_question_is_penalized(self) -> None:
        state = UserState(current_topic="arrays")
        state.topic("arrays").level = 1
        state.topic("arrays").ema_accuracy = 0.65
        state.push_recent("a2")
        sel = self.selector.select(state)
        self.assertNotEqual(sel.question["id"], "a2")

    def test_weakness_boosts_matching_question(self) -> None:
        state = UserState(current_topic="arrays")
        # Level-0 user would otherwise get a1; weakness pushes us to a2.
        state.add_weakness("off_by_one", 3.0)
        sel = self.selector.select(state)
        self.assertEqual(sel.question["id"], "a2")
        self.assertIn("off_by_one", sel.reason)

    def test_strength_penalty_discourages_overdrilling(self) -> None:
        """With strong mastery of `loop` and no weaknesses, a2 should beat a1.

        Even though a1 is the easiest and would normally win on ZPD alone,
        the strength penalty on its `loop` tag drops its score below a2.
        """
        state = UserState(current_topic="arrays")
        state.topic("arrays").level = 1         # target ≈ 2
        state.topic("arrays").ema_accuracy = 0.65
        state.add_strength("loop", 5.0)         # heavy strength on a1's tag
        sel = self.selector.select(state)
        self.assertIn(sel.question["id"], {"a2", "a3"})
        self.assertNotEqual(sel.question["id"], "a1")

    def test_scheduled_review_jumps_to_front(self) -> None:
        state = UserState(current_topic="arrays")
        state.topic("arrays").level = 2          # would otherwise prefer a2/a3
        state.topic("arrays").ema_accuracy = 0.7
        state.schedule_review("a1")              # but a1 is a forced review
        sel = self.selector.select(state)
        self.assertEqual(sel.question["id"], "a1")
        self.assertIn("review", sel.reason.lower())

    def test_reason_string_contains_zpd_info(self) -> None:
        state = UserState(current_topic="arrays")
        sel = self.selector.select(state)
        self.assertIn("difficulty", sel.reason.lower())
        self.assertIn("success", sel.reason.lower())  # ZPD band text


if __name__ == "__main__":
    unittest.main()
