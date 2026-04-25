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
        """Celebrate the win, acknowledge any rough edges without nagging."""
        budget = question.get("time_budget_seconds") or 0
        if score >= 0.85:
            parts = ["Correct!"]
        else:
            parts = ["Nice — you got the main idea."]

        if hints_used == 0:
            parts.append("No hints needed.")
        elif hints_used == 1:
            parts.append("One hint was all it took.")
        else:
            parts.append(f"Got there after {hints_used} hints — keep going.")

        if budget and elapsed <= budget:
            parts.append(f"Finished in {int(elapsed)}s.")
        elif budget:
            parts.append(f"Took {int(elapsed)}s — a touch over budget.")
        return " ".join(parts)

    def on_wrong(self, error_type: str | None, attempts_on_question: int,
                 score: float = 0.0, missed: list[str] | None = None) -> str:
        """Kinder on-wrong message — never shame, always point forward."""
        if score >= 0.35:
            lead = {
                1: "Nearly there — one more piece and you've got it.",
                2: "Still close. Let's sharpen one detail.",
                3: "Getting warmer. Let's walk through the full idea.",
            }.get(attempts_on_question, "Let's fine-tune this.")
        else:
            lead = {
                1: "Not quite — but the first try rarely nails it.",
                2: "Let's try a different angle.",
                3: "Three goes in — time to see the worked solution.",
            }.get(attempts_on_question, "Let's look again together.")

        watch_out = {
            "off_by_one":           " Watch your loop bounds on this one.",
            "base_case_issue":      " Pin down the smallest input first.",
            "time_complexity_issue": " A nested-loop solution works but is slow — look for a one-pass idea.",
            "state_definition":     " Describe in plain English what each dp cell stores before coding.",
        }
        if error_type in watch_out:
            lead += watch_out[error_type]

        if missed:
            miss = missed[0]
            lead += f" Missing from your answer: {miss}."
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
