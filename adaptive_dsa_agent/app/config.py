"""
Central configuration for the Adaptive DSA Tutor Agent.

All paths, thresholds, and feature flags are read from here so the rest of the
codebase has no hard-coded constants. Values can be overridden via environment
variables which makes the MVP deployable without code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROMPTS_DIR = PROJECT_ROOT / "prompts"


def _load_dotenv(path: Path) -> None:
    """Tiny no-dependency .env loader.

    Parses ``KEY=VALUE`` lines (ignores blanks and ``#`` comments, supports
    single/double quoted values). Existing environment variables win, so a
    real shell export still takes precedence over the file.
    """
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        # .env is a convenience — never fail app startup because of it.
        pass


_load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class Config:
    # --- storage paths ---
    questions_path: Path = DATA_DIR / "questions.json"
    topics_path: Path = DATA_DIR / "topics.json"
    user_progress_path: Path = DATA_DIR / "user_progress.json"

    # --- prompt paths ---
    hint_prompt_path: Path = PROMPTS_DIR / "hint_prompt.txt"
    solution_prompt_path: Path = PROMPTS_DIR / "solution_prompt.txt"
    evaluation_prompt_path: Path = PROMPTS_DIR / "evaluation_prompt.txt"

    # --- decision-engine thresholds ---
    # Difficulty bounds for questions (1 easy ... 5 hard).
    min_difficulty: int = 1
    max_difficulty: int = 5

    # Topic skill bounds (0 beginner ... 5 mastered).
    min_skill_level: int = 0
    max_skill_level: int = 5

    # How many recent questions to avoid re-asking (short-term novelty window).
    recent_question_window: int = 5

    # Streak of correct answers required to bump topic skill level.
    mastery_streak: int = 3

    # Wrong-streak at which we switch topic (user is stuck).
    stuck_wrong_streak: int = 3

    # Spaced-repetition: attempts before a failed question becomes eligible again.
    spaced_repetition_cooldown: int = 3

    # Weight factors for question selection scoring.
    weakness_boost: float = 2.0
    topic_match_boost: float = 1.0
    difficulty_match_boost: float = 1.5
    recent_penalty: float = 3.0

    # --- LLM settings (Google Gemini) ---
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    )
    use_llm_hints: bool = field(
        default_factory=lambda: os.getenv("USE_LLM_HINTS", "auto").lower() != "off"
    )

    # --- misc ---
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


# A process-wide singleton. Import `settings` anywhere to read config.
settings = Config()
