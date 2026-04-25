"""
Feedback composer — user-facing messages.

v2 upgrades
-----------
* ``on_correct`` / ``on_wrong`` speak in terms of the partial-credit score,
  so a 50% attempt gets different language from a 10% attempt.
* The progress dashboard now surfaces EMA accuracy, response time, strengths
  and scheduled reviews — the richer memory from v2 is visible to the user.
"""

from __future__ import annotations

from typing import Any

from ..config import settings
from ..user_model.user_state import UserState


class FeedbackComposer:

    # ---------------- per-attempt feedback ----------------

    def on_correct(self, question: dict[str, Any], hints_used: int, elapsed: float,
                   score: float = 1.0) -> str:
        budget = question.get("time_budget_seconds") or 0
        parts = ["Correct!"]
        if score < 0.9:
            parts.append(f"(score {score:.0%} — just over the line)")
        if hints_used == 0:
            parts.append("Nailed it with no hints.")
        elif hints_used == 1:
            parts.append("One hint was all you needed — nice recovery.")
        else:
            parts.append(f"Got there after {hints_used} hints — progress!")
        if budget and elapsed <= budget:
            parts.append(f"Finished in {int(elapsed)}s (budget {budget}s).")
        elif budget:
            parts.append(
                f"Took {int(elapsed)}s vs. a {budget}s budget — try to tighten your approach."
            )
        return " ".join(parts)

    def on_wrong(self, error_type: str | None, attempts_on_question: int,
                 score: float = 0.0, missed: list[str] | None = None) -> str:
        if score >= 0.4:
            lead = {
                1: f"So close ({score:.0%}) — let's sharpen it.",
                2: f"Still a little off ({score:.0%}) — closer this time.",
                3: f"Three tries at {score:.0%}. Time to walk through the solution.",
            }.get(attempts_on_question, "Let's take another look.")
        else:
            lead = {
                1: "Not quite — but you're on the hook now.",
                2: "Still off. Let's go deeper.",
                3: "Three misses — time to see the full solution.",
            }.get(attempts_on_question, "Let's take another look.")
        if error_type and error_type not in ("unknown", "logic", None):
            lead += f" Smells like a **{error_type.replace('_', ' ')}** issue."
        if missed:
            lead += f" Your answer didn't touch: {', '.join(missed[:2])}."
        return lead

    # ---------------- summaries ----------------

    def progress_summary(self, state: UserState) -> str:
        """Richer text dashboard: levels, EMA, streaks, weaknesses, strengths, reviews."""
        lines: list[str] = []
        lines.append("---------- Learning Progress ----------")
        if not state.topics:
            lines.append("(no attempts yet)")
        else:
            for name, row in sorted(state.topics.items()):
                bar = self._level_bar(row.level)
                lines.append(
                    f"  {name:<8} lvl {row.level}/{settings.max_skill_level} {bar}  "
                    f"acc={row.ema_accuracy:.0%}  "
                    f"streak=+{row.streak}/-{row.wrong_streak}  "
                    f"n={row.attempts}  "
                    f"avg={row.ema_response_time:.0f}s"
                )

        lines.append("")
        top_w = [(t, state.weaknesses[t]) for t in state.top_weaknesses(3)]
        lines.append(
            "Weaknesses : "
            + (", ".join(f"{t}({w:.1f})" for t, w in top_w) if top_w else "none detected")
        )
        top_s = [(t, state.strengths[t]) for t in state.top_strengths(3)]
        lines.append(
            "Strengths  : "
            + (", ".join(f"{t}({w:.1f})" for t, w in top_s) if top_s else "none yet")
        )

        if state.scheduled_reviews:
            lines.append(f"Scheduled reviews: {len(state.scheduled_reviews)} queued")

        recent = state.history[-5:]
        if recent:
            correct = sum(1 for r in recent if r.correct)
            avg_score = sum(r.score for r in recent) / len(recent)
            lines.append(
                f"Last {len(recent)} attempts: {correct}/{len(recent)} correct  "
                f"avg partial-credit {avg_score:.0%}"
            )
        lines.append(f"Confidence : {state.confidence:.2f}")
        lines.append("---------------------------------------")
        return "\n".join(lines)

    def why_this_question(self, topic: str, level: int, reason: str) -> str:
        return (
            f"Topic: {topic.capitalize()} (Level {level})\n"
            f"Why this question: {reason}"
        )

    def show_solution(self, question: dict[str, Any]) -> str:
        return (
            "Solution outline:\n  "
            + question.get("solution", "(no solution text available)")
        )

    # ---------------- internal ----------------

    @staticmethod
    def _level_bar(level: int) -> str:
        filled = "#" * level
        empty = "." * (settings.max_skill_level - level)
        return f"[{filled}{empty}]"
