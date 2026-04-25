# Adaptive DSA Tutor Agent (MVP)

An intelligent, **decision-driven** tutor for Data Structures & Algorithms.

Unlike a chatbot, this system:

- Tracks a persistent **user model** (topic skill levels, streaks, weaknesses, history).
- Uses a **decision engine** to pick the next action (new question, hint, solution, topic switch, level-up).
- Selects questions **adaptively** (weakness-biased, difficulty-matched, spaced-repeated).
- Escalates **multi-level hints** (never reveals the full solution on hints 1 or 2).
- Detects **weaknesses** (`off_by_one`, `base_case_issue`, `time_complexity_issue`, …) from the learner's answers.
- Works **with or without a Gemini key** — the hint generator has a deterministic offline fallback.

---

## Project layout

```
adaptive_dsa_agent/
├── app/
│   ├── main.py                 # CLI entry point — orchestrates the 10-step main flow
│   ├── config.py               # Thresholds, paths, feature flags
│   ├── agent/
│   │   ├── decision_engine.py  # "Brain": input state+verdict -> next action
│   │   ├── strategy.py         # ActionType enum + Decision dataclass
│   │   └── state_manager.py    # Façade: applies decisions to state + persists
│   ├── user_model/
│   │   ├── user_state.py       # Pure data model (topics, history, weaknesses)
│   │   ├── skill_tracker.py    # Streak/level update rules
│   │   └── weakness_detector.py# Evaluator-output -> normalized weakness tags
│   ├── question_engine/
│   │   ├── question_bank.py    # Loads questions.json, queries
│   │   ├── difficulty_manager.py# Pure-function difficulty math
│   │   └── selector.py         # Scoring algorithm + "why this question" reason
│   ├── interaction/
│   │   ├── evaluator.py        # Heuristic correctness check
│   │   ├── hint_generator.py   # LLM + offline rule-based fallback
│   │   └── feedback.py         # Human-friendly message composer
│   └── utils/
│       └── logger.py
├── data/
│   ├── questions.json          # 16 seed questions (arrays, DP; difficulty 1-5)
│   ├── topics.json
│   └── user_progress.json      # Persisted per-user state
├── prompts/
│   ├── hint_prompt.txt
│   ├── solution_prompt.txt
│   └── evaluation_prompt.txt
├── server/                     # FastAPI app: JWT auth, PostgreSQL (DATABASE_URL), tutor HTTP API
│   ├── main.py                 # ``uvicorn server.main:app``
│   ├── auth_routes.py          # /send-otp, /verify-otp, /auth/google
│   └── tutor_routes.py         # /user/stats, /questions/next, /submit-answer, …
├── tests/
│   ├── test_decision_engine.py # All 6 decision rules
│   └── test_selector.py        # Topic/difficulty/weakness/recency behaviors
├── requirements.txt
└── README.md
```

---

## HTTP API (Next.js frontend)

From this directory, install deps and run:

```bash
pip install -r requirements.txt
python -m uvicorn server.main:app --reload --host 127.0.0.1 --port 8000
```

Copy `.env.example` to `.env` and set at least `JWT_SECRET`. For **Google sign-in**, set `GOOGLE_CLIENT_ID` to your OAuth Web client ID (same value as `NEXT_PUBLIC_GOOGLE_CLIENT_ID` in the frontend). For **email OTP via Gmail**, set `GMAIL_USER` and `GMAIL_APP_PASSWORD` (Google Account app password). If SMTP is omitted, the server logs the OTP in development.

The API uses **PostgreSQL** by default. Set `DATABASE_URL` in `.env` (see `.env.example`). The URL form is `postgresql+psycopg://user:password@host:port/dbname` (url-encode special characters in the password). Create the database and user first; tables are created on API startup. For a local **SQLite** file instead, set e.g. `DATABASE_URL=sqlite:///./data/tutor_api.db` relative to `adaptive_dsa_agent/`.

---

## Quick start

Python 3.10 or newer is required.

```bash
# 1. (Optional) create a virtualenv
python -m venv .venv
.\.venv\Scripts\activate         # Windows PowerShell
# source .venv/bin/activate      # macOS/Linux

# 2. (Optional) install the Gemini SDK for LLM-powered hints
pip install -r requirements.txt

# 3. (Optional) enable the LLM hint path
#    Get a free key at https://aistudio.google.com/app/apikey, then:
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
#    Open `.env` and paste your GEMINI_API_KEY.
#    `.env` is gitignored, so your key stays off GitHub.
#
#    Alternatively, export it per-session:
#    PowerShell: $env:GEMINI_API_KEY = "..."
#    bash:       export GEMINI_API_KEY=...

# 4. Run the tutor
cd adaptive_dsa_agent
python -m app.main                 # start fresh as user "default"
python -m app.main --user alice    # separate progress file per user
python -m app.main --topic dp      # start on a specific topic
```

