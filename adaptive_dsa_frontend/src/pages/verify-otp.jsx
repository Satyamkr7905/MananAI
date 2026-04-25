import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/router";
import { ArrowLeft, ShieldCheck } from "lucide-react";
import toast from "react-hot-toast";

import AuthShell from "@/components/AuthShell";
import Loader from "@/components/Loader";
import { useAuth } from "@/hooks/useAuth";
import { getPendingEmail } from "@/services/auth";

const OTP_LEN = 6;

/**
 * Two verification flows land here:
 *   ?mode=signup  → after /signup, confirm the email is real (POST /signup/verify)
 *   ?mode=login   → magic-code sign-in (POST /verify-otp) — default when mode is absent
 */
export default function VerifyOtp() {
  const router = useRouter();
  const { login, verifySignupOtp, requestOtp } = useAuth();

  const mode = useMemo(() => {
    const m = (router.query?.mode || "").toString().toLowerCase();
    return m === "signup" ? "signup" : "login";
  }, [router.query]);

  const [email, setEmail] = useState("");
  const [digits, setDigits] = useState(Array(OTP_LEN).fill(""));
  const [submitting, setSubmitting] = useState(false);
  const [devOtpHint, setDevOtpHint] = useState("");
  const inputsRef = useRef([]);

  useEffect(() => {
    const pending = getPendingEmail();
    if (!pending) {
      router.replace(mode === "signup" ? "/signup" : "/login");
      return;
    }
    setEmail(pending);
    if (typeof window !== "undefined") {
      const d = window.sessionStorage.getItem("adt.devOtp");
      if (d && /^\d{6}$/.test(d)) setDevOtpHint(d);
    }
    setTimeout(() => inputsRef.current[0]?.focus(), 50);
  }, [router, mode]);

  const setDigit = (i, v) => {
    const c = v.replace(/\D/g, "").slice(-1);
    setDigits((prev) => {
      const next = [...prev];
      next[i] = c;
      return next;
    });
    if (c && i < OTP_LEN - 1) inputsRef.current[i + 1]?.focus();
  };

  const onKeyDown = (i, e) => {
    if (e.key === "Backspace" && !digits[i] && i > 0) {
      inputsRef.current[i - 1]?.focus();
    }
  };

  const onPaste = (e) => {
    const text = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, OTP_LEN);
    if (text.length) {
      e.preventDefault();
      const next = text.split("").concat(Array(OTP_LEN - text.length).fill(""));
      setDigits(next.slice(0, OTP_LEN));
      inputsRef.current[Math.min(text.length, OTP_LEN - 1)]?.focus();
    }
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    const otp = digits.join("");
    if (otp.length !== OTP_LEN) {
      toast.error("Enter the full 6-digit code.");
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "signup") {
        await verifySignupOtp(email, otp);
      } else {
        await login(email, otp);
      }
    } catch {
      setDigits(Array(OTP_LEN).fill(""));
      inputsRef.current[0]?.focus();
    } finally {
      setSubmitting(false);
    }
  };

  const onResend = async () => {
    try {
      await requestOtp(email);
      if (typeof window !== "undefined") {
        const d = window.sessionStorage.getItem("adt.devOtp");
        if (d && /^\d{6}$/.test(d)) setDevOtpHint(d);
      }
    } catch {
      /* toast surfaced */
    }
  };

  const title = mode === "signup" ? "Verify your email" : "Enter sign-in code";
  const intro =
    mode === "signup"
      ? "Enter the 6-digit code we just emailed — this confirms your address is real."
      : "Enter the 6-digit code we emailed you.";

  return (
    <AuthShell>
      <div className="animate-fade-in">
        <button
          type="button"
          onClick={() => router.push(mode === "signup" ? "/signup" : "/login")}
          className="btn-subtle -ml-3 mb-4 text-sm"
        >
          <ArrowLeft className="h-4 w-4" />
          {mode === "signup" ? "Back to sign up" : "Use a different email"}
        </button>

        <div className="flex items-center gap-2 mb-2">
          <div className="h-9 w-9 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-900/40 dark:text-brand-300 grid place-items-center">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 tracking-tight">{title}</h2>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {devOtpHint ? (
            <>SMTP is not configured on the server — use the code below (same one shown in the toast). </>
          ) : (
            <>
              {intro}{" "}
              <span className="font-medium text-slate-700 dark:text-slate-200">{email}</span>
            </>
          )}
        </p>

        {devOtpHint && (
          <p className="mt-2 text-sm text-amber-950 dark:text-amber-100 bg-amber-50 dark:bg-amber-950/60 ring-1 ring-amber-200 dark:ring-amber-800 rounded-xl px-3 py-2.5">
            Your one-time code: <span className="font-mono text-lg font-semibold tracking-widest">{devOtpHint}</span>
            <span className="block text-xs text-amber-900/80 dark:text-amber-200/80 mt-1.5">
              For real email delivery, set <code className="font-mono">GMAIL_USER</code> and{" "}
              <code className="font-mono">GMAIL_APP_PASSWORD</code> on your server.
            </span>
          </p>
        )}

        <form onSubmit={onSubmit} className="mt-8 flex flex-col gap-5">
          <div className="flex items-center justify-between gap-2" onPaste={onPaste}>
            {digits.map((d, i) => (
              <input
                key={i}
                ref={(el) => (inputsRef.current[i] = el)}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={d}
                onChange={(e) => setDigit(i, e.target.value)}
                onKeyDown={(e) => onKeyDown(i, e)}
                className="input text-center text-xl font-semibold h-14 tracking-widest"
                aria-label={`Digit ${i + 1}`}
              />
            ))}
          </div>

          <button type="submit" disabled={submitting} className="btn-primary w-full">
            {submitting ? <Loader size="sm" /> : mode === "signup" ? "Verify email" : "Verify & sign in"}
          </button>
        </form>

        <div className="mt-5 text-sm text-slate-500 dark:text-slate-400">
          Didn't get it?{" "}
          <button type="button" onClick={onResend} className="text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-medium">
            Resend code
          </button>
        </div>
      </div>
    </AuthShell>
  );
}
