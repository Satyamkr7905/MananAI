# Adaptive DSA Tutor — Frontend

Modern React frontend for the Adaptive DSA Tutor Agent. It runs standalone on mock data, or connects to any backend that implements the API contract below.

**Stack**: Next.js 14 · React 18 · Tailwind CSS · Recharts · lucide-react · react-hot-toast

---

## Features

- **Email OTP auth** with protected routes, persistent session via localStorage.
- **Dashboard** — streak / solved / accuracy / level stats, 14-day progress chart, topic strength cards with strongest/weakest flagged, recent highlights feed.
- **Practice page** — topic & difficulty filters, question card with "why this question?", multi-level hints (L1 → L2 → L3), code-style answer editor with `Ctrl + Enter` submit, rich feedback with partial-credit visualization and matched/missed concept pills.
- **Never-repeat rule** — questions you solve on the **first attempt with zero hints** are marked *Mastered* and automatically excluded from future rotations.
- **History page** — per-user log of every correctly-solved question with first-try badge, score, hints used, difficulty, topic, and timestamp. Filter by topic. Reset on demand.
- **Analytics page** — mistake breakdown donut, top-category progress bars, weekly bar chart, 14-day accuracy trend.
- **Polish** — toasts, loaders, empty states, keyboard-first OTP inputs (paste supported), mobile drawer nav, responsive grid.

---

## Quick start

```bash
# 1. install
cd adaptive_dsa_frontend
npm install

# 2. run (mock data, no backend required)
npm run dev
# → http://localhost:3000
#   Login with any email; the OTP in demo mode is 123456.
```

To connect a real backend:

```bash
cp .env.local.example .env.local
# edit .env.local and set NEXT_PUBLIC_API_BASE
npm run dev
```

