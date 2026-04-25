/**
 * Auth service — narrow wrapper around the token+user persistence concern.
 *
 * The UI never touches localStorage directly; it goes through here so the
 * storage keys are centralized and mocked easily in tests later.
 */

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
  // Note: per-user progress keys (adt.progress.<uid>) intentionally NOT
  // cleared here — sign-out should preserve history so the next login for the
  // same user keeps their progress. Use `clearProgress()` from userProgress
  // for an explicit wipe.
};

export const setPendingEmail = (email) => {
  if (!isBrowser()) return;
  window.localStorage.setItem(STORAGE_KEYS.pendingEmail, email);
};

export const getPendingEmail = () => {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(STORAGE_KEYS.pendingEmail);
};
