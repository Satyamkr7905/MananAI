"""
QuestionBank — read-only store over questions.json.

Wrapping the data in a class lets the rest of the code ask semantic questions
("give me everything for topic X at difficulty <= Y") without caring about the
underlying JSON layout.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from ..config import settings
from ..utils.logger import get_logger

log = get_logger(__name__)


class QuestionBank:
    def __init__(self, path: Path | None = None):
        self.path = path or settings.questions_path
        self._questions: list[dict[str, Any]] = []
        self._by_id: dict[str, dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        """Read and validate questions.json. Duplicates are rejected loudly."""
        if not self.path.exists():
            raise FileNotFoundError(f"Questions file not found: {self.path}")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("questions.json must contain a JSON array.")

        self._questions = data
        self._by_id = {}
        for q in data:
            qid = q.get("id")
            if not qid:
                raise ValueError(f"Question missing 'id': {q}")
            if qid in self._by_id:
                raise ValueError(f"Duplicate question id: {qid}")
            self._by_id[qid] = q
        log.info("Loaded %d questions from %s", len(self._questions), self.path)

    # --------------- queries ---------------

    def all(self) -> list[dict[str, Any]]:
        return list(self._questions)

    def get(self, qid: str) -> dict[str, Any] | None:
        return self._by_id.get(qid)

    def by_topic(self, topic: str) -> list[dict[str, Any]]:
        return [q for q in self._questions if q.get("topic") == topic]

    def by_topic_and_difficulty_range(
        self,
        topic: str,
        min_diff: int,
        max_diff: int,
    ) -> list[dict[str, Any]]:
        return [
            q for q in self._questions
            if q.get("topic") == topic and min_diff <= int(q.get("difficulty", 0)) <= max_diff
        ]

    def topics(self) -> Iterable[str]:
        return sorted({q["topic"] for q in self._questions})
