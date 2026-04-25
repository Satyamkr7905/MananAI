"""
Hint generator — LLM (Gemini) with a strong offline fallback.

v2 upgrades
-----------
* **Gap analysis** drives hint content: the evaluator tells us which concepts
  were present vs. missing in the answer, so the hint can reference them
  specifically ("You've got the loop right — what's missing is the complement
  lookup"). Both the LLM and the offline path consume this.
* **Socratic L1**: a single question, not a statement, to get the learner
  thinking. Different for "you're close" vs "you're lost" vs "first-try miss".
* **Targeted L2**: names the approach + the invariant/state — still no code.
* **Scaffolded L3**: numbered algorithm, pulled from the question's reference
  solution; still code-free.
* Graceful degradation: if Gemini errors or returns empty, the offline path
  produces a perfectly usable hint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..config import settings
from ..utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class HintContext:
    """Everything a hint generator needs, pre-analyzed."""
    question: dict[str, Any]
    user_answer: str
    level: int
    matched: list[str]
    missed: list[str]
    score: float
    approach: str | None
    weaknesses: list[str]
    strengths: list[str]


class HintGenerator:
    def __init__(self) -> None:
        # Defer Gemini import + client setup until the first LLM hint — keeps
        # CLI/API startup fast when hints are offline-only or unused.
        self._llm_model: Any | None = None
        self._llm_model_attempted = False
        self._prompt_template = self._load_template()

    # ------------------------------------------------------------------ public

    def generate_hint(
        self,
        question: dict[str, Any],
        user_answer: str,
        weaknesses: Iterable[str],
        level: int,
        *,
        evaluator_result: dict[str, Any] | None = None,
        strengths: Iterable[str] = (),
    ) -> str:
        """Return a hint string. Falls back to offline path on any LLM error."""
        level = max(1, min(3, int(level)))
        ctx = HintContext(
            question=question,
            user_answer=user_answer or "",
            level=level,
            matched=list((evaluator_result or {}).get("matched") or []),
            missed=list((evaluator_result or {}).get("missed") or []),
            score=float((evaluator_result or {}).get("score", 0.0)),
            approach=(evaluator_result or {}).get("approach"),
            weaknesses=list(weaknesses),
            strengths=list(strengths),
        )

        model = self._get_llm_model()
        if model is not None:
            try:
                return self._llm_hint(ctx, model)
            except Exception as exc:
                log.warning("LLM hint failed (%s); falling back to offline hint.", exc)

        return self._offline_hint(ctx)

    def _get_llm_model(self) -> Any | None:
        if self._llm_model_attempted:
            return self._llm_model
        self._llm_model_attempted = True
        self._llm_model = self._maybe_build_model()
        return self._llm_model

    # ------------------------------------------------------------------ LLM path

    def _llm_hint(self, ctx: HintContext, model: Any) -> str:
        q = ctx.question
        prompt = self._prompt_template.format(
            topic=q.get("topic", ""),
            title=q.get("title", ""),
            description=q.get("description", ""),
            solution=q.get("solution", ""),
            approach=ctx.approach or (q.get("tags") or ["general"])[0],
            user_answer=ctx.user_answer or "(no answer yet)",
            score=f"{ctx.score:.0%}",
            matched=", ".join(ctx.matched) or "(none)",
            missed=", ".join(ctx.missed) or "(none)",
            weaknesses=", ".join(ctx.weaknesses) or "none recorded",
            strengths=", ".join(ctx.strengths) or "none recorded",
            level=ctx.level,
        )
        import google.generativeai as genai  # type: ignore
        resp = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.35,
                max_output_tokens=260,
            ),
        )
        text = getattr(resp, "text", None)
        if not text:
            raise RuntimeError("Gemini returned an empty response.")
        return text.strip()

    def _maybe_build_model(self):
        if not settings.use_llm_hints or not settings.gemini_api_key:
            return None
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError:
            log.info("google-generativeai not installed — using offline hint generator.")
            return None
        try:
            genai.configure(api_key=settings.gemini_api_key)
            return genai.GenerativeModel(settings.gemini_model)
        except Exception as exc:
            log.warning("Could not build Gemini model (%s) — using offline hints.", exc)
            return None

    def _load_template(self) -> str:
        try:
            return settings.hint_prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            log.warning("hint_prompt.txt missing; using an embedded fallback template.")
            return (
                "Question: {title}\nDescription: {description}\nLearner answer: {user_answer}\n"
                "Matched: {matched}\nMissed: {missed}\nWeaknesses: {weaknesses}\nLevel: {level}\n"
                "Produce a level-{level} tutoring hint without revealing the solution."
            )

    # ------------------------------------------------------------------ offline path

    def _offline_hint(self, ctx: HintContext) -> str:
        tags = ctx.question.get("tags") or []
        technique = _technique_phrase(tags)

        if ctx.level == 1:
            return self._offline_l1(ctx, technique)
        if ctx.level == 2:
            return self._offline_l2(ctx, technique)
        return self._offline_l3(ctx)

    # ---- L1: Socratic, differentiated by how-close-they-are ----

    def _offline_l1(self, ctx: HintContext, technique: tuple[str, str]) -> str:
        # Praise what they got right, then ask ONE question.
        got_right = ""
        if ctx.matched:
            got_right = f"Good — you've already reached for {', '.join(ctx.matched[:2])}. "

        if ctx.score >= 0.4:
            nudge = (
                f"{got_right}You're close. What's the *invariant* that should hold "
                "between iterations? Write it in one sentence before coding."
            )
        elif ctx.score < 0.15 and ctx.user_answer:
            nudge = (
                f"Let's zoom out. {technique[0].capitalize()}? "
                "Try to name the algorithmic pattern before writing anything."
            )
        else:
            nudge = f"{got_right}{technique[0].capitalize()}?"

        if ctx.weaknesses:
            nudge += f" (You've slipped on `{ctx.weaknesses[0]}` recently — keep it in mind here.)"
        return nudge

    # ---- L2: targeted — name the approach, identify the gap ----

    def _offline_l2(self, ctx: HintContext, technique: tuple[str, str]) -> str:
        approach_line = f"Try this approach: {technique[1]}."
        gap_line = ""
        if ctx.missed:
            gap_line = (
                f" Your answer hasn't addressed {ctx.missed[0]}"
                + (f" and {ctx.missed[1]}" if len(ctx.missed) > 1 else "")
                + " — think about where that fits."
            )
        invariant_line = (
            " Before coding, write the loop invariant or DP state in plain English — "
            "that alone usually unblocks the tricky case."
        )
        if ctx.weaknesses and ctx.weaknesses[0] == "off_by_one":
            invariant_line = (
                " Walk a size-3 example on paper first to catch the off-by-one in your bounds."
            )
        return approach_line + gap_line + invariant_line

    # ---- L3: numbered algorithm, no code ----

    def _offline_l3(self, ctx: HintContext) -> str:
        steps = _split_solution_into_steps(ctx.question.get("solution") or "")
        numbered = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        return (
            "Here's the full approach (try to implement it yourself):\n"
            f"{numbered}\n"
            "If you're still stuck after this, ask to see the solution."
        )


# ---------------------------------------------------------------------------
# small pure helpers
# ---------------------------------------------------------------------------

_TECHNIQUE_HINTS: dict[str, tuple[str, str]] = {
    "two_pointer": (
        "think about two indices moving toward (or with) each other",
        "use two pointers and move them based on a comparison invariant",
    ),
    "sliding_window": (
        "think about maintaining a window of valid elements as you scan",
        "expand the right edge; contract the left edge whenever the window becomes invalid",
    ),
    "hash_map": (
        "think about what you'd want to look up in O(1) as you scan",
        "keep previously-seen values (or their complements) in a hash map for O(1) queries",
    ),
    "1d_dp": (
        "can the answer at index i be built from smaller indices?",
        "define dp[i] explicitly in words, then derive it from dp[i-1] and/or dp[i-2]",
    ),
    "2d_dp": (
        "do two indices (i, j) together describe a subproblem?",
        "define dp[i][j] precisely, then derive it from smaller (i, j) states",
    ),
    "base_case": (
        "what is the smallest possible input supposed to return?",
        "pin down the base cases first (n=0, n=1), then the recurrence",
    ),
    "kadane": (
        "what's the best subarray *ending* exactly at each index?",
        "track current-best-ending-here and overall-best in a single pass",
    ),
    "off_by_one": (
        "walk through length 0, 1, 2 inputs — do the bounds hold?",
        "re-derive the loop bounds on paper with a 3-element example",
    ),
    "state_definition": (
        "can you describe each dp cell in one sentence?",
        "write a precise English definition of dp[i] / dp[i][j] before coding",
    ),
    "binary_search": (
        "is the search space monotonic in some predicate?",
        "phrase the problem as 'find the smallest x such that P(x) is true' and binary-search on x",
    ),
}

_GENERIC = (
    "what algorithmic pattern does this problem most resemble?",
    "sketch the approach in pseudocode first, pinning down the invariant or recurrence",
)


def _technique_phrase(tags: Iterable[str]) -> tuple[str, str]:
    for t in tags:
        if t in _TECHNIQUE_HINTS:
            return _TECHNIQUE_HINTS[t]
    return _GENERIC


def _split_solution_into_steps(solution: str) -> list[str]:
    if not solution:
        return ["Re-read the problem and state the approach in plain English first."]
    parts = [p.strip() for p in solution.replace(";", ".").split(".") if p.strip()]
    return parts[:6] if parts else [solution.strip()]