When the real endpoint is unreachable, each API call **silently falls back to mock data** (you'll see a `[api]` warning in the console), so a flaky backend never blocks the UI.

---

## Project structure

```
adaptive_dsa_frontend/
├── src/
│   ├── pages/
│   │   ├── _app.jsx              # Providers, Toaster, Inter font
│   │   ├── _document.jsx
│   │   ├── index.jsx             # → /dashboard or /login based on session
│   │   ├── login.jsx             # Email entry, POSTs /send-otp
│   │   ├── verify-otp.jsx        # 6-digit code grid, POSTs /verify-otp
│   │   ├── dashboard.jsx         # Main screen
│   │   ├── practice.jsx          # Interaction surface (+ topic/difficulty filters, never-repeat)
│   │   ├── history.jsx           # Per-user solved log with Mastered flag
│   │   └── analytics.jsx         # Charts + mistake breakdown
│   ├── components/
│   │   ├── AppLayout.jsx         # ProtectedRoute + Navbar + Sidebar shell
│   │   ├── AuthShell.jsx         # 2-column marketing panel + form
│   │   ├── Navbar.jsx
│   │   ├── Sidebar.jsx           # Desktop rail + mobile drawer
│   │   ├── ProtectedRoute.jsx
│   │   ├── StatsCard.jsx
│   │   ├── ProgressBar.jsx
│   │   ├── TopicCard.jsx
│   │   ├── Highlight.jsx
│   │   ├── Graph.jsx             # Area/line — accuracy & level trends
│   │   ├── PieChart.jsx          # Mistake breakdown donut
│   │   ├── QuestionCard.jsx      # Title + difficulty + tags + "why this"
│   │   ├── CodeEditor.jsx        # Styled monospace textarea, Ctrl+Enter
│   │   ├── FeedbackBox.jsx       # Partial-credit & matched/missed pills
│   │   ├── FilterBar.jsx         # Topic + difficulty pickers for Practice
│   │   ├── HintPanel.jsx         # Multi-level hint escalator
│   │   ├── Loader.jsx
│   │   └── EmptyState.jsx
│   ├── context/
│   │   └── AuthContext.jsx       # login/logout/requestOtp + hydration
│   ├── hooks/
│   │   ├── useAuth.js
│   │   └── useApi.js             # Loading/error/data + toast on error
│   ├── services/
│   │   ├── api.js                # Real fetch wrapper (with mock fallback)
│   │   ├── mockApi.js            # Rich dummy data so UI works standalone (22 questions)
│   │   ├── auth.js               # Session storage helpers
│   │   └── userProgress.js       # Per-user solved set + history (localStorage)
│   ├── utils/
│   │   ├── cn.js
│   │   ├── constants.js          # Storage keys, color tokens
│   │   └── formatters.js
│   └── styles/
│       └── globals.css           # Tailwind + design-system classes
├── public/
│   └── favicon.svg
├── .env.local.example
├── next.config.js
├── tailwind.config.js
├── postcss.config.js
├── jsconfig.json
└── package.json
```

---

## API contract

Every call below is implemented in `src/services/api.js` with a mock fallback in `src/services/mockApi.js`.

| Method | Path | Request body | Response |
|---|---|---|---|
| `POST` | `/send-otp`    | `{ email }`                                | `{ ok: true, message }` |
| `POST` | `/verify-otp`  | `{ email, otp }`                           | `{ token, user: { id, email, name, joinedAt } }` |
| `GET`  | `/user/stats`  | —                                          | `{ streak, totalSolved, accuracy, level, topics[], strongest, weakest, progressSeries[], highlights[] }` |
| `GET`  | `/topics`      | —                                          | `[{ key, label, count }]` |
| `GET`  | `/questions/next` | query: `topic`, `difficulty`, `excludeIds` | `{ id, topic, title, difficulty, description, tags[], reason, time_budget_seconds } \| null` |
| `POST` | `/submit-answer` | `{ questionId, answer, hintsUsed }`       | `{ correct, score, error_type, matched[], missed[], notes }` |
| `GET`  | `/questions/:id/hint?level=N` | —                            | `{ level, text }` |
| `GET`  | `/analytics`   | —                                          | `{ mistakeBreakdown[], weekly[], accuracyTrend[] }` |

`mockApi.js` documents the exact shapes — use it as a spec for the backend.

---

## Auth flow

```
/login          →  enters email       →  POST /send-otp
                                        →  /verify-otp
/verify-otp     →  enters 6-digit code →  POST /verify-otp  (demo: 123456)
                                        →  token + user persisted to localStorage
                                        →  /dashboard
```

- Session is hydrated from localStorage on first client render via `AuthContext`.
- `AppLayout` wraps every authenticated page with `ProtectedRoute`; unauthenticated visits are redirected to `/login` without flashing.
- Sign-out clears all session keys (`adt.token`, `adt.user`, `adt.pendingEmail`).

---

## Practice filters, never-repeat, and history

The Practice page honors three intertwined user-facing rules:

1. **Topic filter** — a pill selector (All / Arrays / Dynamic Programming / Graphs / Trees) narrows the question pool.
2. **Difficulty filter** — a dropdown (All · 1 Easy · 2 · 3 Medium · 4 · 5 Hard) further narrows it.
3. **Never-repeat rule** — when a user submits a correct answer on their **first attempt** with **zero hints used**, the question ID is added to their per-user "mastered" set and automatically excluded from every future `getNextQuestion` call. The header subtitle reminds them how many questions have been locked out.

The **History** page (`/history`) is the read-side of this data:

- Lists every correctly-solved question (not just the mastered ones).
- Flags the ones that were solved first-try-no-hint with a `[Mastered]` badge and an emerald sparkle.
- Exposes topic filtering, KPIs (total, first-try count, average score, mastered/locked), and a "Clear history" action.

### Storage shape

All per-user progress is stored under a user-scoped localStorage key:

```
key: "adt.progress.<userId>"
value: {
  solvedFirstTryNoHint: [qid, ...],        // never-repeat set
  history: [{ qid, title, topic, difficulty, tags, score,
              hintsUsed, firstAttempt, solvedAt }, ...]
}
```

A real backend should own this data via `GET /user/history` and `POST /user/record-attempt`; the frontend is designed to swap in seamlessly — only `src/services/userProgress.js` would change.

## Design system

- Primary palette: Tailwind `brand-*` scale (indigo-driven) in `tailwind.config.js`.
- Design tokens in `globals.css` expose reusable classes: `.card`, `.btn-primary`, `.btn-ghost`, `.btn-subtle`, `.input`, `.badge-*`, `.section-title`.
- Semantic colors for error categories in `utils/constants.js` — both pie-chart slices and pills read the same source.

---

## Extending

| Want to... | Touch only... |
|---|---|
| Swap the textarea for Monaco | `components/CodeEditor.jsx` — props already match. |
| Add a new page | Drop a new file in `src/pages/` and wrap with `<AppLayout>`. |
| Add a nav item | `components/Sidebar.jsx` `NAV` array. |
| Change theme colors | `tailwind.config.js` `brand` scale + regenerate. |
| Hit a real backend | Set `NEXT_PUBLIC_API_BASE`; the mock fallback still kicks in for endpoints the backend hasn't shipped yet. |

---

## Notes

- **Mobile-first**: every page is tested at ≥ 360 px width; the Sidebar becomes a drawer below `md`.
- **No dead dependencies**: the MVP avoids SWR / React Query / redux / shadcn — everything above is one hook (`useApi`) + React Context. Add them later only when complexity demands it.
- **Accessibility**: all inputs have labels, buttons have `aria-label`s where icons are alone, focus rings are never suppressed.
