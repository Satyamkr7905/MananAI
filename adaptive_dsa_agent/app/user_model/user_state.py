"""
UserState — the agent's memory of a single learner.

v2 memory upgrades
------------------
* ``TopicSkill`` now carries an EMA of accuracy and response time so the
  agent can reason about *how reliably* the learner performs at the topic,
  not just raw correct counts.
* ``question_stats`` implements Leitner-style spaced repetition at the level
  of individual questions (``box`` and ``due_at_attempt``).
* ``strengths`` is a float-weighted counterpart to ``weaknesses`` so the
  selector can avoid over-drilling topics the learner already owns.
* ``weaknesses`` values are now floats that *decay* every time an attempt
  fires (see StateManager) so fixed weaknesses actually disappear.
* ``tag_exposure`` lets the selector prefer tags the user hasn't met recently
  (breadth).
* ``scheduled_reviews`` is a FIFO queue the selector consults before choosing
  a brand-new question.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..config import settings


_EMA_ALPHA = 0.35  # weight of newest observation in EMA updates


@dataclass
class TopicSkill:
    """Per-topic skill row — tracks both discrete level and continuous signals."""
    level: int = 0
    streak: int = 0
    wrong_streak: int = 0
    attempts: int = 0
    # EMAs. ema_accuracy is in [0, 1] — it absorbs the evaluator's partial score,
    # giving a much finer signal than win/loss alone.
    ema_accuracy: float = 0.5
    ema_response_time: float = 0.0

    def update_ema(self, score: float, seconds: float) -> None:
        self.ema_accuracy = _EMA_ALPHA * float(score) + (1 - _EMA_ALPHA) * self.ema_accuracy
        if seconds > 0:
            if self.ema_response_time == 0.0:
                self.ema_response_time = float(seconds)
            else:
                self.ema_response_time = (
                    _EMA_ALPHA * float(seconds) + (1 - _EMA_ALPHA) * self.ema_response_time
                )


@dataclass
class QuestionStat:
    """Per-question Leitner memory. Drives true spaced repetition."""
    attempts: int = 0
    correct: int = 0
    box: int = 1            # 1 = just learning, increases with each correct answer
    due_at_attempt: int = 0 # history-length index after which this qid is due again
    last_correct: bool = False


@dataclass
class AttemptRecord:
    qid: str
    topic: str
    correct: bool
    score: float
    hints_used: int
    time_seconds: float
    self_confidence: float | None
    calibration_error: float | None
    error_type: str | None
    timestamp: str


@dataclass
class UserState:
    user_id: str = "default"
    topics: dict[str, TopicSkill] = field(default_factory=dict)
    weaknesses: dict[str, float] = field(default_factory=dict)
    strengths: dict[str, float] = field(default_factory=dict)
    question_stats: dict[str, QuestionStat] = field(default_factory=dict)
    tag_exposure: dict[str, int] = field(default_factory=dict)
    history: list[AttemptRecord] = field(default_factory=list)
    recent_qids: list[str] = field(default_factory=list)
    scheduled_reviews: list[str] = field(default_factory=list)
    avg_response_time: float = 0.0
    confidence: float = 0.5
    confidence_ema: float = 0.5
    calibration_mae: float = 0.0
    current_topic: str | None = None

    # ---------------- convenience getters ----------------

    def topic(self, name: str) -> TopicSkill:
        if name not in self.topics:
            self.topics[name] = TopicSkill()
        return self.topics[name]

    def qstat(self, qid: str) -> QuestionStat:
        if qid not in self.question_stats:
            self.question_stats[qid] = QuestionStat()
        return self.question_stats[qid]

    def push_recent(self, qid: str) -> None:
        if qid in self.recent_qids:
            self.recent_qids.remove(qid)
        self.recent_qids.append(qid)
        window = settings.recent_question_window
        if len(self.recent_qids) > window:
            self.recent_qids = self.recent_qids[-window:]

    # ---------------- mutations ----------------

    def record_attempt(
        self,
        qid: str,
        topic: str,
        correct: bool,
        score: float,
        hints_used: int,
        time_seconds: float,
        self_confidence: float | None,
        error_type: str | None,
        question_tags: Iterable[str] = (),
    ) -> AttemptRecord:
        """Append an attempt and run all the memory-level bookkeeping."""
        conf_norm: float | None = None
        if self_confidence is not None:
            conf_norm = max(0.0, min(1.0, float(self_confidence)))
        calibration_error = abs((conf_norm or 0.0) - float(score)) if conf_norm is not None else None
        rec = AttemptRecord(
            qid=qid,
            topic=topic,
            correct=correct,
            score=float(score),
            hints_used=hints_used,
            time_seconds=float(time_seconds),
            self_confidence=conf_norm,
            calibration_error=calibration_error,
            error_type=error_type,
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self.history.append(rec)
        self.push_recent(qid)

        # Running averages ----------------------------------------------------
        n = len(self.history)
        self.avg_response_time = ((self.avg_response_time * (n - 1)) + rec.time_seconds) / n
        trow = self.topic(topic)
        trow.attempts += 1
        trow.update_ema(score=rec.score, seconds=rec.time_seconds)
        if rec.self_confidence is not None:
            if trow.attempts <= 1:
                self.confidence_ema = rec.self_confidence
            else:
                self.confidence_ema = (
                    _EMA_ALPHA * rec.self_confidence + (1 - _EMA_ALPHA) * self.confidence_ema
                )
            self.confidence = self.confidence_ema
            seen_cal = [h.calibration_error for h in self.history if h.calibration_error is not None]
            if seen_cal:
                self.calibration_mae = float(sum(seen_cal) / len(seen_cal))

        # Per-question Leitner memory ----------------------------------------
        qs = self.qstat(qid)
        qs.attempts += 1
        qs.last_correct = bool(correct)
        if correct:
            qs.correct += 1
            qs.box = min(5, qs.box + 1)
        else:
            qs.box = 1  # failure resets the learning cycle
        # Next review is scheduled in exponentially-growing gaps per box.
        gap = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}.get(qs.box, 1)
        qs.due_at_attempt = n + gap

        # Tag exposure -------------------------------------------------------
        for t in question_tags:
            self.tag_exposure[t] = self.tag_exposure.get(t, 0) + 1

        return rec

    # --- weakness / strength helpers ---

    def add_weakness(self, tag: str | None, weight: float = 1.0) -> None:
        if not tag:
            return
        self.weaknesses[tag] = self.weaknesses.get(tag, 0.0) + float(weight)

    def add_strength(self, tag: str | None, weight: float = 1.0) -> None:
        if not tag:
            return
        self.strengths[tag] = self.strengths.get(tag, 0.0) + float(weight)

    def decay_weaknesses(self, factor: float = 0.92) -> None:
        """Slowly fade weaknesses so fixed-and-forgotten ones disappear.

        Anything below 0.1 is removed outright to keep the dict small.
        """
        for k in list(self.weaknesses):
            self.weaknesses[k] *= factor
            if self.weaknesses[k] < 0.1:
                del self.weaknesses[k]

    def top_weaknesses(self, k: int = 3) -> list[str]:
        return [w for w, _ in sorted(self.weaknesses.items(), key=lambda kv: -kv[1])[:k]]

    def top_strengths(self, k: int = 3) -> list[str]:
        return [s for s, _ in sorted(self.strengths.items(), key=lambda kv: -kv[1])[:k]]

    def schedule_review(self, qid: str) -> None:
        """Push a question to the review queue (e.g. after a SHOW_SOLUTION)."""
        if qid and qid not in self.scheduled_reviews:
            self.scheduled_reviews.append(qid)

    def pop_review(self) -> str | None:
        return self.scheduled_reviews.pop(0) if self.scheduled_reviews else None

    def due_for_review_qids(self) -> list[str]:
        """Questions whose Leitner cool-down has elapsed — ordered by how overdue."""
        n = len(self.history)
        due = [
            (n - qs.due_at_attempt, qid)
            for qid, qs in self.question_stats.items()
            if qs.due_at_attempt <= n and not qs.last_correct
        ]
        due.sort(reverse=True)  # most overdue first
        return [qid for _, qid in due]

    def attempts_since(self, qid: str) -> int:
        last_idx = -1
        for i, rec in enumerate(self.history):
            if rec.qid == qid:
                last_idx = i
        if last_idx == -1:
            return 10**6
        return len(self.history) - 1 - last_idx

    # ---------------- serialization ----------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "topics": {k: asdict(v) for k, v in self.topics.items()},
            "weaknesses": dict(self.weaknesses),
            "strengths": dict(self.strengths),
            "question_stats": {k: asdict(v) for k, v in self.question_stats.items()},
            "tag_exposure": dict(self.tag_exposure),
            "history": [asdict(h) for h in self.history],
            "recent_qids": list(self.recent_qids),
            "scheduled_reviews": list(self.scheduled_reviews),
            "avg_response_time": self.avg_response_time,
            "confidence": self.confidence,
            "confidence_ema": self.confidence_ema,
            "calibration_mae": self.calibration_mae,
            "current_topic": self.current_topic,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserState":
        topics = {k: TopicSkill(**v) for k, v in (data.get("topics") or {}).items()}
        qstats = {k: QuestionStat(**v) for k, v in (data.get("question_stats") or {}).items()}
        # History rows may predate the ``score`` field; default gracefully.
        history = []
        for h in data.get("history") or []:
            if "score" not in h:
                h = {**h, "score": 1.0 if h.get("correct") else 0.0}
            if "self_confidence" not in h:
                h = {**h, "self_confidence": None}
            if "calibration_error" not in h:
                h = {**h, "calibration_error": None}
            history.append(AttemptRecord(**h))
        return cls(
            user_id=data.get("user_id", "default"),
            topics=topics,
            weaknesses={k: float(v) for k, v in (data.get("weaknesses") or {}).items()},
            strengths={k: float(v) for k, v in (data.get("strengths") or {}).items()},
            question_stats=qstats,
            tag_exposure=dict(data.get("tag_exposure") or {}),
            history=history,
            recent_qids=list(data.get("recent_qids") or []),
            scheduled_reviews=list(data.get("scheduled_reviews") or []),
            avg_response_time=float(data.get("avg_response_time", 0.0)),
            confidence=float(data.get("confidence", 0.5)),
            confidence_ema=float(data.get("confidence_ema", data.get("confidence", 0.5))),
            calibration_mae=float(data.get("calibration_mae", 0.0)),
            current_topic=data.get("current_topic"),
        )


# ---------------------------------------------------------------------------
# Storage helpers (JSON file keyed by user_id)
# ---------------------------------------------------------------------------

def load_user_state(user_id: str = "default", path: Path | None = None) -> UserState:
    path = path or settings.user_progress_path
    if not path.exists():
        return UserState(user_id=user_id)
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError:
        raw = {}
    users = raw if isinstance(raw, dict) else {}
    if user_id in users:
        return UserState.from_dict(users[user_id])
    return UserState(user_id=user_id)


def save_user_state(state: UserState, path: Path | None = None) -> None:
    path = path or settings.user_progress_path
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "{}") if path.exists() else {}
    except json.JSONDecodeError:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    raw[state.user_id] = state.to_dict()
    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")


def list_recent_qids(state: UserState) -> Iterable[str]:
    return state.recent_qids
