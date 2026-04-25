// Auth session helper — thin wrapper over localStorage so the UI don't
// touch storage keys directly. one place to change if keys move.

import { STORAGE_KEYS } from "@/utils/constants";

const isBrowser = () => typeof window !== "undefined";

export const saveSession = ({ token, user }) => {
  if (!isBrowser()) return;
  window.localStorage.setItem(STORAGE_KEYS.token, token);
  window.localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(user));
};

export const loadSession = () => {
  if (!isBrowser()) return { token: null, user: null };
  const token = window.localStorage.getItem(STORAGE_KEYS.token);
  const raw = window.localStorage.getItem(STORAGE_KEYS.user);
  let user = null;
  try { user = raw ? JSON.parse(raw) : null; } catch { user = null; }
  return { token, user };
};

export const clearSession = () => {
  if (!isBrowser()) return;
  window.localStorage.removeItem(STORAGE_KEYS.token);
  window.localStorage.removeItem(STORAGE_KEYS.user);
  window.localStorage.removeItem(STORAGE_KEYS.pendingEmail);
  // note: per-user progress keys (adt.progress.<uid>) are kept on purpose —
  // signing out shouldn't wipe history. use clearProgress() from
  // userProgress.js if you actually want to wipe it.
};

export const setPendingEmail = (email) => {
  if (!isBrowser()) return;
  window.localStorage.setItem(STORAGE_KEYS.pendingEmail, email);
};

export const getPendingEmail = () => {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(STORAGE_KEYS.pendingEmail);
};
