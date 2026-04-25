import { Brain, Sparkles, Target, TrendingUp } from "lucide-react";

/**
 * AuthShell — two-column marketing + form layout shared by login and OTP.
 * The left panel never re-renders as the user moves between auth steps, so
 * the transition feels continuous.
 */
export default function AuthShell({ children }) {
  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2">
      {/* brand panel */}
      <aside className="hidden lg:flex flex-col justify-between bg-gradient-to-br from-brand-600 via-brand-700 to-brand-900 text-white p-12 relative overflow-hidden">
        <div className="flex items-center gap-2">
          <div className="h-9 w-9 rounded-xl bg-white/15 backdrop-blur grid place-items-center ring-1 ring-white/20">
            <Brain className="h-5 w-5" strokeWidth={2.25} />
          </div>
          <span className="font-semibold tracking-tight">DSA By NOVA</span>
        </div>

        <div className="relative z-10">
          <h1 className="text-3xl xl:text-4xl font-semibold tracking-tight leading-tight">
            An AI coach that <br /> meets you where you are.
          </h1>
          <p className="mt-4 text-brand-100/90 max-w-md leading-relaxed">
            Targeted questions. Socratic hints. Memory of every pattern you've met.
            Built for sustained, compounding improvement — not just cram-and-forget.
          </p>

          <ul className="mt-8 flex flex-col gap-4 max-w-md">
            <Feature icon={Target} title="Learning-zone selection">
              Questions target ~75% predicted success — the sweet spot for growth.
            </Feature>
            <Feature icon={Sparkles} title="Multi-level hints">
              Nudges first, scaffolding only if you need it. Never spoon-fed.
            </Feature>
            <Feature icon={TrendingUp} title="Weakness tracking">
              Off-by-one, time complexity, base cases — all tracked and revisited.
            </Feature>
          </ul>
        </div>

        {/* subtle decorative orbs */}
        <div className="absolute -bottom-24 -right-24 h-80 w-80 rounded-full bg-white/5 blur-3xl" />
        <div className="absolute top-20 -left-10 h-48 w-48 rounded-full bg-white/5 blur-3xl" />

        <div className="relative text-xs text-brand-100/70">
          © {new Date().getFullYear()} DSA By NOVA
        </div>
      </aside>

      {/* form panel */}
      <section className="flex items-center justify-center bg-white dark:bg-slate-950 p-6 sm:p-10">
        <div className="w-full max-w-sm">{children}</div>
      </section>
    </div>
  );
}

const Feature = ({ icon: Icon, title, children }) => (
  <li className="flex items-start gap-3">
    <div className="h-9 w-9 rounded-xl bg-white/10 ring-1 ring-white/20 grid place-items-center shrink-0">
      <Icon className="h-4.5 w-4.5" strokeWidth={2} />
    </div>
    <div>
      <div className="text-sm font-semibold">{title}</div>
      <p className="text-sm text-brand-100/80 leading-relaxed">{children}</p>
    </div>
  </li>
);
