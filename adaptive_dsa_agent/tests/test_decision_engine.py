"""Tests for the decision engine.

Covers every branch in the v2 rule table:
* correct -> ASK_NEW
* correct + mastery-ready (streak + EMA) -> LEVEL_UP
* wrong #1 far-off -> GIVE_HINT level 1
* wrong #1 close (score >= 0.4) -> GIVE_HINT level 2 (skip generic nudge)
* wrong #1 lost (score < 0.15) -> GIVE_HINT level 2 (strong scaffolding)
* wrong #2 still lost -> GIVE_HINT level 3
* wrong #2 close -> GIVE_HINT level 2
* wrong #3 (no stuck) -> SHOW_SOLUTION + schedules review
* wrong #3 (stuck topic) -> SWITCH_TOPIC + schedules review
"""

from __future__ import annotations

import unittest

from app.agent.decision_engine import DecisionEngine
from app.agent.strategy import ActionType
from app.config import settings
from app.user_model.user_state import UserState


Q = {"id": "arr_001", "topic": "arrays", "difficulty": 1}


def _wrong(score: float, error_type: str = "logic") -> dict:
    return {"correct": False, "score": score, "error_type": error_type}


class DecisionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = DecisionEngine()
        self.state = UserState(user_id="t")

    # ---- bootstrap path ----

    def test_no_evaluation_yet_picks_new_question(self) -> None:
        d = self.engine.decide(
            state=self.state, question=None, evaluator_result=None, attempts_on_question=0,
        )
        self.assertEqual(d.action, ActionType.ASK_NEW)

    # ---- correct path ----

    def test_correct_answer_asks_new_question(self) -> None:
        d = self.engine.decide(
            state=self.state, question=Q,
            evaluator_result={"correct": True, "score": 1.0}, attempts_on_question=1,
        )
        self.assertEqual(d.action, ActionType.ASK_NEW)

    def test_level_up_requires_both_streak_and_ema(self) -> None:
        """LEVEL_UP only fires when the EMA supports the streak — guards flukes."""
        # Streak about to hit mastery_streak, but EMA is low — no promotion.
        row = self.state.topic("arrays")
        row.streak = settings.mastery_streak - 1
        row.ema_accuracy = 0.55
        d = self.engine.decide(
            state=self.state, question=Q,
            evaluator_result={"correct": True, "score": 1.0}, attempts_on_question=1,
        )
        self.assertEqual(d.action, ActionType.ASK_NEW)

        # Now raise the EMA; promotion should fire.
        row.ema_accuracy = 0.8
        d2 = self.engine.decide(
            state=self.state, question=Q,
            evaluator_result={"correct": True, "score": 1.0}, attempts_on_question=1,
        )
        self.assertEqual(d2.action, ActionType.LEVEL_UP)

    # ---- wrong path with partial credit routing ----

    def test_first_wrong_far_off_gives_l1(self) -> None:
        d = self.engine.decide(
            state=self.state, question=Q,
            evaluator_result=_wrong(0.2), attempts_on_question=1,
        )
        self.assertEqual(d.action, ActionType.GIVE_HINT)
        self.assertEqual(d.hint_level, 1)

    def test_first_wrong_close_jumps_to_l2(self) -> None:
        """Score >= 0.4 on the first miss -> targeted L2 hint, not generic L1."""
        d = self.engine.decide(
            state=self.state, question=Q,
            evaluator_result=_wrong(0.5), attempts_on_question=1,
        )
        self.assertEqual(d.action, ActionType.GIVE_HINT)
        self.assertEqual(d.hint_level, 2)
        self.assertEqual(d.meta.get("reason_code"), "close_first_miss")

    def test_first_wrong_lost_jumps_to_l2_scaffold(self) -> None:
        """Score < 0.15 on the first miss -> strong scaffolding (L2), not Socratic L1."""
        d = self.engine.decide(
            state=self.state, question=Q,
            evaluator_result=_wrong(0.05), attempts_on_question=1,
        )
        self.assertEqual(d.action, ActionType.GIVE_HINT)
        self.assertEqual(d.hint_level, 2)
        self.assertEqual(d.meta.get("reason_code"), "lost_first_miss")

    def test_second_wrong_still_lost_jumps_to_l3(self) -> None:
        d = self.engine.decide(
            state=self.state, question=Q,
            evaluator_result=_wrong(0.15), attempts_on_question=2,
        )
        self.assertEqual(d.action, ActionType.GIVE_HINT)
        self.assertEqual(d.hint_level, 3)

    def test_second_wrong_close_gives_l2(self) -> None:
        d = self.engine.decide(
            state=self.state, question=Q,
            evaluator_result=_wrong(0.45), attempts_on_question=2,
        )
        self.assertEqual(d.action, ActionType.GIVE_HINT)
        self.assertEqual(d.hint_level, 2)

    def test_third_wrong_shows_solution_and_schedules_review(self) -> None:
        self.state.topic("arrays").wrong_streak = 0
        d = self.engine.decide(
            state=self.state, question=Q,
            evaluator_result=_wrong(0.2), attempts_on_question=3,
        )
        self.assertEqual(d.action, ActionType.SHOW_SOLUTION)
        self.assertEqual(d.meta.get("schedule_review"), "arr_001")

    def test_third_wrong_switches_topic_when_stuck(self) -> None:
        self.state.topic("arrays").wrong_streak = settings.stuck_wrong_streak
        self.state.topic("arrays").ema_accuracy = 0.2
        self.state.topic("dp").level = 1
        d = self.engine.decide(
            state=self.state, question=Q,
            evaluator_result=_wrong(0.1), attempts_on_question=3,
        )
        self.assertEqual(d.action, ActionType.SWITCH_TOPIC)
        self.assertEqual(d.next_topic, "dp")
        self.assertEqual(d.meta.get("schedule_review"), "arr_001")


if __name__ == "__main__":
    unittest.main()