### In-session commands

| Command    | Effect                                                       |
|------------|--------------------------------------------------------------|
| *answer*   | Describe your approach (plain English / pseudocode).         |
| `hint`     | Ask for a hint. Each `hint` escalates (level 1 → 2 → 3).     |
| `skip`     | Skip the question (counts as wrong).                         |
| `solution` | Reveal the canonical solution and move on.                   |
| `switch X` | Switch topic (e.g. `switch dp`).                             |
| `progress` | Text-based dashboard (levels, streaks, weaknesses).          |
| `help`     | Show the command list.                                       |
| `quit`     | Save progress and exit.                                      |

---

## How the agent decides what to do next

Single-question rules (from `app/agent/decision_engine.py`):

| Situation                             | Action            |
|---------------------------------------|-------------------|
| Correct answer                        | `ASK_NEW`         |
| Correct answer completing a mastery streak (default 3) | `LEVEL_UP` then `ASK_NEW` |
| 1st wrong on current question         | `GIVE_HINT` level 1 |
| 2nd wrong on current question         | `GIVE_HINT` level 2 |
| 3rd wrong, topic wrong-streak < threshold | `SHOW_SOLUTION` |
| 3rd wrong, topic wrong-streak ≥ threshold (default 3) | `SWITCH_TOPIC` |

All thresholds live in `app/config.py` and are overridable via environment variables — no code changes required to tune behavior.

## How questions are selected

`QuestionSelector` filters by topic then scores every candidate:

```
score = topic_match_boost
      + difficulty_match_boost * closeness(q.difficulty, target)
      + weakness_boost        * (# of user weaknesses in q.tags)
      + spaced_repetition_bonus (if previously-failed and past its cooldown)
      - recent_penalty        (if asked in the last N attempts)
```

The `target` difficulty is derived from the learner's topic skill level, nudged ±1 by their confidence. The selector also produces a plain-English **"why this question"** string that is shown to the learner on every question.

## Weakness detection

The evaluator returns `{correct, error_type, notes}`. The weakness detector:

1. Trusts an explicit `error_type` from the evaluator.
2. Otherwise searches the learner's own answer for keyword patterns
   (e.g. `"off by one"`, `"base case"`, `"TLE"`, `"n^2"`).
3. Falls back to the question's tags when those name a known pitfall.

Weaknesses are stored as a counted dictionary on `UserState` and biases future question selection.

## LLM hints (optional)

When `GEMINI_API_KEY` is set and the `google-generativeai` package is installed, `HintGenerator` uses `prompts/hint_prompt.txt` to build a Gemini `generate_content` request (default model `gemini-2.0-flash`). On any error (missing key, network, filtered response), it gracefully falls back to the rule-based generator that reads the question's tags and reference-solution outline. You never get a broken session.

You can swap the model at any time (e.g. `GEMINI_MODEL=gemini-1.5-pro`) or disable the LLM path entirely with `USE_LLM_HINTS=off`.

---

## Running the tests

```bash
cd adaptive_dsa_agent
python -m unittest discover -s tests -v
```

Thirteen tests cover every decision-engine branch and every selector behavior (topic filter, difficulty steering, weakness boost, recency penalty, reason-string shape).

---

## Extending the MVP

| Want to …                                | Touch only …                                          |
|------------------------------------------|-------------------------------------------------------|
| Add a new topic (e.g. graphs)            | `data/topics.json` + questions in `data/questions.json` |
| Add a new weakness heuristic             | `app/user_model/weakness_detector.py`                  |
| Change how hint levels 1–3 behave        | `prompts/hint_prompt.txt` (LLM path) or `_TECHNIQUE_HINTS` table (offline) |
| Tune mastery / stuck thresholds          | Env vars (read by `app/config.py`)                     |
| Plug in a real code runner               | Replace `app/interaction/evaluator.py::Evaluator.evaluate` |
| Add a REST API                           | Wrap `StateManager`, `QuestionSelector`, `DecisionEngine`, `Evaluator` in FastAPI routes. The core classes are already pure enough to reuse. |

---

## Design notes

- **Pure data, reasoning elsewhere.** `UserState` is intentionally a dumb container; every update rule lives in `skill_tracker`, `weakness_detector`, or the decision engine. That keeps testing trivial.
- **State mutations are centralized** in `StateManager.register_attempt` so there is exactly one place to audit when behavior feels wrong.
- **Decisions are data.** The decision engine returns a typed `Decision` object with a `reason` string — the CLI just dispatches on it. A web UI would do the same.
- **Offline-first LLM.** The rule-based hint generator is strong enough to ship as the only path; the LLM is a pleasant upgrade, not a dependency.
