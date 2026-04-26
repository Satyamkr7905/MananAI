"""Tests for the v2 memory model: EMA, Leitner spacing, weakness decay, strengths."""

from __future__ import annotations

import unittest

from app.user_model.user_state import UserState


class EMATests(unittest.TestCase):
    def test_ema_updates_on_record_attempt(self) -> None:
        s = UserState()
        # Three perfect attempts should drive ema_accuracy toward 1.0.
        for _ in range(3):
            s.record_attempt(qid="q1", topic="arrays", correct=True, score=1.0,
                             hints_used=0, time_seconds=10.0, self_confidence=0.8, error_type=None,
                             question_tags=["loop"])
        self.assertGreater(s.topic("arrays").ema_accuracy, 0.75)

        # Three wrong attempts should pull it back down.
        for _ in range(3):
            s.record_attempt(qid="q1", topic="arrays", correct=False, score=0.0,
                             hints_used=0, time_seconds=60.0, self_confidence=0.7, error_type="logic",
                             question_tags=["loop"])
        self.assertLess(s.topic("arrays").ema_accuracy, 0.5)


class LeitnerTests(unittest.TestCase):
    def test_wrong_answer_keeps_box_at_1_and_schedules_soon(self) -> None:
        s = UserState()
        s.record_attempt(qid="q1", topic="arrays", correct=False, score=0.0,
                         hints_used=0, time_seconds=30.0, self_confidence=0.6, error_type="logic",
                         question_tags=["loop"])
        qs = s.qstat("q1")
        self.assertEqual(qs.box, 1)
        # Due 1 attempt into the future.
        self.assertEqual(qs.due_at_attempt, len(s.history) + 1)
        self.assertNotIn("q1", s.due_for_review_qids())   # not yet due

        # One more unrelated attempt passes → q1 is now due for review.
        s.record_attempt(qid="q2", topic="arrays", correct=True, score=1.0,
                         hints_used=0, time_seconds=20.0, self_confidence=0.9, error_type=None,
                         question_tags=["loop"])
        self.assertIn("q1", s.due_for_review_qids())

    def test_correct_answer_advances_box_and_pushes_out_due_date(self) -> None:
        s = UserState()
        s.record_attempt(qid="q1", topic="arrays", correct=True, score=1.0,
                         hints_used=0, time_seconds=20.0, self_confidence=0.9, error_type=None,
                         question_tags=["loop"])
        qs = s.qstat("q1")
        self.assertEqual(qs.box, 2)
        self.assertEqual(qs.due_at_attempt, len(s.history) + 3)


class WeaknessDecayTests(unittest.TestCase):
    def test_decay_reduces_weights(self) -> None:
        s = UserState()
        s.add_weakness("off_by_one", 3.0)
        s.decay_weaknesses(factor=0.5)
        self.assertAlmostEqual(s.weaknesses["off_by_one"], 1.5, places=6)

    def test_weakness_below_floor_is_removed(self) -> None:
        s = UserState()
        s.add_weakness("off_by_one", 0.2)
        s.decay_weaknesses(factor=0.2)  # drops below 0.1 threshold
        self.assertNotIn("off_by_one", s.weaknesses)


class StrengthTrackingTests(unittest.TestCase):
    def test_strengths_accumulate(self) -> None:
        s = UserState()
        s.add_strength("two_pointer", 1.0)
        s.add_strength("two_pointer", 0.8)
        self.assertAlmostEqual(s.strengths["two_pointer"], 1.8, places=6)
        self.assertIn("two_pointer", s.top_strengths(3))


class ScheduledReviewTests(unittest.TestCase):
    def test_schedule_is_fifo_and_dedup(self) -> None:
        s = UserState()
        s.schedule_review("a")
        s.schedule_review("b")
        s.schedule_review("a")  # duplicate should not re-append
        self.assertEqual(s.scheduled_reviews, ["a", "b"])
        self.assertEqual(s.pop_review(), "a")
        self.assertEqual(s.pop_review(), "b")
        self.assertIsNone(s.pop_review())


class SerializationRoundTripTests(unittest.TestCase):
    def test_roundtrip_preserves_all_v2_fields(self) -> None:
        s = UserState(user_id="x")
        s.topic("arrays").level = 2
        s.record_attempt(qid="q", topic="arrays", correct=True, score=0.9,
                         hints_used=1, time_seconds=42.0, self_confidence=0.75, error_type=None,
                         question_tags=["hash_map"])
        # Set these *after* the attempt so record_attempt's EMA update doesn't
        # surprise us — we're testing serialization, not EMA math.
        s.topic("arrays").ema_accuracy = 0.72
        s.add_weakness("off_by_one", 2.1)
        s.add_strength("hash_map", 1.4)
        s.schedule_review("q2")

        roundtrip = UserState.from_dict(s.to_dict())
        self.assertEqual(roundtrip.topic("arrays").level, 2)
        self.assertAlmostEqual(roundtrip.topic("arrays").ema_accuracy, 0.72, places=5)
        self.assertAlmostEqual(roundtrip.weaknesses["off_by_one"], 2.1, places=5)
        self.assertAlmostEqual(roundtrip.strengths["hash_map"], 1.4, places=5)
        self.assertEqual(roundtrip.scheduled_reviews, ["q2"])
        self.assertEqual(roundtrip.history[0].score, 0.9)
        self.assertAlmostEqual(roundtrip.history[0].self_confidence or 0.0, 0.75, places=5)
        # Leitner stat survives the round-trip too.
        self.assertEqual(roundtrip.qstat("q").box, 2)


class ConfidenceCalibrationTests(unittest.TestCase):
    def test_calibration_updates_when_confidence_present(self) -> None:
        s = UserState()
        s.record_attempt(
            qid="q1",
            topic="arrays",
            correct=False,
            score=0.2,
            hints_used=0,
            time_seconds=15.0,
            self_confidence=0.8,
            error_type="logic",
            question_tags=["loop"],
        )
        self.assertGreater(s.calibration_mae, 0.0)
        self.assertGreater(s.confidence_ema, 0.5)


if __name__ == "__main__":
    unittest.main()
