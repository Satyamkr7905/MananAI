"""
Question selector — picks the next question for a given learner.

v2 scoring model
----------------
Candidates are filtered to the target topic; each candidate accumulates:

    score = topic_match_boost
          + zpd_bonus            (peaks when predicted_success ≈ 0.75)
          + weakness_boost  * sum(weakness_strength for tag in q.tags)
          + breadth_bonus        (favors tags the learner hasn't seen recently)
          + leitner_bonus        (strong — honors due spaced-repetition reviews)
          - strength_penalty     (gentle — avoids over-drilling mastered tags)
          - recent_penalty       (if asked in the last N attempts)
          - difficulty_mismatch_penalty (when way outside target window)

Before scoring, the selector honors two strong priors:

1. ``state.scheduled_reviews`` (engine-pushed): pop the oldest qid and return
   it if it matches the current topic.
2. ``state.due_for_review_qids()`` (Leitner): if any due-for-review question
   in the current topic, prefer it.

The selector also produces a human-readable ``reason`` string so the CLI can
answer "why this question?" without fabricating anything.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from ..config import settings
from ..user_model.skill_tracker import recommend_difficulty
from ..user_model.user_state import UserState
from ..utils.logger import get_logger
from .difficulty_manager import predicted_success, target_window
from .question_bank import QuestionBank

log = get_logger(__name__)


# New scoring constants — kept here (not config) because they're truly about
# scoring geometry, not user-tunable thresholds.
_BREADTH_BOOST = 0.8
_LEITNER_BOOST = 3.5
_STRENGTH_PENALTY = 0.8
_DIFFICULTY_FAR_PENALTY = 1.5


@dataclass
class Selection:
    question: dict[str, Any]
    reason: str
    target_difficulty: float


class QuestionSelector:
    def __init__(self, bank: QuestionBank, rng: random.Random | None = None):
        self.bank = bank
        self.rng = rng or random.Random()

    # ------------------------------------------------------------------ public

    def select(
        self,
        state: UserState,
        topic: str | None = None,
        *,
        exclude_ids: Iterable[str] | None = None,
        fixed_difficulty: int | None = None,
    ) -> Selection | None:
        """Pick the next question.

        * ``exclude_ids`` — mastered / client-supplied IDs to skip (e.g. first-try no-hint).
        * ``fixed_difficulty`` — when set (1–5), only questions with this difficulty.
        * ``topic`` of ``\"all\"`` — search across topics (shuffled order).
        * ``topic`` omitted (``None`` / ``\"\"``) — use ``state.current_topic`` or the
          bank default (CLI / tests); only the literal ``\"all\"`` scans every topic.
        """
        ex = set(exclude_ids or ())
        if topic == "all":
            tops = list(self.bank.topics())
            if not tops:
                return None
            self.rng.shuffle(tops)
            for t in tops:
                sel = self._select_for_topic(state, t, ex, fixed_difficulty)
                if sel is not None:
                    return sel
            return None

        effective = topic if topic not in (None, "") else (state.current_topic or self._default_topic(state))
        if effective is None:
            return None
        return self._select_for_topic(state, effective, ex, fixed_difficulty)

    def _select_for_topic(
        self,
        state: UserState,
        topic: str,
        ex: set[str],
        fixed_difficulty: int | None,
    ) -> Selection | None:
        topic = topic or state.current_topic or self._default_topic(state)
        if topic is None:
            return None

        # ---- Priority 1: engine-scheduled review, if it belongs to this topic.
        forced = self._pop_scheduled_review(state, topic, ex)
        if forced is not None:
            target = recommend_difficulty(state, topic)
            return Selection(
                question=forced,
                reason=(
                    "Scheduled review — revisiting a question you previously missed so the "
                    "correction sticks (spaced repetition)."
                ),
                target_difficulty=target,
            )

        # ---- Priority 2: a Leitner-due previously-missed question in this topic.
        due = self._leitner_due_question(state, topic, ex)
        if due is not None:
            target = recommend_difficulty(state, topic)
            return Selection(
                question=due,
                reason=(
                    f"Leitner review — you missed this one before and it's time to retry "
                    f"(difficulty {due['difficulty']}/5)."
                ),
                target_difficulty=target,
            )

        # ---- Default path: ZPD-scored pick.
        target = recommend_difficulty(state, topic)
        lo, hi = target_window(target, spread=1.0)
        candidates = self.bank.by_topic_and_difficulty_range(topic, lo, hi)
        if not candidates:
            candidates = self.bank.by_topic(topic)
        candidates = self._apply_filters(candidates, ex, fixed_difficulty)
        if not candidates:
            log.warning("No questions for topic '%s' after filters", topic)
            return None

        scored = [(self._score(q, state, target), q) for q in candidates]
        scored.sort(key=lambda p: p[0], reverse=True)

        # Tiny jitter among the top-scoring candidates keeps sessions fresh.
        top_score = scored[0][0]
        top = [q for s, q in scored if s >= top_score - 0.05]
        chosen = self.rng.choice(top)

        reason = self._explain(chosen, state, target)
        return Selection(question=chosen, reason=reason, target_difficulty=target)

    @staticmethod
    def _apply_filters(
        candidates: list[dict[str, Any]],
        ex: set[str],
        fixed_difficulty: int | None,
    ) -> list[dict[str, Any]]:
        out = [q for q in candidates if q.get("id") not in ex]
        if fixed_difficulty is not None:
            fd = int(fixed_difficulty)
            out = [q for q in out if int(q.get("difficulty", 0)) == fd]
        return out

    # ------------------------------------------------------------------ priority lanes

    def _pop_scheduled_review(
        self, state: UserState, topic: str, ex: set[str]
    ) -> dict[str, Any] | None:
        """Pop the oldest engine-scheduled review that still matches this topic."""
        # We don't destructively pop until we're sure it's a topic match.
        for i, qid in enumerate(list(state.scheduled_reviews)):
            if qid in ex:
                continue
            q = self.bank.get(qid)
            if q and q.get("topic") == topic and qid not in state.recent_qids:
                state.scheduled_reviews.pop(i)
                return q
        return None

    def _leitner_due_question(self, state: UserState, topic: str, ex: set[str]) -> dict[str, Any] | None:
        for qid in state.due_for_review_qids():
            if qid in ex or qid in state.recent_qids:
                continue
            q = self.bank.get(qid)
            if q and q.get("topic") == topic:
                return q
        return None

    # ------------------------------------------------------------------ scoring

    def _score(self, q: dict[str, Any], state: UserState, target: float) -> float:
        score = 0.0
        score += settings.topic_match_boost

        # ZPD sweet-spot. Convert predicted-success into a Gaussian-ish bonus
        # peaking at 0.75 success.
        p = predicted_success(target, int(q["difficulty"]))
        zpd = 1.0 - min(1.0, abs(p - 0.75) / 0.5)        # 1.0 at p=0.75, 0.0 at p=0.25 or p=1.25
        score += settings.difficulty_match_boost * zpd

        # Weakness boost — now summing *float* weights, so 3.2 hurts more than 1.0.
        tags = set(q.get("tags") or [])
        for tag in tags:
            if tag in state.weaknesses:
                score += settings.weakness_boost * min(3.0, state.weaknesses[tag])

        # Breadth bonus: prefer tags the learner hasn't seen often.
        exposures = [state.tag_exposure.get(t, 0) for t in tags] or [0]
        breadth = 1.0 / (1.0 + min(exposures)) if exposures else 0.0
        score += _BREADTH_BOOST * breadth

        # Strength penalty: gentle — discourage over-drilling mastered tags.
        for tag in tags:
            if tag in state.strengths and state.strengths[tag] >= 2.0:
                score -= _STRENGTH_PENALTY

        # Recency and severe-mismatch penalties.
        if q["id"] in state.recent_qids:
            score -= settings.recent_penalty
        if abs(int(q["difficulty"]) - target) > 1.5:
            score -= _DIFFICULTY_FAR_PENALTY

        return score

    # ------------------------------------------------------------------ helpers

    def _default_topic(self, state: UserState) -> str | None:
        """Pick a reasonable starting topic: the learner's weakest, else the first."""
        topics = list(self.bank.topics())
        if not topics:
            return None
        if state.topics:
            return min(state.topics, key=lambda t: state.topic(t).level)
        return topics[0]

    def _explain(self, q: dict[str, Any], state: UserState, target: float) -> str:
        """Build the "why this question?" rationale — honest about our reasoning."""
        reasons: list[str] = []
        tags = set(q.get("tags") or [])

        overlap = [w for w in state.weaknesses if w in tags]
        if overlap:
            reasons.append(f"targets your weak spot(s): {', '.join(sorted(overlap))}")

        exposures = [state.tag_exposure.get(t, 0) for t in tags] or [0]
        if exposures and min(exposures) == 0:
            reasons.append("introduces a pattern you haven't practiced yet")

        p = predicted_success(target, int(q["difficulty"]))
        if 0.6 <= p <= 0.85:
            reasons.append(
                f"sits in your learning zone (~{int(p*100)}% predicted success, difficulty {q['difficulty']}/5)"
            )
        elif p > 0.85:
            reasons.append(f"a quick confidence-builder (~{int(p*100)}% predicted success)")
        else:
            reasons.append(
                f"a deliberate stretch — only ~{int(p*100)}% predicted success — to grow the ceiling"
            )

        mastered = [t for t in tags if t in state.strengths and state.strengths[t] >= 2.0]
        if mastered and len(overlap) == 0:
            reasons.append(f"also reinforces your strength in {', '.join(sorted(mastered))}")

        if not reasons:
            reasons.append(f"a fresh {q['topic']} problem at difficulty {q['difficulty']}/5")
        return "; ".join(reasons) + "."
