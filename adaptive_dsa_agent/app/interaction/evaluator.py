"""
Evaluator — decides how correct a free-text answer is.

v2 upgrades
-----------
* **Partial-credit scoring**: returns a float ``score`` in ``[0, 1]`` alongside
  the legacy ``correct`` boolean. The decision engine uses ``score`` to pick a
  smarter hint level ("you're close, here's a targeted nudge" vs. "back to
  basics").
* **Multi-approach support**: a question can declare alternative
  ``approaches`` (e.g. Two Sum via hash map OR sort+two-pointer). We compute
  a score per approach and take the best — so the learner isn't punished for
  choosing a different valid technique.
* **Weighted keywords**: ``core_keywords`` are mandatory and weigh 2.0;
  ``expected_keywords`` are supporting and weigh 1.0.
* **Token-aware matching**: words are extracted after light normalization,
  so ``"Two-pointer"`` matches ``"two pointer"``.
* **Smarter error_type inference**: looks at *how* the answer went wrong
  (brute-force markers, recursion markers, etc).

Output shape (backward-compatible + new fields):

    {
      "correct":    bool,       # True iff score >= correct_threshold
      "score":      float,      # 0..1 partial credit
      "error_type": str | None, # off_by_one | base_case_issue | time_complexity_issue | logic | unknown | null
      "matched":    [str],      # keywords/phrases found in the answer
      "missed":     [str],      # keywords expected but absent
      "approach":   str | None, # which approach fit best, if multi-approach question
      "notes":      str,
    }
"""

from __future__ import annotations

import re
from typing import Any, Iterable


CORRECT_THRESHOLD = 0.65   # score ≥ this → "correct"
CLOSE_THRESHOLD = 0.40     # score ≥ this → "close" (hint more targeted)


_GIVE_UP_PATTERNS = (
    r"\bi\s*don'?t\s*know\b",
    r"\bidk\b",
    r"\bno\s*idea\b",
    r"^\s*skip\s*$",
    r"^\s*pass\s*$",
    r"\bgive\s*up\b",
)

_ERROR_SIGNATURES: list[tuple[str, str]] = [
    (r"\b(off[-\s]?by[-\s]?one|boundary|index\s*out|i\s*[-+]\s*1)\b", "off_by_one"),
    (r"\b(base\s*case|infinite\s*recursion|stack\s*overflow)\b", "base_case_issue"),
    (r"\b(brute\s*force|two\s*nested\s*loops|nested\s*for|o\(n\^?2\))\b", "time_complexity_issue"),
    (r"\b(null|none\s*type|undefined)\b", "logic"),
]

_WORD_NORMALIZE = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    return _WORD_NORMALIZE.sub(" ", text.lower()).strip()


def _contains(haystack: str, needle: str) -> bool:
    """Case-insensitive, whitespace-tolerant substring search."""
    h = _normalize(haystack)
    n = _normalize(needle)
    return bool(n) and n in h


class Evaluator:
    def __init__(
        self,
        correct_threshold: float = CORRECT_THRESHOLD,
        close_threshold: float = CLOSE_THRESHOLD,
    ):
        self.correct_threshold = correct_threshold
        self.close_threshold = close_threshold

    # ------------------------------------------------------------------ public

    def evaluate(self, question: dict[str, Any], user_answer: str) -> dict[str, Any]:
        answer = (user_answer or "").strip()

        if not answer:
            return self._make_result(0.0, None, "Empty answer.", [], [])
        if any(re.search(p, answer.lower()) for p in _GIVE_UP_PATTERNS):
            return self._make_result(0.0, "unknown", "Learner gave up.", [], [])

        # Build the set of scoring approaches.
        approaches = self._resolve_approaches(question)

        best_score = 0.0
        best = None
        best_matched: list[str] = []
        best_missed: list[str] = []

        for ap in approaches:
            s, matched, missed = self._score_approach(answer, ap)
            if s > best_score:
                best_score = s
                best = ap
                best_matched = matched
                best_missed = missed

        if best_score >= self.correct_threshold:
            return self._make_result(
                best_score,
                None,
                f"Matched approach '{best['name']}' ({best_score:.0%}).",
                best_matched,
                best_missed,
                approach=best["name"],
                correct=True,
            )

        error_type = self._infer_error_type(answer.lower(), question, best_score)
        band = "close" if best_score >= self.close_threshold else "off-track"
        return self._make_result(
            best_score,
            error_type,
            f"{band.capitalize()} — {best_score:.0%} match to approach '{best['name'] if best else 'default'}'.",
            best_matched,
            best_missed,
            approach=best["name"] if best else None,
            correct=False,
        )

    # ------------------------------------------------------------------ approach resolution

    def _resolve_approaches(self, question: dict[str, Any]) -> list[dict[str, Any]]:
        """Return normalized list of approaches for this question.

        A question may declare multiple ``approaches``; if not, we synthesize a
        single ``default`` approach from ``expected_keywords`` + ``core_keywords``.
        """
        declared = question.get("approaches") or []
        if declared:
            return [
                {
                    "name": ap.get("name", f"approach_{i}"),
                    "core": list(ap.get("core", ap.get("core_keywords", []))),
                    "support": list(ap.get("keywords", ap.get("expected_keywords", []))),
                }
                for i, ap in enumerate(declared)
            ]

        return [{
            "name": "default",
            "core": list(question.get("core_keywords") or []),
            "support": list(question.get("expected_keywords") or []),
        }]

    # ------------------------------------------------------------------ scoring

    def _score_approach(
        self, answer: str, approach: dict[str, Any]
    ) -> tuple[float, list[str], list[str]]:
        core: list[str] = approach["core"]
        support: list[str] = approach["support"]

        matched: list[str] = []
        missed: list[str] = []

        core_total = sum(2.0 for _ in core)
        support_total = sum(1.0 for _ in support)
        earned = 0.0

        for kw in core:
            if _contains(answer, kw):
                earned += 2.0
                matched.append(kw)
            else:
                missed.append(kw)

        for kw in support:
            if _contains(answer, kw):
                earned += 1.0
                matched.append(kw)
            else:
                missed.append(kw)

        denom = core_total + support_total
        if denom == 0:
            return 0.0, matched, missed

        score = earned / denom

        # Core-keyword enforcement: missing ALL core concepts caps score at 0.45.
        if core and not any(_contains(answer, kw) for kw in core):
            score = min(score, 0.45)

        return score, matched, missed

    # ------------------------------------------------------------------ error-type inference

    def _infer_error_type(self, answer_lower: str, question: dict[str, Any], score: float) -> str:
        for pattern, etype in _ERROR_SIGNATURES:
            if re.search(pattern, answer_lower):
                return etype
        # Use question tags as a secondary hint — but only if the answer is
        # genuinely off-track, not "close".
        pitfalls = {"off_by_one", "base_case_issue", "time_complexity_issue", "state_definition"}
        for tag in question.get("tags") or []:
            if tag in pitfalls:
                return tag
        return "logic" if score < self.close_threshold else "unknown"

    # ------------------------------------------------------------------ output shaping

    @staticmethod
    def _make_result(
        score: float,
        error_type: str | None,
        notes: str,
        matched: Iterable[str],
        missed: Iterable[str],
        *,
        approach: str | None = None,
        correct: bool | None = None,
    ) -> dict[str, Any]:
        if correct is None:
            correct = score >= CORRECT_THRESHOLD
        return {
            "correct": bool(correct),
            "score": float(round(score, 3)),
            "error_type": error_type,
            "matched": list(matched),
            "missed": list(missed),
            "approach": approach,
            "notes": notes,
        }
