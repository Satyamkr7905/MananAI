# Tutor API (auth'd) — stats, questions, submit, hints, history.

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.user_model.user_state import UserState

from .database import get_session
from .deps import ensure_learning_row, get_current_user
from .models import User, UserBehaviorEvent, UserLearningState
from .stats_builder import build_analytics, build_stats, history_payload
from .tutor_service import get_tutor

router = APIRouter(tags=["tutor"])


@router.get("/user/stats")
def user_stats(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    ensure_learning_row(db, user)
    row = db.get(UserLearningState, user.id)
    raw = row.tutor_state_json if row else "{}"
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        data = {}
    state = UserState.from_dict(data) if data else UserState(user_id=user.id)
    state.user_id = user.id
    total_questions = len(get_tutor().bank.all())
    return build_stats(state, total_questions=total_questions)


@router.get("/user/improvement")
def user_improvement(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    limit: int = 100,
):
    # recent behaviour events + a small summary for server-backed accounts.
    n = max(1, min(200, int(limit)))
    rows = (
        db.query(UserBehaviorEvent)
        .filter(UserBehaviorEvent.user_id == user.id)
        .order_by(UserBehaviorEvent.created_at.desc())
        .limit(n)
        .all()
    )
    events = []
    for r in rows:
        try:
            payload = json.loads(r.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        events.append(
            {
                "id": r.id,
                "type": r.event_type,
                "at": r.created_at.isoformat() if r.created_at else None,
                "payload": payload,
            }
        )
    # summary: accuracy across the submit_answer events in this page.
    submits = [e for e in events if e["type"] == "submit_answer" and e.get("payload")]
    total = len(submits)
    correct_n = sum(1 for e in submits if e["payload"].get("correct") is True)
    summary = {
        "attemptsInWindow": total,
        "correctInWindow": correct_n,
        "accuracyInWindow": (correct_n / total) if total else None,
    }
    return {"events": events, "summary": summary}


@router.get("/user/progress")
def user_progress(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    ensure_learning_row(db, user)
    row = db.get(UserLearningState, user.id)
    if row is None:
        return {"history": [], "solvedFirstTryNoHint": []}
    try:
        data = json.loads(row.tutor_state_json or "{}")
    except json.JSONDecodeError:
        data = {}
    state = UserState.from_dict(data) if data else UserState(user_id=user.id)
    bank = {q["id"]: q for q in get_tutor().bank.all()}
    out = history_payload(state, bank)
    try:
        mastered = json.loads(row.solved_first_try_json or "[]")
        out["solvedFirstTryNoHint"] = list(mastered) if isinstance(mastered, list) else out["solvedFirstTryNoHint"]
    except json.JSONDecodeError:
        pass
    return out


@router.get("/topics")
def topics(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    ensure_learning_row(db, user)
    row = db.get(UserLearningState, user.id)
    solved_ids: set[str] = set()
    if row is not None:
        try:
            data = json.loads(row.tutor_state_json or "{}")
        except json.JSONDecodeError:
            data = {}
        state = UserState.from_dict(data) if data else UserState(user_id=user.id)
        solved_ids = {h.qid for h in state.history if h.correct}
    return get_tutor().topics_for_api(solved_ids=solved_ids)


@router.get("/questions/next")
def next_question(
    topic: str | None = None,
    difficulty: str | None = None,
    excludeIds: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    ensure_learning_row(db, user)
    ex = [x.strip() for x in excludeIds.split(",") if x.strip()] if excludeIds else []
    q = get_tutor().next_question(db, user, topic=topic, difficulty=difficulty, exclude_ids=ex, mode=mode)
    if q is None:
        return None
    return q


class SubmitBody(BaseModel):
    questionId: str
    answer: str = ""
    hintsUsed: int = Field(0, ge=0)
    selfConfidence: int | None = Field(default=None, ge=0, le=100)
    mode: str | None = None


@router.post("/submit-answer")
def submit_answer(
    body: SubmitBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    ensure_learning_row(db, user)
    try:
        return get_tutor().submit(
            db,
            user,
            question_id=body.questionId,
            answer=body.answer,
            hints_used=body.hintsUsed,
            self_confidence=body.selfConfidence,
            mode=body.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/analytics")
def analytics(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    ensure_learning_row(db, user)
    row = db.get(UserLearningState, user.id)
    try:
        data = json.loads(row.tutor_state_json or "{}") if row else {}
    except json.JSONDecodeError:
        data = {}
    state = UserState.from_dict(data) if data else UserState(user_id=user.id)
    return build_analytics(state)


@router.get("/questions/{question_id}/hint")
def question_hint(
    question_id: str,
    level: int = 1,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    ensure_learning_row(db, user)
    try:
        text = get_tutor().hint(db, user, question_id, level, mode=mode)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    lv = max(1, min(3, int(level)))
    return {"level": lv, "text": text}
