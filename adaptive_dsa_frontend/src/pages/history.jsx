import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { BookOpen, Check, History as HistoryIcon, RotateCcw, Sparkles, Tag, Trash2 } from "lucide-react";
import toast from "react-hot-toast";

import AppLayout from "@/components/AppLayout";
import EmptyState from "@/components/EmptyState";
import { cn } from "@/utils/cn";
import { pct, shortDate, capitalize } from "@/utils/formatters";
import { clearProgress, loadProgress } from "@/services/userProgress";

const DIFF_TONES  = ["", "badge-success", "badge-success", "badge-brand", "badge-warn", "badge-danger"];

export default function HistoryPage() {
  const [progress, setProgress] = useState({ history: [], solvedFirstTryNoHint: [] });
  const [filterTopic, setFilterTopic] = useState("all");

  useEffect(() => {
    setProgress(loadProgress());
  }, []);

  const topics = useMemo(() => {
    const set = new Set(progress.history.map((r) => r.topic));
    return ["all", ...Array.from(set)];
  }, [progress.history]);

  const filtered = useMemo(() => {
    return progress.history.filter((r) => filterTopic === "all" || r.topic === filterTopic);
  }, [progress.history, filterTopic]);

  const stats = useMemo(() => {
    const total = progress.history.length;
    const firstTry = progress.history.filter((r) => r.firstAttempt && r.hintsUsed === 0).length;
    const avgScore = total ? progress.history.reduce((s, r) => s + (r.score || 0), 0) / total : 0;
    const byTopic = progress.history.reduce((acc, r) => {
      acc[r.topic] = (acc[r.topic] || 0) + 1;
      return acc;
    }, {});
    return { total, firstTry, avgScore, byTopic };
  }, [progress.history]);

  const onReset = () => {
    if (!confirm("Clear your entire solved history? This cannot be undone.")) return;
    clearProgress();
    setProgress({ history: [], solvedFirstTryNoHint: [] });
    toast.success("History cleared.");
  };

  return (
    <AppLayout
      title="History"
      subtitle="Everything you've solved, with the questions you mastered on the first try flagged."
      actions={
        progress.history.length > 0 && (
          <button onClick={onReset} className="btn-ghost text-sm text-rose-600 hover:bg-rose-50">
            <Trash2 className="h-4 w-4" />
            Clear history
          </button>
        )
      }
    >
      {progress.history.length === 0 ? (
        <EmptyState
          icon={HistoryIcon}
          title="No solved questions yet"
          description="Head to Practice and solve your first problem — correct answers will appear here."
          action={
            <Link href="/practice" className="btn-primary text-sm">
              <BookOpen className="h-4 w-4" />
              Start practicing
            </Link>
          }
        />
      ) : (
        <div className="flex flex-col gap-6">
          {/* Summary strip */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Kpi label="Solved total"       value={stats.total} tone="brand" />
            <Kpi label="First-try, no hint" value={stats.firstTry} tone="success" subtitle={`${pct(stats.firstTry / Math.max(1, stats.total))} of solves`} />
            <Kpi label="Average score"      value={pct(stats.avgScore)} tone="warn" />
            <Kpi label="Mastered (locked)"  value={progress.solvedFirstTryNoHint.length}
                 tone="neutral"
                 subtitle="Excluded from future rotations" />
          </div>

          {/* Topic filter row */}
          <div className="card p-3 flex items-center gap-2 overflow-x-auto">
            {topics.map((t) => {
              const active = filterTopic === t;
              const count = t === "all" ? progress.history.length : stats.byTopic[t] || 0;
              return (
                <button
                  key={t}
                  onClick={() => setFilterTopic(t)}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium transition-colors shrink-0 ring-1",
                    active
                      ? "bg-brand-600 text-white ring-brand-600"
                      : "bg-white text-slate-600 ring-slate-200 hover:ring-slate-300 hover:text-slate-900",
                  )}
                >
                  {t === "all" ? "All" : capitalize(t)}
                  <span className={cn(
                    "text-xs rounded-full px-1.5 py-0.5 tabular-nums",
                    active ? "bg-white/20 text-white" : "bg-slate-100 text-slate-500",
                  )}>{count}</span>
                </button>
              );
            })}
          </div>

          {/* Records list */}
          <div className="card overflow-hidden">
            <div className="hidden md:grid grid-cols-12 gap-4 px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 bg-slate-50 border-b border-slate-200">
              <div className="col-span-5">Question</div>
              <div className="col-span-2">Topic</div>
              <div className="col-span-1 text-center">Diff</div>
              <div className="col-span-1 text-center">Hints</div>
              <div className="col-span-1 text-center">Score</div>
              <div className="col-span-2 text-right">Solved</div>
            </div>

            <ul className="divide-y divide-slate-100">
              {filtered.map((r) => {
                const mastered = r.firstAttempt && r.hintsUsed === 0;
                return (
                  <li
                    key={`${r.qid}-${r.solvedAt}`}
                    className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center px-5 py-4 hover:bg-slate-50/60 transition-colors"
                  >
                    <div className="md:col-span-5 min-w-0 flex items-center gap-3">
                      <div className={cn(
                        "h-9 w-9 rounded-xl grid place-items-center shrink-0",
                        mastered ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-500",
                      )}>
                        {mastered ? <Sparkles className="h-4.5 w-4.5" /> : <Check className="h-4.5 w-4.5" />}
                      </div>
                      <div className="min-w-0">
                        <div className="font-medium text-slate-900 truncate flex items-center gap-2">
                          <span className="truncate">{r.title}</span>
                          {mastered && <span className="badge-success shrink-0"><Sparkles className="h-3 w-3" /> Mastered</span>}
                        </div>
                        <div className="text-xs text-slate-500 font-mono truncate">{r.qid}</div>
                      </div>
                    </div>
                    <div className="md:col-span-2 text-sm text-slate-700 capitalize">
                      <span className="badge-neutral">{r.topic}</span>
                    </div>
                    <div className="md:col-span-1 md:text-center">
                      <span className={DIFF_TONES[r.difficulty] || "badge-neutral"}>{r.difficulty}/5</span>
                    </div>
                    <div className="md:col-span-1 md:text-center text-sm tabular-nums">
                      {r.hintsUsed === 0 ? (
                        <span className="text-emerald-600 font-medium">0</span>
                      ) : (
                        <span className="text-slate-600">{r.hintsUsed}</span>
                      )}
                    </div>
                    <div className="md:col-span-1 md:text-center text-sm font-medium tabular-nums">
                      {pct(r.score)}
                    </div>
                    <div className="md:col-span-2 md:text-right text-sm text-slate-500">
                      {shortDate(r.solvedAt)}
                    </div>
                  </li>
                );
              })}
            </ul>

            {filtered.length === 0 && (
              <div className="p-10 text-center text-sm text-slate-500">
                No solves recorded for this topic yet.
              </div>
            )}
          </div>

          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <RotateCcw className="h-3.5 w-3.5" />
            With a real backend, history syncs from the server on login. Local storage keeps a fast offline copy.
          </div>
        </div>
      )}
    </AppLayout>
  );
}

// ---------------------------------------------------------------------------

const KPI_TONES = {
  brand:   "bg-brand-50 text-brand-600",
  success: "bg-emerald-50 text-emerald-600",
  warn:    "bg-amber-50 text-amber-600",
  neutral: "bg-slate-100 text-slate-600",
};

const Kpi = ({ label, value, subtitle, tone = "brand" }) => (
  <div className="card p-4">
    <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
    <div className="mt-1 flex items-baseline gap-2">
      <div className="text-2xl font-semibold text-slate-900 tabular-nums">{value}</div>
    </div>
    {subtitle && (
      <div className={cn("mt-1 text-xs inline-flex rounded-full px-2 py-0.5", KPI_TONES[tone] || KPI_TONES.brand)}>
        {subtitle}
      </div>
    )}
  </div>
);
