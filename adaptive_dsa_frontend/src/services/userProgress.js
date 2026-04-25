// per-user progress snapshot in localStorage so histories don't leak between
// test accounts. backend is the source of truth; we mirror it here so the
// History and Practice pages don't flash empty on reload.
//
// per user shape:
//   { solvedFirstTryNoHint: [qid], history: [AttemptRecord] }
// AttemptRecord:
//   { qid, title, topic, difficulty, score, hintsUsed, firstAttempt, solvedAt }

import { loadSession } from "./auth";
import { STORAGE_KEYS } from "@/utils/constants";

const PROGRESS_PREFIX = "adt.progress."; // final key is adt.progress.<userId>

const isBrowser = () => typeof window !== "undefined";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

const currentUserId = () => {
  const { user } = loadSession();
  return user?.id || user?.email || "guest";
};

const keyFor = (userId) => `${PROGRESS_PREFIX}${userId}`;

const DEFAULT_PROGRESS = () => ({ solvedFirstTryNoHint: [], history: [] });

// ---- read ----

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

// ---- write ----

const persist = (progress) => {
  if (!isBrowser()) return;
  window.localStorage.setItem(keyFor(currentUserId()), JSON.stringify(progress));
};

// save a correct attempt. if it was first-try-no-hint, also add it to the
// never-repeat set. returns the updated snapshot.
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
  progress.history.unshift(record);
  if (progress.history.length > 500) {
    progress.history.length = 500; // cap so storage don't grow forever
  }

  // never-repeat rule: first try AND zero hints.
  if (firstAttempt && hintsUsed === 0 && !progress.solvedFirstTryNoHint.includes(question.id)) {
    progress.solvedFirstTryNoHint.push(question.id);
  }

  persist(progress);
  return progress;
};

// wipe progress for the current user (reserved for a future reset button).
export const clearProgress = () => {
  if (!isBrowser()) return;
  window.localStorage.removeItem(keyFor(currentUserId()));
};

// overwrite local progress from GET /user/progress so History / Practice
// match the server after login or reload.
export async function syncProgressFromServer() {
  if (!isBrowser()) return;
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
