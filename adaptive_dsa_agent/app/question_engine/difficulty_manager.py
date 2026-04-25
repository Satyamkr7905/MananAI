"""
Difficulty manager — pure-function utilities for bumping and clamping difficulty.

v2 now works with **float** targets so the selector can express "aim for 2.4".
"""

from __future__ import annotations

from ..config import settings


def clamp(value: float) -> float:
    return max(float(settings.min_difficulty), min(float(settings.max_difficulty), float(value)))


def bump_up(difficulty: float, amount: float = 1.0) -> float:
    return clamp(difficulty + max(0.5, float(amount)))


def bump_down(difficulty: float, amount: float = 1.0) -> float:
    return clamp(difficulty - max(0.5, float(amount)))


def target_window(center: float, spread: float = 1.0) -> tuple[int, int]:
    """Return an (int, int) difficulty window covering ``center ± spread``."""
    lo = int(max(settings.min_difficulty, round(center - spread)))
    hi = int(min(settings.max_difficulty, round(center + spread)))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def predicted_success(diff_target: float, q_difficulty: int) -> float:
    """Estimate P(correct) for a learner whose ideal difficulty is ``diff_target``.

    Linear falloff: at Δ=0 the learner is ~75% likely to solve it; each extra
    level above their target drops success by ~20%; each level below raises it.
    Clipped to [0.05, 0.95].
    """
    delta = float(q_difficulty) - float(diff_target)
    p = 0.75 - 0.2 * delta
    return max(0.05, min(0.95, p))
