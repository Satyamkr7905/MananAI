"""
Skill tracker — update rules for topic skill, streak and difficulty targeting.

v2 upgrades
-----------
* ``recommend_difficulty`` now returns a **float** so the selector can reason
  about fractional difficulty targets (e.g. 2.4) instead of clamping to ints.
* The target is driven by the learner's EMA accuracy, not just level:
  - at ema≈0.75 (the ZPD sweet spot) we stay on the current level
  - high accuracy pulls target up toward level+2
  - low accuracy pulls it down toward level
* Confidence tracks EMA accuracy so it's no longer just a decay counter.
* Skill level changes now also require the EMA to support the streak —
  a lucky 3-in-a-row after many misses won't promote prematurely.
"""

from __future__ import annotations

from ..config import settings
from ..utils.logger import get_logger
from .user_state import UserState

log = get_logger(__name__)


def register_correct(state: UserState, topic: str, score: float = 1.0) -> bool:
    """Update skills after a correct answer; returns True if the level increased."""
    row = state.topic(topic)
    row.streak += 1
    row.wrong_streak = 0

    leveled_up = False
    # Require both the streak AND a reliable EMA before promoting.
    promotion_ready = (
        row.streak >= settings.mastery_streak
        and row.ema_accuracy >= 0.7
        and row.level < settings.max_skill_level
    )
    if promotion_ready:
        row.level += 1
        row.streak = 0
        leveled_up = True
        log.info("Topic '%s' leveled UP to %d (ema=%.2f)", topic, row.level, row.ema_accuracy)

    # Keep global confidence roughly aligned with recent topic accuracy.
    state.confidence = min(1.0, 0.7 * state.confidence + 0.3 * row.ema_accuracy)
    return leveled_up


def register_wrong(state: UserState, topic: str, score: float = 0.0) -> bool:
    """Update skills after a wrong answer; returns True if the level decreased."""
    row = state.topic(topic)
    row.wrong_streak += 1
    row.streak = 0

    leveled_down = False
    # Demotion is softer: stuck-streak AND ema below 0.4.
    demotion_ready = (
        row.wrong_streak >= settings.stuck_wrong_streak
        and row.ema_accuracy < 0.4
        and row.level > settings.min_skill_level
    )
    if demotion_ready:
        row.level -= 1
        row.wrong_streak = 0
        leveled_down = True
        log.info("Topic '%s' leveled DOWN to %d (ema=%.2f)", topic, row.level, row.ema_accuracy)

    state.confidence = max(0.0, 0.7 * state.confidence + 0.3 * row.ema_accuracy)
    return leveled_down


def is_mastered(state: UserState, topic: str) -> bool:
    return state.topic(topic).level >= settings.max_skill_level


def is_stuck(state: UserState, topic: str) -> bool:
    row = state.topic(topic)
    # Both a hard stuck-streak and an EMA-based signal catch "wobbly" learners.
    return row.wrong_streak >= settings.stuck_wrong_streak or (
        row.attempts >= 4 and row.ema_accuracy < 0.35
    )


def is_fatigued(state: UserState, topic: str, baseline_seconds: float | None = None) -> bool:
    """Heuristic: response time climbing AND accuracy dropping."""
    row = state.topic(topic)
    if row.attempts < 3:
        return False
    if baseline_seconds and row.ema_response_time > baseline_seconds * 1.5:
        return row.ema_accuracy < 0.45
    return False


def recommend_difficulty(state: UserState, topic: str) -> float:
    """Continuous difficulty target derived from level + EMA accuracy.

    Returns a float in ``[min_difficulty, max_difficulty]``. The selector
    rounds/softmaxes this into an actual question pick.

    Mapping:
      base = level + 1                       # level 0 -> diff 1
      gain = (ema_accuracy - 0.65) * 2.5     # +0.875 at ema=1.0, -1.625 at ema=0.0
      target = clamp(base + gain, 1, 5)
    """
    row = state.topic(topic)
    base = row.level + 1
    # ZPD research: aim for ~65-75% predicted success. We peg the reference at 0.65
    # so hitting it keeps us at the current level (no runaway promotion).
    gain = (row.ema_accuracy - 0.65) * 2.5
    target = base + gain
    return max(float(settings.min_difficulty), min(float(settings.max_difficulty), target))
