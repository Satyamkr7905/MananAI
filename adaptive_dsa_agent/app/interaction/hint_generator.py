# Hint generator — Gemini with an offline fallback.
# hints always reference the problem title + use plain english.
# L1 = one Socratic nudge, L2 = name technique + missing piece, L3 = numbered steps.
# if Gemini fails or is off, offline path still gives a usable hint.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..config import settings
from ..utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class HintContext:
    # all the stuff a hint needs, already pulled apart from the request.
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
        # don't load gemini until first LLM hint — keeps CLI/API startup fast
        # when hints are offline only.
        self._llm_model: Any | None = None
        self._llm_model_attempted = False
        self._prompt_template = self._load_template()

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
        # returns a hint string. any LLM failure drops to offline path.
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

    # ---- LLM path ----

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
                "Produce a level-{level} tutoring hint in plain English, specific to the "
                "problem above. Do NOT reveal the full solution at levels 1 or 2."
            )

    # ---- offline path ----

    def _offline_hint(self, ctx: HintContext) -> str:
        tags = ctx.question.get("tags") or []
        technique = _technique_phrase(tags)

        if ctx.level == 1:
            return self._offline_l1(ctx, technique)
        if ctx.level == 2:
            return self._offline_l2(ctx, technique)
        return self._offline_l3(ctx)

    # L1 — one specific, plain-English Socratic question.
    def _offline_l1(self, ctx: HintContext, technique: tuple[str, str]) -> str:
        title = ctx.question.get("title") or "this problem"

        # praise what they already got so they don't feel restart from zero.
        praise = ""
        if ctx.matched:
            praise = f"You've got {_friendly_join(ctx.matched[:2])} — good start. "

        if ctx.score >= self._close():
            # close enough — point at the one missing piece.
            if ctx.missed:
                nudge = (
                    f"{praise}For \"{title}\", what role does **{ctx.missed[0]}** play? "
                    f"Adding that usually closes the gap."
                )
            else:
                nudge = (
                    f"{praise}For \"{title}\", can you say in one sentence "
                    f"what stays true after every step of your approach?"
                )
        elif ctx.score < 0.15 and ctx.user_answer:
            # really off-track — zoom out to the pattern.
            nudge = (
                f"Let's zoom out on \"{title}\". {technique[0].capitalize()}? "
                f"Name the pattern first — code comes after."
            )
        else:
            # somewhere in between, or no answer yet.
            nudge = f"{praise}{technique[0].capitalize()}"
            if not nudge.endswith("?"):
                nudge += "?"

        if ctx.weaknesses and ctx.weaknesses[0] in _WEAKNESS_NUDGES:
            nudge += " " + _WEAKNESS_NUDGES[ctx.weaknesses[0]]
        return nudge

    # L2 — name the technique plainly, call out one missing piece.
    def _offline_l2(self, ctx: HintContext, technique: tuple[str, str]) -> str:
        title = ctx.question.get("title") or "this problem"
        lines: list[str] = [f"Try this for \"{title}\": {technique[1]}."]

        if ctx.missed:
            piece = ctx.missed[0]
            lines.append(
                f"Your answer hasn't covered **{piece}** — that's the piece that "
                f"makes the whole thing work. Where does it fit in your plan?"
            )
        else:
            lines.append(
                "Write your plan in one sentence before coding — that alone usually "
                "unblocks the tricky case."
            )

        if ctx.weaknesses and ctx.weaknesses[0] == "off_by_one":
            lines.append(
                "Tip: walk through a 3-element example on paper to catch any "
                "off-by-one in your bounds."
            )
        return " ".join(lines)

    # L3 — numbered steps from the solution, no code.
    def _offline_l3(self, ctx: HintContext) -> str:
        steps = _split_solution_into_steps(ctx.question.get("solution") or "")
        numbered = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        return (
            "Here's the full approach — try to implement it yourself:\n"
            f"{numbered}\n"
            "If you're still stuck after this, ask to see the worked solution."
        )

    def _close(self) -> float:
        # stay in sync with Evaluator.CLOSE_THRESHOLD without importing at top.
        try:
            from .evaluator import CLOSE_THRESHOLD
            return float(CLOSE_THRESHOLD)
        except Exception:
            return 0.35


# ---- small pure helpers ----

