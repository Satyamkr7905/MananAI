"""
Weakness (and strength) detector — the agent's symptom reader.

v2 upgrades
-----------
* Also emits **strengths**: when a learner answers correctly, tags they used
  successfully are logged so the selector can avoid over-drilling them.
* Signal weight is scaled by the evaluator's partial-credit score so a
  barely-correct answer doesn't mark a topic as a strong suit.
* Much richer keyword pattern library, including positive cues like
  "two pointers", "hash map", "bottom up" that *evidence* a technique.
"""

from __future__ import annotations

import re
from typing import Any

from .user_state import UserState


# Patterns the *wrong* side of an answer leaks. Order = which weakness we pick
# first when multiple match.
_WEAKNESS_PATTERNS: list[tuple[str, str]] = [
    (r"\b(off[-\s]?by[-\s]?one|boundary|index\s*out|i\s*[-+]\s*1)\b", "off_by_one"),
    (r"\b(base\s*case|infinite\s*recursion|stack\s*overflow|recursion\s*limit)\b", "base_case_issue"),
    (r"\b(tle|too\s*slow|timeout|brute\s*force|o\(n\^?2\)|exponential)\b", "time_complexity_issue"),
    (r"\b(state\s*(definition|meaning)|not\s*sure\s*what\s*dp)\b", "state_definition"),
    (r"\b(null|none\s*type|undefined|attribute\s*error)\b", "null_handling"),
]

# Patterns that *evidence* a technique. Used to log strengths on correct answers.
_STRENGTH_PATTERNS: list[tuple[str, str]] = [
    (r"\btwo[-\s]?pointer", "two_pointer"),
    (r"\bsliding[-\s]?window\b", "sliding_window"),
    (r"\bhash\s*(map|set|table)\b|\bdict(ionary)?\b", "hash_map"),
    (r"\b(bottom[-\s]?up|tabulation|iterative\s*dp)\b", "1d_dp"),
    (r"\b(top[-\s]?down|memoi[sz]ation)\b", "memoization"),
    (r"\bkadane", "kadane"),
    (r"\brecurrence|\bdp\[i\]|\bdp\[i\]\[j\]", "state_definition"),
    (r"\bbinary\s*search\b", "binary_search"),
]


def detect_weakness(
    *,
    question: dict[str, Any],
    user_answer: str,
    evaluator_result: dict[str, Any],
    elapsed_seconds: float,
) -> tuple[str | None, float]:
    """Return (weakness_tag, weight). Weight scales with how wrong the answer was."""
    score = float(evaluator_result.get("score", 1.0 if evaluator_result.get("correct") else 0.0))
    correct = bool(evaluator_result.get("correct"))

    if correct:
        # Even a correct answer can expose a latent weakness if it was too slow.
        budget = question.get("time_budget_seconds") or 0
        if budget and elapsed_seconds > budget * 1.75 and "time_complexity_issue" in (question.get("tags") or []):
            return ("time_complexity_issue", 0.5)
        return (None, 0.0)

    # Weight is higher the further from correct the score was.
    weight = max(0.4, 1.0 - score)

    # 1) Trust the evaluator's explicit error_type if it named a pitfall.
    err = evaluator_result.get("error_type")
    pitfalls = {"off_by_one", "base_case_issue", "time_complexity_issue",
                "state_definition", "null_handling", "logic"}
    if err in pitfalls and err != "logic":
        return (err, weight)

    # 2) Scan the user's own answer for leak patterns.
    ans = (user_answer or "").lower()
    for pattern, tag in _WEAKNESS_PATTERNS:
        if re.search(pattern, ans):
            return (tag, weight)

    # 3) Fall back to the question's tags if any match the pitfall set.
    for t in question.get("tags") or []:
        if t in pitfalls and t != "logic":
            return (t, weight * 0.6)  # softer — this is a guess

    return ("logic" if err == "logic" else None, weight if err == "logic" else 0.0)


def detect_strengths(
    *, question: dict[str, Any], user_answer: str, evaluator_result: dict[str, Any]
) -> list[tuple[str, float]]:
    """Return [(tag, weight), …] of techniques the learner *demonstrated*."""
    if not evaluator_result.get("correct"):
        return []
    score = float(evaluator_result.get("score", 1.0))
    weight = max(0.4, score)

    ans = (user_answer or "").lower()
    found: dict[str, float] = {}

    # Patterns in the answer text.
    for pattern, tag in _STRENGTH_PATTERNS:
        if re.search(pattern, ans):
            found[tag] = max(found.get(tag, 0.0), weight)

    # Plus any tag from the question that was *intended* to be used.
    # These are half-weighted because we can't verify the learner really used them.
    for t in question.get("tags") or []:
        if t not in {"hard", "easy"} and t not in found:
            found[t] = max(found.get(t, 0.0), weight * 0.5)

    return list(found.items())


def record_weakness(state: UserState, tag: str | None, weight: float = 1.0) -> None:
    state.add_weakness(tag, weight)


def record_strengths(state: UserState, items: list[tuple[str, float]]) -> None:
    for tag, w in items:
        state.add_strength(tag, w)
