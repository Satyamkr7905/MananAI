"""
StateManager — single façade for mutating and persisting UserState.

v2 upgrades
-----------
* Applies **weakness decay** on every attempt so fixed weaknesses actually fade.
* Records **strengths** on correct answers (symmetric to weaknesses).
* Feeds the evaluator's ``score`` into both EMAs and the topic-skill update.
* Exposes ``schedule_review(qid)`` for the CLI to honor the engine's follow-up.
* Keeps the decision engine purely *read-only* over state — every write is here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..config import settings
from ..user_model import skill_tracker
from ..user_model.user_state import UserState, load_user_state, save_user_state
from ..user_model.weakness_detector import (
    detect_strengths,
    detect_weakness,
    record_strengths,
    record_weakness,
)
from ..utils.logger import get_logger

log = get_logger(__name__)


class StateManager:
    """Façade for mutating ``UserState``.

    By default progress is written to ``data/user_progress.json``. Pass
    ``persist_callback`` to redirect persistence (e.g. SQL database in the
    FastAPI server) without changing the rest of the tutor logic.
    """

    def __init__(
        self,
        user_id: str = "default",
        *,
        initial_state: UserState | None = None,
        persist_callback: Callable[[UserState], None] | None = None,
    ):
        self.user_id = user_id
        self._persist_callback = persist_callback
        if initial_state is not None:
            self.state = initial_state
        else:
            self.state = load_user_state(user_id)
        log.info(
            "Loaded state for user=%s (topics=%d, attempts=%d, weaknesses=%d, strengths=%d)",
            user_id,
            len(self.state.topics),
            len(self.state.history),
            len(self.state.weaknesses),
            len(self.state.strengths),
        )

    # ---------------- session lifecycle ----------------

    def persist(self) -> None:
        if self._persist_callback is not None:
            self._persist_callback(self.state)
        else:
            save_user_state(self.state)

    # ---------------- attempt updates ----------------

    def register_attempt(
        self,
        *,
        question: dict[str, Any],
        user_answer: str,
        evaluator_result: dict[str, Any],
        hints_used: int,
        elapsed_seconds: float,
        self_confidence: float | None = None,
    ) -> dict[str, Any]:
        """Apply every consequence of one attempt; returns a short summary dict."""
        topic = question["topic"]
        correct = bool(evaluator_result.get("correct"))
        score = float(evaluator_result.get("score", 1.0 if correct else 0.0))

        # 1) Decay weaknesses first so a brand-new weakness this attempt isn't diluted.
        self.state.decay_weaknesses()

        # 2) Skill tracker: streaks, level changes, EMA updates.
        leveled_up = leveled_down = False
        if correct:
            leveled_up = skill_tracker.register_correct(self.state, topic, score)
        else:
            leveled_down = skill_tracker.register_wrong(self.state, topic, score)

        # 3) Weakness detection (weighted by how wrong the answer was).
        weakness_tag, weakness_weight = detect_weakness(
            question=question,
            user_answer=user_answer,
            evaluator_result=evaluator_result,
            elapsed_seconds=elapsed_seconds,
        )
        record_weakness(self.state, weakness_tag, weakness_weight)

        # 4) Strength detection (only on correct answers).
        strengths = detect_strengths(
            question=question,
            user_answer=user_answer,
            evaluator_result=evaluator_result,
        )
        record_strengths(self.state, strengths)

        # 5) Append history, update recency, avg time, Leitner box, tag exposure.
        self.state.record_attempt(
            qid=question["id"],
            topic=topic,
            correct=correct,
            score=score,
            hints_used=hints_used,
            time_seconds=elapsed_seconds,
            self_confidence=self_confidence,
            error_type=evaluator_result.get("error_type"),
            question_tags=question.get("tags") or [],
        )

        # 6) Remember focus topic so the selector has a default.
        self.state.current_topic = topic

        return {
            "leveled_up": leveled_up,
            "leveled_down": leveled_down,
            "weakness": weakness_tag,
            "weakness_weight": weakness_weight,
            "strengths": [t for t, _ in strengths],
            "score": score,
        }

    def apply_decision_side_effects(self, decision_meta: dict[str, Any]) -> None:
        """Honor follow-up meta fields emitted by the decision engine."""
        qid = decision_meta.get("schedule_review")
        if qid:
            self.state.schedule_review(qid)
            log.info("Scheduled review for qid=%s", qid)

    def switch_topic(self, new_topic: str) -> None:
        old = self.state.current_topic
        if old and old in self.state.topics:
            self.state.topic(old).wrong_streak = 0
        self.state.current_topic = new_topic
        log.info("Switched topic from '%s' to '%s'", old, new_topic)

    # ---------------- read-only views ----------------

    @property
    def user_state(self) -> UserState:
        return self.state

    @staticmethod
    def config_snapshot() -> dict[str, Any]:
        return {
            "mastery_streak": settings.mastery_streak,
            "stuck_wrong_streak": settings.stuck_wrong_streak,
            "recent_question_window": settings.recent_question_window,
            "spaced_repetition_cooldown": settings.spaced_repetition_cooldown,
        }
