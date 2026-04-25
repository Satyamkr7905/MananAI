"""
Adaptive DSA Tutor — CLI entry point.

Main flow (unchanged from v1 at a high level, but each step is now richer):
  1. Load user state         — now EMA-tracked, Leitner-scheduled, strength-aware
  2. Select question         — ZPD scoring + scheduled reviews
  3. Show "why this question"
  4. Accept answer
  5. Evaluate answer         — partial-credit score, multi-approach
  6. Update memory           — weakness decay, strengths, Leitner boxes, EMAs
  7. Decide next step        — score-aware, fatigue-aware, schedules reviews
  8. Generate hint/feedback  — gap-analysis-driven
  9. Save user state
  10. Repeat

Run with:
    python -m app.main
    python -m app.main --user alice
    python -m app.main --topic dp
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from .agent.decision_engine import DecisionEngine
from .agent.state_manager import StateManager
from .agent.strategy import ActionType, Decision
from .interaction.evaluator import Evaluator
from .interaction.feedback import FeedbackComposer
from .interaction.hint_generator import HintGenerator
from .question_engine.question_bank import QuestionBank
from .question_engine.selector import QuestionSelector, Selection
from .utils.logger import get_logger

log = get_logger(__name__)


BANNER = r"""
========================================================
          Adaptive DSA Tutor Agent  -  MVP v2
   Type 'help' for commands, 'quit' to save & exit
========================================================
"""

HELP_TEXT = """
Commands during a question:
  (just type your approach in plain English / pseudocode)
  hint       Ask for a hint (escalates with each use).
  skip       Skip the current question (counts as wrong).
  solution   Reveal the solution and move on.
  progress   Show your learning dashboard.
  switch X   Switch to topic X (e.g. 'switch dp').
  help       Show this message.
  quit       Save progress and exit.
