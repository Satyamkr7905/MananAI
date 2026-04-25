import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { Eye, EyeOff, Lock, Mail, User } from "lucide-react";
import toast from "react-hot-toast";

import AuthShell from "@/components/AuthShell";
import Loader from "@/components/Loader";
import { useAuth } from "@/hooks/useAuth";
import { isRealBackendConfigured } from "@/services/api";

const MIN_PW = 8;

/** Mild strength meter — purely informational, not a server-side gate. */
function scorePassword(pw) {
  if (!pw) return { score: 0, label: "" };
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^\w\s]/.test(pw)) score++;
  const labels = ["Very weak", "Weak", "Okay", "Good", "Strong", "Excellent"];
  return { score, label: labels[Math.min(score, labels.length - 1)] };
}

export default function Signup() {
  const router = useRouter();
  const { token, loading, signup } = useAuth();
  const realBackend = isRealBackendConfigured();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && token) router.replace("/dashboard");
  }, [loading, token, router]);

  const strength = scorePassword(password);
  const issues = [];
  if (password && password.length < MIN_PW) issues.push(`Password must be at least ${MIN_PW} characters.`);
  if (confirm && password !== confirm) issues.push("Passwords don't match.");

  const canSubmit =
    email.trim() && password.length >= MIN_PW && password === confirm && !submitting;

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await signup({
        email: email.trim().toLowerCase(),
        password,
        name: name.trim() || undefined,
      });
      router.push("/verify-otp?mode=signup");
    } catch {
      // toast surfaced by AuthContext
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell>
      <div className="animate-fade-in">
        <h2 className="text-2xl font-semibold text-slate-900 tracking-tight">Create your account</h2>
        <p className="mt-1.5 text-sm text-slate-500">
          We'll email a 6-digit code to verify that Gmail address is yours.
        </p>

        {!realBackend && (
          <div className="mt-4 rounded-xl bg-amber-50 ring-1 ring-amber-200 px-3 py-2.5 text-xs text-amber-900 leading-relaxed">
            <strong className="font-semibold">Demo mode is on.</strong> Sign-up needs the real FastAPI backend. Set{" "}
            <code className="rounded bg-amber-100/80 px-1 py-0.5 font-mono text-[11px]">NEXT_PUBLIC_API_BASE</code> in{" "}
            <code className="rounded bg-amber-100/80 px-1 py-0.5 font-mono text-[11px]">.env.local</code> and start the
            API server.
          </div>
        )}

        <form onSubmit={onSubmit} className="mt-8 flex flex-col gap-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-slate-700 mb-1.5">
              Name <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                id="name"
                type="text"
                autoComplete="name"
                placeholder="Ada Lovelace"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input pl-9"
                maxLength={80}
              />
            </div>
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1.5">
              Email
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                placeholder="you@gmail.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input pl-9"
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                id="password"
                type={showPw ? "text" : "password"}
                required
                autoComplete="new-password"
                placeholder={`At least ${MIN_PW} characters`}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input pl-9 pr-10"
                minLength={MIN_PW}
                maxLength={128}
              />
              <button
                type="button"
                onClick={() => setShowPw((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                aria-label={showPw ? "Hide password" : "Show password"}
              >
                {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {password && (
              <div className="mt-2 flex items-center gap-2">
                <div className="flex-1 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className={`h-full transition-all ${
                      strength.score <= 1
                        ? "w-1/5 bg-rose-500"
                        : strength.score === 2
                          ? "w-2/5 bg-amber-500"
                          : strength.score === 3
                            ? "w-3/5 bg-yellow-500"
                            : strength.score === 4
                              ? "w-4/5 bg-emerald-500"
                              : "w-full bg-emerald-600"
                    }`}
                  />
                </div>
                <span className="text-xs text-slate-500 w-20 text-right">{strength.label}</span>
              </div>
            )}
          </div>

          <div>
            <label htmlFor="confirm" className="block text-sm font-medium text-slate-700 mb-1.5">
              Confirm password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                id="confirm"
                type={showPw ? "text" : "password"}
                required
                autoComplete="new-password"
                placeholder="Type it again"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className="input pl-9"
                minLength={MIN_PW}
                maxLength={128}
              />
            </div>
          </div>

          {issues.length > 0 && (
            <ul className="text-xs text-rose-600 flex flex-col gap-1">
              {issues.map((m) => (
                <li key={m}>• {m}</li>
              ))}
            </ul>
          )}

          <button type="submit" className="btn-primary w-full mt-2" disabled={!canSubmit}>
            {submitting ? <Loader size="sm" /> : "Create account & send code"}
          </button>
        </form>

        <p className="mt-6 text-sm text-slate-500">
          Already have an account?{" "}
          <Link href="/login" className="text-brand-600 hover:text-brand-700 font-medium">
            Sign in
          </Link>
        </p>
        <p className="mt-4 text-xs text-slate-400 leading-relaxed">
          By creating an account you agree to receive a one-time verification email at the address above.
          We store only a bcrypt hash of your password — never the plaintext.
        </p>
      </div>
    </AuthShell>
  );
}
