/**
 * API service — thin fetch wrapper with automatic fallback to `mockApi.js`.
 *
 * Behavior
 * --------
 * * If NEXT_PUBLIC_USE_MOCK_API === "true" OR NEXT_PUBLIC_API_BASE is unset, we
 *   always use mock data (the UI is fully usable with zero backend).
 * * Otherwise we call the real backend at NEXT_PUBLIC_API_BASE. On any network
 *   error we fall back to mock data and log a console warning — so a flaky
 *   backend never blocks a demo.
 *
 * Each exported function mirrors exactly one backend endpoint from the spec.
 */

import {
  mockGetAnalytics,
  mockGetHint,
  mockGetNextQuestion,
  mockGetStats,
  mockGetTopics,
  mockSendOtp,
  mockSubmitAnswer,
  mockVerifyOtp,
} from "./mockApi";
import { STORAGE_KEYS } from "@/utils/constants";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "").trim();
const FORCE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_API === "true" || !API_BASE;

/** User can force the in-browser demo (OTP 123456, mock tutor) when API URL is set. */
const isPreferMock = () => typeof window !== "undefined" && window.localStorage.getItem("adt.preferMock") === "true";
export const shouldUseMock = () => FORCE_MOCK || isPreferMock();

/** True when auth and tutor calls hit your FastAPI server (not the in-browser demo). */
export const isRealBackendConfigured = () => !shouldUseMock();

const authHeader = () => {
  if (typeof window === "undefined") return {};
  const t = window.localStorage.getItem(STORAGE_KEYS.token);
  return t ? { Authorization: `Bearer ${t}` } : {};
};

const isNetworkError = (err) =>
  err?.name === "TypeError" ||
  /failed to fetch|networkerror|load failed|abort/i.test(String(err?.message || ""));

const request = async (path, { method = "GET", body, headers, timeoutMs = 15_000 } = {}) => {
  const ac = typeof AbortController !== "undefined" ? new AbortController() : null;
  const to = ac ? setTimeout(() => ac.abort(), timeoutMs) : null;
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: { "Content-Type": "application/json", ...authHeader(), ...headers },
      body: body ? JSON.stringify(body) : undefined,
      signal: ac?.signal,
    });
    if (!res.ok) {
      let msg = `Request failed (${res.status})`;
      try {
        const data = await res.json();
        const firstValErr = Array.isArray(data?.detail) ? data.detail[0] : null;
        const detailText =
          typeof data?.detail === "string"
            ? data.detail
            : firstValErr && typeof firstValErr === "object" && (firstValErr.msg || firstValErr.message)
              ? firstValErr.msg || firstValErr.message
              : null;
        msg = data?.message || detailText || msg;
      } catch {
        /* ignore body parse errors */
      }
      const err = new Error(msg);
      err.status = res.status;
      throw err;
    }
    return res.json();
  } catch (err) {
    if (isNetworkError(err)) {
      const where = API_BASE || "(unset)";
      const nicer = new Error(
        `Can't reach the API at ${where}. Make sure the FastAPI server is running on that address and CORS_ORIGINS includes this site.`,
      );
      nicer.cause = err;
      nicer.isNetwork = true;
      throw nicer;
    }
    throw err;
  } finally {
    if (to) clearTimeout(to);
  }
};

/** Graceful executor: try real endpoint, fall back to the mock. */
const safe = async (mockFn, realFn) => {
  if (shouldUseMock()) return mockFn();
  try {
    return await realFn();
  } catch (err) {
    // Network/CORS/5xx — any of these mean the backend isn't responding.
    console.warn("[api] real call failed, falling back to mock:", err.message);
    return mockFn();
  }
};

// ------------------------------ endpoints ---------------------------------

/**
 * Email OTP — never falls back to the demo flow when a backend URL is set.
 * (Demo OTP 123456 only applies when ``NEXT_PUBLIC_API_BASE`` is unset or mock is forced.)
 */
