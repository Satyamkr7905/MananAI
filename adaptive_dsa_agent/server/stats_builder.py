# Build dashboard stats / analytics JSON from a UserState in the shape the
# frontend expects.

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.user_model.user_state import UserState

TOPIC_LABELS: dict[str, str] = {
    "arrays": "Arrays",
    "dp": "Dynamic Programming",
    "graphs": "Graphs",
    "trees": "Trees",
    "strings": "Strings",
}


def _day_key(iso_ts: str) -> str:
    try:
        d = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return d.date().isoformat()
    except ValueError:
        return date.today().isoformat()


def build_stats(state: UserState, total_questions: int = 0) -> dict[str, Any]:
    topics_out: list[dict[str, Any]] = []
    for topic_key, skill in sorted(state.topics.items()):
        lvl = max(0, min(5, int(skill.level)))
        progress = min(1.0, max(0.0, skill.level / 5.0))
        topics_out.append(
            {
                "topic": topic_key,
                "display": TOPIC_LABELS.get(topic_key, topic_key.replace("_", " ").title()),
                "level": lvl,
                "progress": round(progress, 2),
                "solved": int(skill.attempts),
                "accuracy": round(float(skill.ema_accuracy), 2),
            }
        )

    if not topics_out:
        topics_out = [
            {
                "topic": "arrays",
                "display": "Arrays",
                "level": 1,
                "progress": 0.05,
                "solved": 0,
                "accuracy": 0.5,
            }
        ]

    strongest = max(topics_out, key=lambda t: t["progress"])
    weakest = min(topics_out, key=lambda t: t["progress"])

    correct = sum(1 for h in state.history if h.correct)
    solved_unique = len({h.qid for h in state.history if h.correct})
    total = len(state.history)
    accuracy = (correct / total) if total else 0.0

    days_with = {_day_key(h.timestamp) for h in state.history}
    streak = 0
    d = date.today()
    while d.isoformat() in days_with:
        streak += 1
        d -= timedelta(days=1)

    progress_series = _progress_series(state)

    # Overall level: every (total_questions / 5) unique questions solved adds 1
    # level (clamped to 1..5). With 88 questions this is ~17 per level.
    effective_total = int(total_questions) if int(total_questions) > 0 else 88
    per_level = max(1, effective_total // 5)
    level = max(1, min(5, 1 + solved_unique // per_level))

    return {
        "streak": streak,
        "totalSolved": correct,
        "solvedUnique": solved_unique,
        "totalQuestions": effective_total,
        "perLevel": per_level,
        "accuracy": round(accuracy, 2),
        "level": level,
        "topics": topics_out,
        "strongest": strongest,
        "weakest": weakest,
        "progressSeries": progress_series,
        "highlights": _highlights(state),
    }


def _progress_series(state: UserState) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    by_day: dict[str, list[float]] = {}
    for h in state.history:
        day = _day_key(h.timestamp)
        by_day.setdefault(day, []).append(1.0 if h.correct else 0.0)

    out: list[dict[str, Any]] = []
    level = 1.5
    acc = 0.55
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        ds = d.isoformat()
        if ds in by_day:
            acc = sum(by_day[ds]) / len(by_day[ds])
        level = max(1.0, min(5.0, level + (acc - 0.5) * 0.08))
        lbl = d.strftime("%b %d").lstrip("0").replace(" 0", " ")
        out.append(
            {
                "date": ds,
                "label": lbl,
                "level": round(level, 2),
                "accuracy": round(acc, 2),
            }
        )
    return out


def _highlights(state: UserState) -> list[dict[str, Any]]:
    if not state.history:
        return []
    last = state.history[-1]
    return [
        {
            "id": "h_last",
            "type": "achievement" if last.correct else "hardest",
            "title": "Latest attempt",
            "meta": f"{last.topic} · score {last.score:.0%}",
            "when": last.timestamp,
        }
    ]


def build_analytics(state: UserState) -> dict[str, Any]:
    mistakes = Counter()
    for h in state.history:
        if not h.correct and h.error_type:
            mistakes[h.error_type] += 1
    mistake_breakdown = [{"key": k, "count": c} for k, c in mistakes.most_common()]

    today = datetime.now(timezone.utc).date()
    weekly: list[dict[str, Any]] = []
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        attempts = [h for h in state.history if _day_key(h.timestamp) == d.isoformat()]
        solved = sum(1 for h in attempts if h.correct)
        acc = (sum(1 for h in attempts if h.correct) / len(attempts)) if attempts else 0.0
        weekly.append({"day": day_names[d.weekday()], "solved": solved, "accuracy": round(acc, 2)})

    series = build_stats(state)["progressSeries"]
    accuracy_trend = [{"label": p["label"], "accuracy": p["accuracy"]} for p in series[-7:]]

    return {
        "mistakeBreakdown": mistake_breakdown
        or [
            {"key": "logic", "count": 0},
        ],
        "weekly": weekly,
        "accuracyTrend": accuracy_trend,
    }


def history_payload(state: UserState, bank_questions_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    # correct-only history rows + mastered IDs for the History page.
    rows: list[dict[str, Any]] = []
    for i in range(len(state.history) - 1, -1, -1):
        h = state.history[i]
        if not h.correct:
            continue
        prior = state.history[:i]
        first_attempt = not any(x.qid == h.qid for x in prior)
        q = bank_questions_by_id.get(h.qid, {})
        rows.append(
            {
                "qid": h.qid,
                "title": q.get("title", h.qid),
                "topic": h.topic,
                "difficulty": int(q.get("difficulty", 1)),
                "tags": q.get("tags") or [],
                "score": float(h.score),
                "hintsUsed": int(h.hints_used),
                "firstAttempt": first_attempt,
                "solvedAt": h.timestamp,
            }
        )

    mastered: list[str] = []
    for r in rows:
        if r["firstAttempt"] and r["hintsUsed"] == 0 and r["qid"] not in mastered:
            mastered.append(r["qid"])

    return {"history": rows, "solvedFirstTryNoHint": mastered}


def merge_solved_lists(server_list: Iterable[str], client_list: Iterable[str] | None) -> list[str]:
    out: list[str] = []
    for x in list(server_list) + list(client_list or ()):
        if x not in out:
            out.append(x)
    return out