"""


class TutorCLI:
    def __init__(self, user_id: str, start_topic: str | None):
        self.sm = StateManager(user_id=user_id)
        self.bank = QuestionBank()
        self.selector = QuestionSelector(self.bank)
        self.evaluator = Evaluator()
        self.hinter = HintGenerator()
        self.engine = DecisionEngine()
        self.feedback = FeedbackComposer()
        self.start_topic = start_topic

    # ------------------------------------------------------------------ run loop

    def run(self) -> None:
        print(BANNER)
        if self.start_topic:
            self.sm.switch_topic(self.start_topic)

        try:
            while True:
                selection = self._select_next()
                if selection is None:
                    print("No questions available for this topic. Exiting.")
                    break

                keep_going = self._ask_and_evaluate(selection)
                self.sm.persist()
                if not keep_going:
                    break
        except (KeyboardInterrupt, EOFError):
            print("\nSaving progress...")
        finally:
            self.sm.persist()
            print("\n" + self.feedback.progress_summary(self.sm.user_state))
            print("Progress saved. Bye!")

    # ------------------------------------------------------------------ steps

    def _select_next(self) -> Selection | None:
        return self.selector.select(self.sm.user_state)

    def _ask_and_evaluate(self, selection: Selection) -> bool:
        q = selection.question
        topic_level = self.sm.user_state.topic(q["topic"]).level

        print("\n" + "=" * 60)
        print(self.feedback.why_this_question(q["topic"], topic_level, selection.reason))
        print(f"\n[{q['id']}] {q['title']}  (difficulty {q['difficulty']}/5)")
        print(q["description"])
        print("-" * 60)
        print("Describe your approach (or type 'hint' / 'solution' / 'skip' / 'quit' / 'progress').")

        hints_used = 0
        attempts_on_question = 0
        t_start = time.monotonic()
        last_result: dict[str, Any] | None = None

        while True:
            try:
                raw = input("> ").strip()
            except EOFError:
                return False
            if not raw:
                continue

            lower = raw.lower()
            if lower in ("quit", "exit"):
                return False
            if lower == "help":
                print(HELP_TEXT)
                continue
            if lower == "progress":
                print(self.feedback.progress_summary(self.sm.user_state))
                continue
            if lower.startswith("switch "):
                new_topic = lower.split(None, 1)[1]
                if new_topic in list(self.bank.topics()):
                    self.sm.switch_topic(new_topic)
                    print(f"Switched to topic '{new_topic}'. Picking a new question...")
                    return True
                print(f"Unknown topic '{new_topic}'. Known: {', '.join(self.bank.topics())}")
                continue
            if lower == "hint":
                hints_used += 1
                hint = self.hinter.generate_hint(
                    question=q,
                    user_answer="",
                    weaknesses=self.sm.user_state.top_weaknesses(3),
                    level=min(3, hints_used),
                    evaluator_result=last_result,
                    strengths=self.sm.user_state.top_strengths(3),
                )
                print(f"\nHint (level {min(3, hints_used)}): {hint}\n")
                continue
            if lower == "solution":
                print("\n" + self.feedback.show_solution(q))
                result = {"correct": False, "score": 0.0, "error_type": "unknown",
                          "notes": "Learner requested the solution.", "matched": [], "missed": []}
                self._finalize_attempt(
                    q=q, user_answer="(viewed solution)", result=result,
                    hints_used=max(hints_used, 3), elapsed=time.monotonic() - t_start,
                    decision_meta={"schedule_review": q["id"]},
                )
                return True

            skipped = lower == "skip"
            attempts_on_question += 1

            if skipped:
                result = {"correct": False, "score": 0.0, "error_type": "unknown",
                          "notes": "Skipped.", "matched": [], "missed": []}
            else:
                result = self.evaluator.evaluate(q, raw)
            last_result = result

            decision = self.engine.decide(
                state=self.sm.user_state,
                question=q,
                evaluator_result=result,
                attempts_on_question=attempts_on_question,
            )

            should_continue_question = self._apply_decision(
                decision=decision,
                q=q,
                user_answer=raw if not skipped else "(skipped)",
                result=result,
                hints_used=hints_used,
                attempts_on_question=attempts_on_question,
                t_start=t_start,
            )
            if not should_continue_question:
                return True

    # ------------------------------------------------------------------ decision dispatch

    def _apply_decision(
        self,
        *,
        decision: Decision,
        q: dict[str, Any],
        user_answer: str,
        result: dict[str, Any],
        hints_used: int,
        attempts_on_question: int,
        t_start: float,
    ) -> bool:
        action = decision.action
        elapsed = time.monotonic() - t_start

        if action in (ActionType.ASK_NEW, ActionType.LEVEL_UP):
            self._finalize_attempt(q=q, user_answer=user_answer, result=result,
                                   hints_used=hints_used, elapsed=elapsed,
                                   decision_meta=decision.meta)
            print("\n" + self.feedback.on_correct(q, hints_used, elapsed, result.get("score", 1.0)))
            if action == ActionType.LEVEL_UP:
                level = self.sm.user_state.topic(q["topic"]).level
                print(f"Level up! {q['topic']} is now level {level}/5.")
            return False

        if action == ActionType.GIVE_HINT:
            print("\n" + self.feedback.on_wrong(
                result.get("error_type"), attempts_on_question,
                score=result.get("score", 0.0), missed=result.get("missed"),
            ))
            hint = self.hinter.generate_hint(
                question=q,
                user_answer=user_answer,
                weaknesses=self.sm.user_state.top_weaknesses(3),
                level=decision.hint_level,
                evaluator_result=result,
                strengths=self.sm.user_state.top_strengths(3),
            )
            print(f"\nHint (level {decision.hint_level}): {hint}\n")
            return True

        if action == ActionType.SHOW_SOLUTION:
            print("\n" + self.feedback.on_wrong(
                result.get("error_type"), attempts_on_question,
                score=result.get("score", 0.0), missed=result.get("missed"),
            ))
            print(self.feedback.show_solution(q))
            self._finalize_attempt(q=q, user_answer=user_answer, result=result,
                                   hints_used=max(hints_used, 3), elapsed=elapsed,
                                   decision_meta=decision.meta)
            return False

        if action == ActionType.SWITCH_TOPIC:
            print("\n" + self.feedback.on_wrong(
                result.get("error_type"), attempts_on_question,
                score=result.get("score", 0.0), missed=result.get("missed"),
            ))
            print(self.feedback.show_solution(q))
            self._finalize_attempt(q=q, user_answer=user_answer, result=result,
                                   hints_used=max(hints_used, 3), elapsed=elapsed,
                                   decision_meta=decision.meta)
            if decision.next_topic:
                self.sm.switch_topic(decision.next_topic)
                print(f"\n>> {decision.reason}  New topic: {decision.next_topic}.")
            return False

        self._finalize_attempt(q=q, user_answer=user_answer, result=result,
                               hints_used=hints_used, elapsed=elapsed,
                               decision_meta=decision.meta)
        return False

    # ------------------------------------------------------------------ mutate + save

    def _finalize_attempt(
        self,
        *,
        q: dict[str, Any],
        user_answer: str,
        result: dict[str, Any],
        hints_used: int,
        elapsed: float,
        decision_meta: dict[str, Any] | None = None,
    ) -> None:
        summary = self.sm.register_attempt(
            question=q,
            user_answer=user_answer,
            evaluator_result=result,
            hints_used=hints_used,
            elapsed_seconds=elapsed,
        )
        if decision_meta:
            self.sm.apply_decision_side_effects(decision_meta)
        if summary["leveled_up"]:
            log.info("Level up event for topic %s", q["topic"])
        if summary["leveled_down"]:
            log.info("Level down event for topic %s", q["topic"])


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Adaptive DSA Tutor Agent (MVP v2)")
    p.add_argument("--user", default="default", help="User id to load/save progress under.")
    p.add_argument("--topic", default=None, help="Start on this topic (e.g. 'arrays', 'dp').")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    TutorCLI(user_id=args.user, start_topic=args.topic).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
