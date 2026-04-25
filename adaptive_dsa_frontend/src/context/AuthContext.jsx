/**
 * AuthContext — single source of truth for whether the user is signed in.
 *
 * Responsibilities
 * ----------------
 * 1. Hydrate the session from localStorage on first client render so a
 *    refresh doesn't log the user out.
 * 2. Expose `login`, `logout`, and `requestOtp` helpers that wrap the API
 *    service, so pages stay UI-only.
 * 3. Expose `loading` while hydration is in flight — ProtectedRoute uses this
 *    to avoid flashing the login page on refresh.
 */

import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";

import {
  loginWithGoogle as apiLoginWithGoogle,
  loginWithPassword as apiLoginWithPassword,
  sendOtp,
  signup as apiSignup,
  signupVerify as apiSignupVerify,
  verifyOtp,
} from "@/services/api";
import {
  clearSession,
  getPendingEmail,
  loadSession,
  saveSession,
  setPendingEmail,
} from "@/services/auth";
import { syncProgressFromServer } from "@/services/userProgress";

export const AuthContext = createContext({
  user: null,
  token: null,
  loading: true,
  requestOtp: async () => {},
  login: async () => {},
  loginWithPassword: async () => {},
  signup: async () => {},
  verifySignupOtp: async () => {},
  loginWithGoogle: async () => {},
  logout: () => {},
});

export const AuthProvider = ({ children }) => {
  const [state, setState] = useState({ user: null, token: null, loading: true });
  const router = useRouter();

  // Hydrate from localStorage on mount — must run client-side only.
  // Finish loading immediately so the shell is not blocked by a slow /user/progress.
  useEffect(() => {
    const { token, user } = loadSession();
    setState({ token, user, loading: false });
    if (token && user) {
      syncProgressFromServer().catch(() => {
        /* offline or stale token */
      });
    }
  }, []);

  const requestOtp = useCallback(async (email) => {
    try {
      const res = await sendOtp({ email });
      setPendingEmail(email);
      if (typeof window !== "undefined" && res.devCode) {
        try {
          window.sessionStorage.setItem("adt.devOtp", String(res.devCode));
        } catch {
          /* ignore */
        }
        toast.success(
          `Your code: ${res.devCode}. Add GMAIL_USER and GMAIL_APP_PASSWORD to the API .env to receive codes by email.`,
          { duration: 8000 },
        );
      } else {
        toast.success(res.message || "OTP sent.");
        if (typeof window !== "undefined") {
          try {
            window.sessionStorage.removeItem("adt.devOtp");
          } catch {
            /* ignore */
          }
        }
      }
      return res;
    } catch (e) {
      toast.error(e?.message || "Could not send sign-in code.");
      throw e;
    }
  }, []);

  const login = useCallback(
    async (email, otp) => {
      try {
        const { token, user } = await verifyOtp({ email, otp });
        saveSession({ token, user });
        try {
          await syncProgressFromServer();
        } catch {
          /* non-fatal */
        }
        setState({ token, user, loading: false });
        try {
          if (typeof window !== "undefined") window.sessionStorage.removeItem("adt.devOtp");
        } catch {
          /* ignore */
        }
        toast.success(`Welcome, ${user.name || user.email}!`);
        router.push("/dashboard");
      } catch (e) {
        toast.error(e?.message || "Sign-in failed.");
        throw e;
      }
    },
    [router],
  );

  const loginWithGoogle = useCallback(
    async (credential) => {
      const { token, user } = await apiLoginWithGoogle({ credential });
      saveSession({ token, user });
      try {
        await syncProgressFromServer();
      } catch {
        /* non-fatal */
      }
      setState({ token, user, loading: false });
      toast.success(`Welcome, ${user.name || user.email}!`);
      router.push("/dashboard");
    },
    [router],
  );

  const loginWithPassword = useCallback(
    async (email, password) => {
      try {
        const { token, user } = await apiLoginWithPassword({ email, password });
        saveSession({ token, user });
        try {
          await syncProgressFromServer();
        } catch {
          /* non-fatal */
        }
        setState({ token, user, loading: false });
        toast.success(`Welcome back, ${user.name || user.email}!`);
        router.push("/dashboard");
      } catch (e) {
        toast.error(e?.message || "Sign-in failed.");
        throw e;
      }
    },
    [router],
  );

  const signup = useCallback(async ({ email, password, name }) => {
    try {
      const res = await apiSignup({ email, password, name });
      setPendingEmail(email);
      if (typeof window !== "undefined") {
        if (res?.devCode) {
          try {
            window.sessionStorage.setItem("adt.devOtp", String(res.devCode));
          } catch {
            /* ignore */
          }
          toast.success(
            `Your verification code: ${res.devCode}. (SMTP not configured — add GMAIL_USER/GMAIL_APP_PASSWORD in the API .env to receive codes by email.)`,
            { duration: 8000 },
          );
        } else {
          try {
            window.sessionStorage.removeItem("adt.devOtp");
          } catch {
            /* ignore */
          }
          toast.success(res?.message || "Account created. Check your email for the code.");
        }
      }
      return res;
    } catch (e) {
      toast.error(e?.message || "Could not create account.");
      throw e;
    }
  }, []);

  const verifySignupOtp = useCallback(
    async (email, otp) => {
      try {
        const { token, user } = await apiSignupVerify({ email, otp });
        saveSession({ token, user });
        try {
          await syncProgressFromServer();
        } catch {
          /* non-fatal */
        }
        setState({ token, user, loading: false });
        try {
          if (typeof window !== "undefined") window.sessionStorage.removeItem("adt.devOtp");
        } catch {
          /* ignore */
        }
        toast.success(`Welcome, ${user.name || user.email}!`);
        router.push("/dashboard");
      } catch (e) {
        toast.error(e?.message || "Verification failed.");
        throw e;
      }
    },
    [router],
  );

  const logout = useCallback(() => {
    clearSession();
    setState({ token: null, user: null, loading: false });
    router.push("/login");
  }, [router]);

  const value = useMemo(
    () => ({
      ...state,
      requestOtp,
      login,
      loginWithPassword,
      signup,
      verifySignupOtp,
      loginWithGoogle,
      logout,
      getPendingEmail,
    }),
    [state, requestOtp, login, loginWithPassword, signup, verifySignupOtp, loginWithGoogle, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
