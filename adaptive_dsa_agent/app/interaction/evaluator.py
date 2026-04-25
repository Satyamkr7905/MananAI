# Evaluator — decides how correct a free-text answer is.
# synonym-aware (dictionary = hash map), partial-credit 0..1, kinder notes.
#
# Output shape:
#   { correct, score, error_type, matched, missed, approach, notes }

from __future__ import annotations

import re
from typing import Any, Iterable


CORRECT_THRESHOLD = 0.55   # score >= this means "correct"
CLOSE_THRESHOLD = 0.35     # score >= this means "nearly there"


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

# each set is one concept. if any alias in the group appears in the
# answer, the keyword counts as matched. matcher normalises to
# alphanumerics first so "hash-map" / "hash map" / "hashmap" all land
# on the same string.
_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({
        "hash", "hash map", "hashmap", "hash table", "hashtable",
        "dict", "dictionary", "map", "lookup table", "lookup",
    }),
    frozenset({
        "two pointer", "two pointers", "2 pointer", "2 pointers",
        "left right pointer", "left and right pointer",
    }),
    frozenset({"sliding window", "window"}),
    frozenset({
        "dp", "dynamic programming", "tabulation", "bottom up", "bottom-up",
    }),
    frozenset({"memo", "memoization", "memoize", "cache", "cached"}),
    frozenset({"recursion", "recursive", "recurse"}),
    frozenset({
        "loop", "iterate", "iteration", "iterating",
        "for loop", "while loop", "running", "running through",
    }),
    frozenset({"sum", "total", "accumulator", "running total"}),
    frozenset({"add", "plus", "increment"}),
    frozenset({"max", "maximum", "largest", "biggest", "greatest", "highest"}),
    frozenset({"min", "minimum", "smallest", "lowest"}),
    frozenset({"sort", "sorted", "sorting", "order", "ordered"}),
    frozenset({"swap", "exchange", "switch"}),
    frozenset({
        "complement", "difference", "target minus", "needed value",
        "pair sum", "remaining", "other number",
    }),
    frozenset({"stack", "lifo", "last in first out"}),
    frozenset({"queue", "fifo", "first in first out"}),
    frozenset({"bfs", "breadth first", "breadth-first", "level order"}),
    frozenset({"dfs", "depth first", "depth-first"}),
    frozenset({"linked list", "linked-list", "linkedlist", "linked nodes"}),
    frozenset({"binary search", "halve", "halving", "midpoint"}),
    frozenset({"base case", "base cases", "initial case", "stopping condition", "starting case"}),
    frozenset({"kadane", "best ending here", "current sum", "running sum"}),
    frozenset({
        "tree", "binary tree", "bst", "root", "leaf",
    }),
    frozenset({"graph", "adjacency", "vertices", "edges", "nodes and edges"}),
    frozenset({
        "seen", "visited", "already seen", "previously seen", "previous",
    }),
)


_WORD_NORMALIZE = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    return _WORD_NORMALIZE.sub(" ", text.lower()).strip()


def _aliases_of(keyword: str) -> set[str]:
    # return every accepted spelling for keyword (self + synonym group).
    norm = _normalize(keyword)
    if not norm:
        return set()
    for group in _SYNONYM_GROUPS:
        normalized = {_normalize(w) for w in group}
        if norm in normalized:
            return {a for a in normalized if a}
    return {norm}


def _contains(haystack: str, needle: str) -> bool:
    # case-insensitive, whitespace-tolerant, synonym-aware substring check.
    h = _normalize(haystack)
    if not h:
        return False
    for alias in _aliases_of(needle):
        if alias and alias in h:
            return True
    return False


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = _normalize(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


class Evaluator:
    def __init__(
        self,
        correct_threshold: float = CORRECT_THRESHOLD,
        close_threshold: float = CLOSE_THRESHOLD,
    ):
        self.correct_threshold = correct_threshold
        self.close_threshold = close_threshold

    def evaluate(self, question: dict[str, Any], user_answer: str) -> dict[str, Any]:
        answer = (user_answer or "").strip()

        if not answer:
            return self._make_result(0.0, None, "Nothing submitted yet.", [], [])
        if any(re.search(p, answer.lower()) for p in _GIVE_UP_PATTERNS):
            return self._make_result(
                0.0, "unknown",
                "No worries — grab a hint and we'll work through it together.",
                [], [],
            )

        approaches = self._resolve_approaches(question)

        best_score = 0.0
        best: dict[str, Any] | None = None
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
                self._correct_note(best_score, best_missed),
                best_matched,
                best_missed,
                approach=best["name"] if best else None,
                correct=True,
            )

        error_type = self._infer_error_type(answer.lower(), question, best_score)
        return self._make_result(
            best_score,
            error_type,
            self._wrong_note(best_score, best_missed),
            best_matched,
            best_missed,
            approach=best["name"] if best else None,
            correct=False,
        )

    @staticmethod
    def _correct_note(score: float, missed: list[str]) -> str:
        if score >= 0.85:
            return "Solid — you hit the core ideas."
        if missed:
            return (
                f"Right idea! Just a little tightening — consider "
                f"mentioning {missed[0]}."
            )
        return "Right idea! A couple of small details would round it out."

    @staticmethod
    def _wrong_note(score: float, missed: list[str]) -> str:
        if score >= 0.35:
            if missed:
                return (
                    f"Almost there — you're missing the piece about "
                    f"**{missed[0]}**. Add that and you're golden."
                )
            return "Almost there — add one more detail and it clicks."
        if score > 0.0:
            return "You've got part of it. Try naming the main technique first."
        return "Let's step back and name the pattern — then the details follow."

    def _resolve_approaches(self, question: dict[str, Any]) -> list[dict[str, Any]]:
        # normalise approaches into the {name, core, support} shape we score against.
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

        # if they missed every core concept, cap at 0.45 so support-only
        # answers can't pass the correct threshold by accident.
        if core and not any(_contains(answer, kw) for kw in core):
            score = min(score, 0.45)

        # authors sometime list a word in both `core` and `keywords` — dedupe
        # so UI don't show the same chip twice.
        matched = _dedupe_preserve_order(matched)
        missed = _dedupe_preserve_order(missed)

        return score, matched, missed

    def _infer_error_type(self, answer_lower: str, question: dict[str, Any], score: float) -> str:
        for pattern, etype in _ERROR_SIGNATURES:
            if re.search(pattern, answer_lower):
                return etype
        # fall back to question tags, but only when answer is really off-track.
        pitfalls = {"off_by_one", "base_case_issue", "time_complexity_issue", "state_definition"}
        for tag in question.get("tags") or []:
            if tag in pitfalls:
                return tag
        return "logic" if score < self.close_threshold else "unknown"

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
