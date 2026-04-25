import { Lightbulb } from "lucide-react";
import { cn } from "@/utils/cn";

/**
 * HintPanel — shows the hints that have been requested so far, with a button
 * to escalate. Every hint line is timestamped by its level so learners can
 * see their escalation trail.
 */
export default function HintPanel({ hints = [], onRequestHint, loading, disabled }) {
  const nextLevel = Math.min(3, hints.length + 1);
  const atMax = hints.length >= 3;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-xl bg-amber-50 text-amber-600 grid place-items-center">
            <Lightbulb className="h-4 w-4" strokeWidth={2} />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-900">Hints</div>
            <div className="text-xs text-slate-500">
              {hints.length
                ? `Level ${hints.length} of 3 · escalates with each request`
                : "Gentle nudges first, stronger scaffolding if needed"}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onRequestHint}
          disabled={loading || atMax || disabled}
          className={cn("btn-ghost text-sm", atMax && "opacity-60")}
        >
          {loading ? "Getting hint..." : atMax ? "Max hints reached" : `Hint ${nextLevel}`}
        </button>
      </div>

      {hints.length === 0 ? (
        <div className="rounded-xl bg-slate-50 ring-1 ring-slate-100 p-4 text-sm text-slate-500">
          Stuck? Ask for a hint. We'll start with a question and only reveal the approach if you need it.
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {hints.map((h, i) => (
            <li key={i} className="flex items-start gap-3 animate-fade-in">
              <span className={cn(
                "shrink-0 h-6 w-6 rounded-full grid place-items-center text-xs font-semibold",
                i === 0 ? "bg-emerald-100 text-emerald-700"
                : i === 1 ? "bg-brand-100 text-brand-700"
                : "bg-amber-100 text-amber-700",
              )}>
                L{i + 1}
              </span>
              <p className="text-sm text-slate-800 leading-relaxed whitespace-pre-wrap">{h}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
