/**
 * userProgress — per-user local persistence of solved questions + history.
 *
 * In a real app, the backend owns this data. For the frontend-only MVP we
 * scope a tiny JSON document per user in localStorage so histories don't
 * leak between test accounts.
 *
 * Shape (per user):
 *   {
 *     solvedFirstTryNoHint: Set<qid>   -- never-repeat rule
 *     history: AttemptRecord[]         -- everything the user solved (correct)
 *   }
 *
 * AttemptRecord:
 *   { qid, title, topic, difficulty, score, hintsUsed,
 *     firstAttempt: bool, solvedAt: iso-string }
 *
 * Nothing outside this file should touch the storage directly.
 */

import { loadSession } from "./auth";
import { shouldUseMock } from "./api";
import { STORAGE_KEYS } from "@/utils/constants";

const PROGRESS_PREFIX = "adt.progress."; // full key is adt.progress.<userId>

const isBrowser = () => typeof window !== "undefined";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

const currentUserId = () => {
  const { user } = loadSession();
  return user?.id || user?.email || "guest";
};

const keyFor = (userId) => `${PROGRESS_PREFIX}${userId}`;

const DEFAULT_PROGRESS = () => ({ solvedFirstTryNoHint: [], history: [] });

// --------------------------------------------------------------------------- read

export const loadProgress = () => {
  if (!isBrowser()) return DEFAULT_PROGRESS();
  const raw = window.localStorage.getItem(keyFor(currentUserId()));
  if (!raw) return DEFAULT_PROGRESS();
  try {
    const parsed = JSON.parse(raw);
    return {
      solvedFirstTryNoHint: Array.isArray(parsed.solvedFirstTryNoHint) ? parsed.solvedFirstTryNoHint : [],
      history: Array.isArray(parsed.history) ? parsed.history : [],
    };
  } catch {
    return DEFAULT_PROGRESS();
  }
};

export const getSolvedFirstTryIds = () => loadProgress().solvedFirstTryNoHint;

export const getHistory = () => loadProgress().history;

// --------------------------------------------------------------------------- write

const persist = (progress) => {
  if (!isBrowser()) return;
  window.localStorage.setItem(keyFor(currentUserId()), JSON.stringify(progress));
};

/**
 * Record a correct attempt. If it was first-attempt-no-hint, it joins the
 * never-repeat set too. A history row is always appended for correct answers.
 *
 * Returns the updated progress snapshot.
 */
export const recordCorrectAttempt = ({
  question,
  score,
  hintsUsed,
  firstAttempt,
}) => {
  const progress = loadProgress();

  const record = {
    qid: question.id,
    title: question.title,
    topic: question.topic,
    difficulty: question.difficulty,
    tags: question.tags || [],
    score,
    hintsUsed,
    firstAttempt: !!firstAttempt,
    solvedAt: new Date().toISOString(),
  };
  progress.history.unshift(record);          // newest first
  if (progress.history.length > 500) {
    progress.history.length = 500;           // cap to avoid runaway storage
  }

  // The never-repeat rule: first attempt AND zero hints.
  if (firstAttempt && hintsUsed === 0 && !progress.solvedFirstTryNoHint.includes(question.id)) {
    progress.solvedFirstTryNoHint.push(question.id);
  }

  persist(progress);
  return progress;
};

/** Clear ALL progress for the current user. Exposed for a future "reset" button. */
export const clearProgress = () => {
  if (!isBrowser()) return;
  window.localStorage.removeItem(keyFor(currentUserId()));
};

/**
 * Overwrite local progress from the FastAPI ``GET /user/progress`` payload.
 * Call after login or on app load when a token exists so History / Practice
 * match server-side state.
 */
export async function syncProgressFromServer() {
  if (!isBrowser() || shouldUseMock()) return;
  const token = window.localStorage.getItem(STORAGE_KEYS.token);
  if (!token) return;
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), 12_000);
  let res;
  try {
    res = await fetch(`${API_BASE}/user/progress`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: ac.signal,
    });
  } catch {
    return;
  } finally {
    clearTimeout(t);
  }
  if (!res.ok) return;
  const data = await res.json();
  persist({
    solvedFirstTryNoHint: Array.isArray(data.solvedFirstTryNoHint) ? data.solvedFirstTryNoHint : [],
    history: Array.isArray(data.history) ? data.history : [],
  });
}
