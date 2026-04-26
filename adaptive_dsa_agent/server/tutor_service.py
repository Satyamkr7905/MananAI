# Bridges HTTP routes to QuestionBank, selector, evaluator, hints, StateManager.

from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy.orm import Session

from app.agent.decision_engine import DecisionEngine
from app.agent.state_manager import StateManager
from app.interaction.evaluator import Evaluator
from app.interaction.hint_generator import HintGenerator
from app.question_engine.question_bank import QuestionBank
from app.question_engine.selector import QuestionSelector
from app.user_model.user_state import UserState

from .models import User, UserBehaviorEvent, UserLearningState
from .stats_builder import merge_solved_lists


def _strip_question(q: dict[str, Any], reason: str | None) -> dict[str, Any]:
    out = {k: v for k, v in q.items() if k != "solution"}
    if reason:
        out["reason"] = reason
    return out


def _load_state(row: UserLearningState, user: User) -> UserState:
    try:
        raw = json.loads(row.tutor_state_json or "{}")
    except json.JSONDecodeError:
        raw = {}
    if not raw:
        return UserState(user_id=user.id)
    st = UserState.from_dict(raw)
    st.user_id = user.id
    return st


def _solved_list(row: UserLearningState) -> list[str]:
    try:
        data = json.loads(row.solved_first_try_json or "[]")
        return list(data) if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _confidence_to_unit_scale(self_confidence: int | float | None) -> float | None:
    if self_confidence is None:
        return None
    raw = float(self_confidence)
    if raw > 1.0:
        raw = raw / 100.0
    return max(0.0, min(1.0, raw))


def _calibration_band(error: float) -> str:
    if error <= 0.15:
        return "well_calibrated"
    if error <= 0.35:
        return "slightly_miscalibrated"
    return "poorly_calibrated"


def _is_interview_mode(mode: str | None) -> bool:
    return (mode or "").strip().lower() == "interview"


