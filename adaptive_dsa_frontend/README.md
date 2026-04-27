# MananAI — Frontend

Next.js frontend for **MananAI**. Talks to the FastAPI backend.

**Stack**: Next.js 14 · React 18 · Tailwind CSS · Recharts · lucide-react · react-hot-toast

---

## Features

- **Email OTP + password auth** — signup flow verifies email with a 6-digit code, login checks password, Google Sign-In optional.
- **Dashboard** — streak / solved / accuracy / level stats, 14-day progress chart, topic strength cards, recent highlights.
- **Practice** — topic + difficulty filters, question card with "why this question?", 3 hint levels (L1 → L2 → L3), code-style textarea, feedback with partial-credit bar and matched / missed concept pills.
- **Never-repeat rule** — questions solved on the **first try with zero hints** are marked *Mastered* and skipped in future rotations.
- **History** — every correctly-solved question, filter by topic, KPIs, reset button.
- **Analytics** — mistake donut, top-category bars, weekly activity, accuracy trend.
- **Dark mode** on every page, mobile drawer nav, responsive grid.

---

## Quick start

```bash
cd adaptive_dsa_frontend
npm install
cp .env.local.example .env.local
# edit .env.local and set NEXT_PUBLIC_API_BASE to your FastAPI URL
npm run dev
# -> http://localhost:3000
```

The frontend needs the backend running — there is no offline mock any more. Start the FastAPI server first (see `../adaptive_dsa_agent/README.md`).

### env vars

| var | required | what it does |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE` | yes | FastAPI URL, e.g. `http://127.0.0.1:8000` or the Render URL |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | no | same Web client ID as the backend `GOOGLE_CLIENT_ID`. leave blank to hide the Google button |

---

## Project layout

```
src/
├── pages/
│   ├── _app.jsx           # providers, toaster, health-check ping
│   ├── _document.jsx      # preconnect hints
│   ├── index.jsx          # -> /dashboard or /login
│   ├── login.jsx          # password + OTP + google
│   ├── signup.jsx         # email + password, sends OTP
│   ├── verify-otp.jsx     # 6-digit code grid
│   ├── dashboard.jsx
│   ├── practice.jsx       # question + hints + editor + feedback
│   ├── history.jsx
│   └── analytics.jsx
├── components/            # layout, cards, charts, forms
├── context/
│   ├── AuthContext.jsx    # login/signup/logout + session hydrate
│   └── ThemeContext.jsx   # dark mode toggle
├── hooks/
│   ├── useAuth.js
│   └── useApi.js          # loading / error / data + toast on error
├── services/
│   ├── api.js             # fetch wrapper, one fn per endpoint
│   ├── auth.js            # localStorage session helpers
│   └── userProgress.js    # per-user progress mirror
└── styles/globals.css     # Tailwind + .card/.btn/.badge tokens
```

---

## API contract

Every call is defined in `src/services/api.js`.

| method | path | body | response |
| --- | --- | --- | --- |
| `POST` | `/send-otp` | `{ email }` | `{ ok, message, devCode? }` |
| `POST` | `/verify-otp` | `{ email, otp }` | `{ token, user }` |
| `POST` | `/signup` | `{ email, password, name }` | `{ ok, message, devCode? }` |
| `POST` | `/signup/verify` | `{ email, otp }` | `{ token, user }` |
| `POST` | `/login` | `{ email, password }` | `{ token, user }` |
| `POST` | `/auth/google` | `{ credential }` | `{ token, user }` |
| `GET`  | `/user/stats` | — | stats + progressSeries + topics |
| `GET`  | `/user/progress` | — | `{ history, solvedFirstTryNoHint }` |
| `GET`  | `/user/improvement` | — | recent events + window accuracy |
| `GET`  | `/topics` | — | `[{ key, label, count }]` |
| `GET`  | `/questions/next` | qs: `topic`, `difficulty`, `excludeIds` | question or `null` |
| `POST` | `/submit-answer` | `{ questionId, answer, hintsUsed }` | `{ correct, score, matched, missed, ... }` |
| `GET`  | `/questions/:id/hint?level=N` | — | `{ level, text }` |
| `GET`  | `/analytics` | — | mistake + weekly + trend data |

---

## Auth flow

```
/signup  -> email + password  -> POST /signup          -> OTP mail
/verify-otp -> 6-digit code    -> POST /signup/verify  -> token + user
/login   -> email + password  -> POST /login           -> token + user
         -> (or) Google btn   -> POST /auth/google     -> token + user
         -> (or) magic-link   -> POST /send-otp + /verify-otp
```

Session lives in localStorage keys `adt.token` and `adt.user`. `ProtectedRoute` bounces unauthenticated users to `/login` without flashing the target page.

---

## Never-repeat + history

Practice page honors three rules:

1. **Topic filter** — pill selector narrows the pool.
2. **Difficulty filter** — dropdown narrows further.
3. **Never-repeat** — correct answer on first try with zero hints locks out the question forever (per user).

History page reads this. Mastered rows get a badge. "Clear history" wipes everything.

Per-user localStorage key: `adt.progress.<userId>` holding `{ solvedFirstTryNoHint, history }`.

---

## Design tokens

- brand palette in `tailwind.config.js` (indigo-driven).
- shared classes in `globals.css`: `.card`, `.btn`, `.btn-primary`, `.btn-ghost`, `.btn-subtle`, `.input`, `.badge-*`, `.section-title` — all have `dark:` variants.
- mistake-category colors in `src/utils/constants.js` (pie chart + pills share the same source).

---

## Notes

- **Mobile-first** — tested at >= 360px; sidebar becomes a drawer under `md`.
- **No dead deps** — one custom hook (`useApi`) + React Context; no SWR / Redux / shadcn.
- **Accessibility** — labels on every input, aria-labels on icon buttons, focus rings left alone.
