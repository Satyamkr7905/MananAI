import { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useRouter } from "next/router";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";
import toast from "react-hot-toast";

import AuthShell from "@/components/AuthShell";
import Loader from "@/components/Loader";
import { useAuth } from "@/hooks/useAuth";

// Lazy-load the Google Identity Services button so its ~20KB chunk (and the
// remote gsi/client script) only load when the user actually needs it.
const GoogleLogin = dynamic(
  () => import("@react-oauth/google").then((m) => m.GoogleLogin),
  {
    ssr: false,
    loading: () => (
      <div className="h-10 w-[260px] rounded-md bg-slate-100 dark:bg-slate-800 animate-pulse" />
    ),
  },
);

export default function Login() {
  const router = useRouter();
  const { token, loading, requestOtp, loginWithPassword, loginWithGoogle } = useAuth();

  const showGoogle = Boolean(process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [magicBusy, setMagicBusy] = useState(false);

  useEffect(() => {
    if (!loading && token) router.replace("/dashboard");
  }, [loading, token, router]);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      toast.error("Enter your email and password.");
      return;
    }
    setSubmitting(true);
    try {
      await loginWithPassword(email.trim().toLowerCase(), password);
    } catch {
      // toast surfaced by AuthContext
    } finally {
      setSubmitting(false);
    }
  };

  const onMagicLink = async () => {
    if (!email.trim()) {
      toast.error("Enter your email first, then ask for a code.");
      return;
    }
    setMagicBusy(true);
    try {
      await requestOtp(email.trim().toLowerCase());
      router.push("/verify-otp?mode=login");
    } catch {
      /* toast surfaced */
    } finally {
      setMagicBusy(false);
    }
  };

  return (
    <AuthShell>
      <div className="animate-fade-in">
        <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 tracking-tight">Sign in</h2>
        <p className="mt-1.5 text-sm text-slate-500 dark:text-slate-400">
          Welcome back. Use the password you set during sign up.
        </p>

        <form onSubmit={onSubmit} className="mt-8 flex flex-col gap-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1.5">
              Email
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500" />
              <input
                id="email"
                type="email"
                required
                autoFocus
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input pl-9"
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500" />
              <input
                id="password"
                type={showPw ? "text" : "password"}
                required
                autoComplete="current-password"
                placeholder="Your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input pl-9 pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPw((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:text-slate-500 dark:hover:text-slate-300 dark:hover:bg-slate-800"
                aria-label={showPw ? "Hide password" : "Show password"}
              >
                {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <button type="submit" className="btn-primary w-full mt-2" disabled={submitting}>
            {submitting ? <Loader size="sm" /> : "Sign in"}
          </button>
        </form>

        <div className="mt-4 flex items-center justify-between text-sm">
          <button
            type="button"
            onClick={onMagicLink}
            disabled={magicBusy}
            className="text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-medium disabled:opacity-60"
          >
            {magicBusy ? "Sending code…" : "Email me a one-time code instead"}
          </button>
          <Link href="/signup" className="text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100 font-medium">
            Create account
          </Link>
        </div>

        {showGoogle && (
          <>
            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center" aria-hidden>
                <div className="w-full border-t border-slate-200 dark:border-slate-700" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-white dark:bg-slate-950 px-3 text-slate-400 dark:text-slate-500">or continue with</span>
              </div>
            </div>
            <div className="flex justify-center">
              <GoogleLogin
                onSuccess={async (res) => {
                  try {
                    await loginWithGoogle(res.credential);
                  } catch (e) {
                    toast.error(e?.message || "Google sign-in failed.");
                  }
                }}
                onError={() => toast.error("Google sign-in was cancelled or failed.")}
                useOneTap={false}
              />
            </div>
          </>
        )}

        <p className="mt-6 text-xs text-slate-400 dark:text-slate-500 leading-relaxed">
          New here?{" "}
          <Link href="/signup" className="text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-medium">
            Create an account
          </Link>{" "}
          — we'll email you a 6-digit code to verify your address.
        </p>
      </div>
    </AuthShell>
  );
}
