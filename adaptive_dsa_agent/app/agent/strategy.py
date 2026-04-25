"""
Strategy types — the enumerated "next actions" the decision engine can emit.

Keeping actions in a small, typed namespace means the CLI/UI can `match` on an
enum instead of parsing magic strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    ASK_NEW          = "ask_new"           # pick a fresh question
    GIVE_HINT        = "give_hint"         # stay on question, escalate hint level
    SHOW_SOLUTION    = "show_solution"     # reveal + move on, lower difficulty
    SWITCH_TOPIC     = "switch_topic"      # learner is stuck on current topic
    LEVEL_UP         = "level_up"          # celebratory bump; follow-up: ASK_NEW
    END_SESSION      = "end_session"       # (reserved — e.g., bank exhausted)


@dataclass
class Decision:
    """A single decision from the engine. Always includes a human-readable reason."""
    action: ActionType
    reason: str
    # Optional payload fields — only populated when relevant to the action.
    hint_level: int = 0
    next_topic: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