export const sendOtp = async ({ email }) => {
  if (shouldUseMock()) return mockSendOtp({ email });
  return request("/send-otp", { method: "POST", body: { email } });
};

export const verifyOtp = async ({ email, otp }) => {
  if (shouldUseMock()) return mockVerifyOtp({ email, otp });
  return request("/verify-otp", { method: "POST", body: { email, otp } });
};

/** Create an email+password account. Server responds with message+devCode? and
 * emails a 6-digit OTP to prove the address. Always hits the real backend —
 * the mock demo doesn't have password auth. */
export const signup = async ({ email, password, name }) => {
  if (shouldUseMock()) {
    const err = new Error(
      "Signup needs the real backend. Set NEXT_PUBLIC_API_BASE to your FastAPI server (e.g. http://127.0.0.1:8000).",
    );
    err.status = 503;
    throw err;
  }
  return request("/signup", { method: "POST", body: { email, password, name } });
};

/** Complete signup — OTP → JWT + user. */
export const signupVerify = async ({ email, otp }) => {
  if (shouldUseMock()) {
    const err = new Error("Signup verification requires the real backend.");
    err.status = 503;
    throw err;
  }
  return request("/signup/verify", { method: "POST", body: { email, otp } });
};

/** Password sign-in for verified accounts. */
export const loginWithPassword = async ({ email, password }) => {
  if (shouldUseMock()) {
    const err = new Error("Password sign-in requires the real backend.");
    err.status = 503;
    throw err;
  }
  return request("/login", { method: "POST", body: { email, password } });
};

export const getStats    = () => safe(
  () => mockGetStats(),
  () => request("/user/stats"),
);

/**
 * Get the next question, honoring optional filters.
 *
 * @param {{ topic?: string, difficulty?: number|string, excludeIds?: string[] }} opts
 */
export const getNextQuestion = (opts = {}) => {
  const params = new URLSearchParams();
  params.set("topic", opts.topic ?? "all");
  if (opts.difficulty && opts.difficulty !== "all") params.set("difficulty", String(opts.difficulty));
  if (opts.excludeIds?.length) params.set("excludeIds", opts.excludeIds.join(","));
  const qs = params.toString();
  return safe(
    () => mockGetNextQuestion(opts),
    () => request(`/questions/next?${qs}`),
  );
};

export const getTopics = () => safe(
  () => mockGetTopics(),
  () => request("/topics"),
);

export const submitAnswer = ({ questionId, answer, hintsUsed }) => safe(
  () => mockSubmitAnswer({ questionId, answer, hintsUsed }),
  () => request("/submit-answer", { method: "POST", body: { questionId, answer, hintsUsed } }),
);

export const getAnalytics = () => safe(
  () => mockGetAnalytics(),
  () => request("/analytics"),
);

export const getHint = ({ questionId, level }) => safe(
  () => mockGetHint({ questionId, level }),
  () => request(`/questions/${questionId}/hint?level=${level}`),
);

/** Full progress snapshot from the API (history + mastered IDs). Mock returns empty. */
export const getUserProgress = () => safe(
  () => Promise.resolve({ history: [], solvedFirstTryNoHint: [] }),
  () => request("/user/progress"),
);

/** Recent server-logged events + accuracy in window (improvement record). */
export const getUserImprovement = () => safe(
  () =>
    Promise.resolve({
      events: [],
      summary: { attemptsInWindow: 0, correctInWindow: 0, accuracyInWindow: null },
    }),
  () => request("/user/improvement"),
);

/**
 * Exchange a Google Identity Services credential (JWT) for our API JWT.
 * Requires ``NEXT_PUBLIC_API_BASE`` and a configured server ``GOOGLE_CLIENT_ID``.
 */
export const loginWithGoogle = async ({ credential }) => {
  if (shouldUseMock()) {
    const err = new Error(
      "Google sign-in needs a real backend. Set NEXT_PUBLIC_API_BASE and start the FastAPI server.",
    );
    err.status = 503;
    throw err;
  }
  return request("/auth/google", { method: "POST", body: { credential } });
};
