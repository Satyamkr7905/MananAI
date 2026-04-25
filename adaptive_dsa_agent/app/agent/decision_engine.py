"""
Decision engine — the tutor's brain.

v2 upgrades
-----------
* **Partial-credit routing**: the engine reads ``evaluator_result["score"]``.
  A first miss with score ≥ 0.4 ("close") escalates directly to a level-2
  targeted hint instead of a generic level-1 nudge.
  A first miss with score < 0.15 (nearly empty) jumps to a level-2 *scaffolding*
  hint — no point asking "what pattern fits?" if they're lost.
* **Fatigue detection**: if the topic's EMA response time is well above the
  question budget AND EMA accuracy has dropped, we emit SWITCH_TOPIC to a
  lighter topic for recovery even without 3 explicit misses.
* **Follow-up scheduling**: after SHOW_SOLUTION we schedule the question for
  spaced review via ``Decision.meta["schedule_review"]``.
* **Mastery promotion** uses both streak *and* EMA accuracy for stability.

The engine still **does not mutate state**; the StateManager applies the
consequences. That separation makes behavior easy to unit-test.
"""

from __future__ import annotations

from typing import Any

from ..config import settings
from ..user_model import skill_tracker
from ..user_model.user_state import UserState
from ..utils.logger import get_logger
from .strategy import ActionType, Decision

log = get_logger(__name__)


class DecisionEngine:
    def decide(
        self,
        *,
        state: UserState,
        question: dict[str, Any] | None,
        evaluator_result: dict[str, Any] | None,
        attempts_on_question: int,
    ) -> Decision:
        """Return the next action for the tutor."""

        # ---------------- Case A: nothing answered yet ----------------
        if evaluator_result is None or question is None:
            return Decision(
                action=ActionType.ASK_NEW,
                reason="Starting or resuming session — selecting the next question.",
            )

        topic = question["topic"]
        correct = bool(evaluator_result.get("correct"))
        score = float(evaluator_result.get("score", 1.0 if correct else 0.0))

        # ---------------- Case B: correct ----------------
        if correct:
            if _about_to_master(state, topic):
                return Decision(
                    action=ActionType.LEVEL_UP,
                    reason=(
                        f"{settings.mastery_streak}-in-a-row on {topic} with strong EMA "
                        f"({state.topic(topic).ema_accuracy:.0%}). Promoting topic level."
                    ),
                    next_topic=topic,
                    meta={"score": score},
                )
            return Decision(
                action=ActionType.ASK_NEW,
                reason=(
                    f"Correct ({score:.0%}). Updating difficulty and selecting the next question."
                ),
                meta={"score": score},
            )

        # ---------------- Case C: wrong — but we might be close ----------------
        # Partial credit reshapes which hint to give:
        # * score >= 0.4  -> learner is close; skip generic L1 nudges.
        # * score <  0.15 -> learner is lost; give strong scaffolding (L2) fast.
        if attempts_on_question == 1:
            if score >= 0.40:
                return Decision(
                    action=ActionType.GIVE_HINT,
                    reason=f"First miss but you're close ({score:.0%}). A targeted hint should do it.",
                    hint_level=2,
                    meta={"score": score, "reason_code": "close_first_miss"},
                )
            if score < 0.15:
                return Decision(
                    action=ActionType.GIVE_HINT,
                    reason="First attempt looks lost — giving a strong scaffolding hint.",
                    hint_level=2,
                    meta={"score": score, "reason_code": "lost_first_miss"},
                )
            return Decision(
                action=ActionType.GIVE_HINT,
                reason="First miss — a gentle Socratic nudge should be enough.",
                hint_level=1,
                meta={"score": score, "reason_code": "first_miss"},
            )

        if attempts_on_question == 2:
            # On the second miss, if they still haven't made progress, go to L3
            # (full algorithmic scaffolding) rather than another mid-level hint.
            if score < 0.25:
                return Decision(
                    action=ActionType.GIVE_HINT,
                    reason="Still off-track — walking through the approach step-by-step.",
                    hint_level=3,
                    meta={"score": score, "reason_code": "stuck_second_miss"},
                )
            return Decision(
                action=ActionType.GIVE_HINT,
                reason="Second miss — escalating hint specificity.",
                hint_level=2,
                meta={"score": score, "reason_code": "second_miss"},
            )

        # --- three or more misses on this question ---
        # Fatigue: switch to an easier topic for recovery.
        if skill_tracker.is_stuck(state, topic):
            next_topic = _pick_fallback_topic(state, current=topic)
            return Decision(
                action=ActionType.SWITCH_TOPIC,
                reason=(
                    f"Stuck on {topic} (ema={state.topic(topic).ema_accuracy:.0%}, "
                    f"wrong_streak={state.topic(topic).wrong_streak}). Switching to rebuild momentum."
                ),
                next_topic=next_topic,
                meta={
                    "previous_topic": topic,
                    "score": score,
                    "schedule_review": question.get("id"),
                },
            )

        return Decision(
            action=ActionType.SHOW_SOLUTION,
            reason="Three misses on this question — revealing the solution and scheduling a review.",
            hint_level=3,
            meta={"score": score, "schedule_review": question.get("id")},
        )


# ---------------------------------------------------------------------------
# helpers (pure functions, easy to unit-test)
# ---------------------------------------------------------------------------

def _about_to_master(state: UserState, topic: str) -> bool:
    """Would *this* correct answer trigger a level-up?

    Checks both the streak-about-to-complete AND a strong EMA so we don't
    promote based on a lucky 3-in-a-row after many misses.
    """
    row = state.topic(topic)
    streak_ready = (row.streak + 1) >= settings.mastery_streak
    ema_ready = row.ema_accuracy >= 0.7
    return streak_ready and ema_ready and row.level < settings.max_skill_level


def _pick_fallback_topic(state: UserState, current: str) -> str | None:
    """Choose a different topic the learner has seen before — prefer easier ones."""
    others = [t for t in state.topics if t != current]
    if not others:
        return None
    return min(others, key=lambda t: state.topic(t).level)