# (L1 Socratic question, L2 approach blurb) per technique.
# rule: no jargon unless the same sentence explains it.
_TECHNIQUE_HINTS: dict[str, tuple[str, str]] = {
    "two_pointer": (
        "could two markers (one at each end, or one trailing the other) help you scan this in a single pass",
        "use two pointers — one at each end (or one trailing the other) — and decide which one to move based on the values they point at",
    ),
    "sliding_window": (
        "can you keep a window of valid items and slide it across the input",
        "keep a window that grows on the right; whenever it breaks the rule, shrink it from the left",
    ),
    "hash_map": (
        "what would you want to look up in one step while scanning the list",
        "as you scan, store what you've seen in a hash map (a dictionary) so you can look up the partner value in O(1)",
    ),
    "1d_dp": (
        "can the answer at position i be built from the answers at smaller positions",
        "define dp[i] in plain English ('the best answer up to index i'), then write the formula using dp[i-1] (and maybe dp[i-2])",
    ),
    "2d_dp": (
        "do two indices (i, j) together describe a sub-problem that's easier than the full input",
        "define dp[i][j] in one sentence, then build it from smaller (i, j) cells",
    ),
    "base_case": (
        "what is the smallest possible input supposed to return",
        "pin down the base cases first (n = 0, n = 1), then write the rule that builds bigger answers from them",
    ),
    "kadane": (
        "what's the best contiguous sum that *ends exactly at* the current index",
        "keep two running numbers: best-ending-here and best-overall, updating both in one pass",
    ),
    "off_by_one": (
        "what do the bounds look like when the input has length 0, 1, or 2",
        "re-derive the loop bounds by hand on a 3-element example before trusting the code",
    ),
    "state_definition": (
        "can you describe each dp cell in one plain sentence",
        "write a precise English definition of dp[i] or dp[i][j] first; the formula usually falls out",
    ),
    "binary_search": (
        "is there a predicate that flips from false to true exactly once across the input",
        "phrase the task as 'find the smallest x such that P(x) is true' and binary-search on x",
    ),
    "prefix_sum": (
        "if you knew the sum up to every index, could any range-sum be computed in one step",
        "build a prefix-sum array; then range sums are prefix[r] - prefix[l-1]",
    ),
    "stack": (
        "as you scan, do you need to remember the most recent unmatched item",
        "push items onto a stack; pop when the current item closes / resolves the one on top",
    ),
    "queue": (
        "do you process items in the order they arrived, FIFO",
        "push new items to the back of a queue and pull from the front",
    ),
    "bfs": (
        "could you explore nearest-first, one level at a time",
        "use a queue and process nodes level by level, marking visited as you go",
    ),
    "dfs": (
        "could you explore one branch as deep as possible, then backtrack",
        "recurse (or use a stack) to go deep, marking visited and returning on dead ends",
    ),
    "greedy": (
        "is there a locally-best choice that's also globally-best",
        "make the locally-best choice at each step and prove it never paints you into a corner",
    ),
    "sorting": (
        "would the problem become easy if the input were sorted first",
        "sort first, then use the ordering to do a one-pass solution",
    ),
}

_GENERIC = (
    "what pattern does this problem most resemble — a scan, a lookup, a window, a sort",
    "sketch the approach in one plain-English sentence before writing any code",
)

# tacked on when the learner has a known weakness.
_WEAKNESS_NUDGES: dict[str, str] = {
    "off_by_one":           "(You've had off-by-one issues before — double-check your bounds here.)",
    "base_case_issue":      "(Remember to sanity-check your base case — it's tripped you up before.)",
    "time_complexity_issue": "(A nested-loop solution tends to tempt you — can this be one-pass?)",
    "state_definition":     "(Describe what each dp cell means in plain words before writing the formula.)",
}


def _technique_phrase(tags: Iterable[str]) -> tuple[str, str]:
    for t in tags:
        if t in _TECHNIQUE_HINTS:
            return _TECHNIQUE_HINTS[t]
    return _GENERIC


def _friendly_join(items: list[str]) -> str:
    # human-sounding: 'loop and sum' not 'loop, sum'.
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _split_solution_into_steps(solution: str) -> list[str]:
    if not solution:
        return ["Re-read the problem and state the approach in plain English first."]
    parts = [p.strip() for p in solution.replace(";", ".").split(".") if p.strip()]
    return parts[:6] if parts else [solution.strip()]
