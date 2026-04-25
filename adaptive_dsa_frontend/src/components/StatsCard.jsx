import { cn } from "@/utils/cn";

/**
 * StatsCard — compact KPI tile used across the dashboard.
 *
 * Props:
 *   label    : "Current streak"
 *   value    : "7"               (big number / string)
 *   suffix   : "days"            (subtle unit)
 *   delta    : "+2 this week"    (optional trend string)
 *   tone     : brand | success | warn | danger | neutral
 *   icon     : lucide component
 */
const TONES = {
  brand:   { bg: "bg-brand-50 dark:bg-brand-900/40",     fg: "text-brand-600 dark:text-brand-300" },
  success: { bg: "bg-emerald-50 dark:bg-emerald-900/40", fg: "text-emerald-600 dark:text-emerald-300" },
  warn:    { bg: "bg-amber-50 dark:bg-amber-900/40",     fg: "text-amber-600 dark:text-amber-300" },
  danger:  { bg: "bg-rose-50 dark:bg-rose-900/40",       fg: "text-rose-600 dark:text-rose-300" },
  neutral: { bg: "bg-slate-100 dark:bg-slate-800",       fg: "text-slate-600 dark:text-slate-300" },
};

export default function StatsCard({ label, value, suffix, delta, tone = "brand", icon: Icon }) {
  const t = TONES[tone] || TONES.brand;
  return (
    <div className="card p-5 flex items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">{label}</div>
        <div className="mt-2 flex items-baseline gap-1.5">
          <div className="text-3xl font-semibold text-slate-900 dark:text-slate-100 tracking-tight tabular-nums">{value}</div>
          {suffix && <div className="text-sm text-slate-500 dark:text-slate-400">{suffix}</div>}
        </div>
        {delta && (
          <div className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">{delta}</div>
        )}
      </div>
      {Icon && (
        <div className={cn("h-10 w-10 rounded-xl grid place-items-center shrink-0", t.bg, t.fg)}>
          <Icon className="h-5 w-5" strokeWidth={2} />
        </div>
      )}
    </div>
  );
}