class TutorRuntime:
    # process-global bank + selector (read-only). hints are stateless per request.

    def __init__(self) -> None:
        self.bank = QuestionBank()
        self.selector = QuestionSelector(self.bank)
        self.engine = DecisionEngine()
        self.evaluator = Evaluator()
        self.hinter = HintGenerator()

    def topics_for_api(self) -> list[dict[str, Any]]:
        by_key: dict[str, int] = {}
        for q in self.bank.all():
            t = q.get("topic", "")
            by_key[t] = by_key.get(t, 0) + 1
        labels = {
            "arrays": "Arrays",
            "dp": "Dynamic Programming",
            "graphs": "Graphs",
            "trees": "Trees",
            "strings": "Strings",
        }
        return [{"key": k, "label": labels.get(k, k), "count": c} for k, c in sorted(by_key.items())]

    def next_question(
        self,
        db: Session,
        user: User,
        *,
        topic: str | None,
        difficulty: str | None,
        exclude_ids: list[str] | None,
        mode: str | None = None,
    ) -> dict[str, Any] | None:
        row = db.get(UserLearningState, user.id)
        if row is None:
            return None
        state = _load_state(row, user)
        solved = _solved_list(row)
        ex = merge_solved_lists(solved, exclude_ids)

        fd: int | None = None
        if difficulty not in (None, "", "all"):
            try:
                fd = int(difficulty)
            except ValueError:
                fd = None
        if _is_interview_mode(mode) and fd is None:
            # Interview rounds default to medium if no explicit level is requested.
            fd = 3

        req_topic = (topic or "all").strip() or "all"
        sel = self.selector.select(state, req_topic, exclude_ids=ex, fixed_difficulty=fd)
        if sel is None:
            return None

        row.current_qid = sel.question["id"]
        row.attempts_on_current = 0
        db.add(row)
        db.commit()

        reason = None if _is_interview_mode(mode) else sel.reason
        out = _strip_question(sel.question, reason)
        if _is_interview_mode(mode):
            out["mode"] = "interview"
            out["interviewPrompt"] = "Explain approach, complexity, and edge cases."
        return out

    def submit(
        self,
        db: Session,
        user: User,
        *,
        question_id: str,
        answer: str,
        hints_used: int,
        self_confidence: int | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        row = db.get(UserLearningState, user.id)
        if row is None:
            raise ValueError("learning row missing")
        q = self.bank.get(question_id)
        if q is None:
            raise ValueError("unknown question")

        state = _load_state(row, user)

        def persist(s: UserState) -> None:
            row.tutor_state_json = json.dumps(s.to_dict())
            db.add(row)

        sm = StateManager(user.id, initial_state=state, persist_callback=persist)

        if row.current_qid != question_id:
            row.current_qid = question_id
            row.attempts_on_current = 1
        else:
            row.attempts_on_current = int(row.attempts_on_current or 0) + 1
        attempts_on_q = int(row.attempts_on_current)

        t0 = time.perf_counter()
        eval_result = self.evaluator.evaluate(q, answer or "")
        interview_mode = _is_interview_mode(mode)
        if interview_mode:
            # Interview mode is deliberately stricter than practice mode.
            interview_correct = float(eval_result.get("score", 0.0)) >= 0.70
            eval_result = {**eval_result, "correct": interview_correct}
        elapsed = time.perf_counter() - t0
        confidence_norm = _confidence_to_unit_scale(self_confidence)
        effective_hints_used = 0 if interview_mode else int(hints_used)

        sm.register_attempt(
            question=q,
            user_answer=answer or "",
            evaluator_result=eval_result,
            hints_used=effective_hints_used,
            elapsed_seconds=elapsed,
            self_confidence=confidence_norm,
        )
        decision = self.engine.decide(
            state=sm.state,
            question=q,
            evaluator_result=eval_result,
            attempts_on_question=attempts_on_q,
        )
        sm.apply_decision_side_effects(decision.meta or {})
        sm.persist()

        solved = _solved_list(row)
        correct = bool(eval_result.get("correct"))
        if correct and attempts_on_q == 1 and effective_hints_used == 0 and question_id not in solved:
            solved.append(question_id)
            row.solved_first_try_json = json.dumps(solved)

        db.add(
            UserBehaviorEvent(
                user_id=user.id,
                event_type="submit_answer",
                payload_json=json.dumps(
                    {
                        "questionId": question_id,
                        "correct": bool(eval_result.get("correct")),
                        "score": eval_result.get("score"),
                        "error_type": eval_result.get("error_type"),
                        "hintsUsed": effective_hints_used,
                        "mode": "interview" if interview_mode else "practice",
                        "attemptsOnQuestion": attempts_on_q,
                        "selfConfidence": confidence_norm,
                        "calibrationError": (
                            abs(confidence_norm - float(eval_result.get("score", 0.0)))
                            if confidence_norm is not None
                            else None
                        ),
                    }
                ),
            )
        )
        db.add(row)
        db.commit()

        calibration: dict[str, Any] | None = None
        if confidence_norm is not None:
            calib_err = abs(confidence_norm - float(eval_result.get("score", 0.0)))
            calibration = {
                "selfConfidence": round(confidence_norm, 3),
                "error": round(calib_err, 3),
                "band": _calibration_band(calib_err),
                "runningMae": round(float(sm.state.calibration_mae), 3),
            }

        counterfactual: str | None = None
        if float(eval_result.get("score", 0.0)) >= float(self.evaluator.close_threshold):
            counterfactual = self.hinter.generate_counterfactual(q, eval_result)

        return {
            **eval_result,
            "questionId": question_id,
            "calibration": calibration,
            "counterfactual": counterfactual,
            "mode": "interview" if interview_mode else "practice",
        }

    def hint(
        self,
        db: Session,
        user: User,
        question_id: str,
        level: int,
        last_answer: str = "",
        mode: str | None = None,
    ) -> str:
        if _is_interview_mode(mode):
            raise ValueError("Hints are disabled in interview mode.")
        row = db.get(UserLearningState, user.id)
        state = _load_state(row, user) if row else UserState(user_id=user.id)
        q = self.bank.get(question_id)
        if q is None:
            raise ValueError("unknown question")
        weak = state.top_weaknesses(5)
        strong = state.top_strengths(5)
        return self.hinter.generate_hint(
            q,
            last_answer or "",
            weak,
            level,
            evaluator_result=None,
            strengths=strong,
        )


_tutor: TutorRuntime | None = None


def get_tutor() -> TutorRuntime:
    # lazy singleton — don't load questions.json + tutor stack at import time,
    # keeps uvicorn cold-start fast.
    global _tutor
    if _tutor is None:
        _tutor = TutorRuntime()
    return _tutor
