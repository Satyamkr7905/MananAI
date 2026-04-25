import { CheckCircle2, XCircle, Info, Target } from "lucide-react";
import { pct } from "@/utils/formatters";
import { cn } from "@/utils/cn";
import ProgressBar from "./ProgressBar";

/**
 * FeedbackBox — renders the evaluator's verdict after a submission.
 *
 * Accepts the rich v2 shape from the backend:
 *   { correct, score, error_type, matched, missed, notes }
 * The UI leans on the partial-credit `score` so users see progress, not just pass/fail.
 */
export default function FeedbackBox({ result }) {
  if (!result) return null;
  const { correct, score = 0, error_type, matched = [], missed = [], notes } = result;

  const tone = correct ? "success" : score >= 0.4 ? "brand" : "danger";
  const Icon = correct ? CheckCircle2 : score >= 0.4 ? Target : XCircle;

  const toneClasses = {
    success: "ring-emerald-200 bg-emerald-50 text-emerald-900",
    brand:   "ring-brand-200   bg-brand-50   text-brand-900",
    danger:  "ring-rose-200    bg-rose-50    text-rose-900",
  }[tone];

  const lead = correct
    ? "Correct!"
    : score >= 0.4
    ? `So close — ${pct(score)} match.`
    : `Off-track — ${pct(score)} match.`;

  return (
    <div className={cn("rounded-2xl ring-1 p-5 animate-fade-in", toneClasses)}>
      <div className="flex items-center gap-2">
        <Icon className="h-5 w-5" />
        <span className="font-semibold">{lead}</span>
        {error_type && !correct && (
          <span className="badge-neutral ml-1">
            looks like: <span className="ml-1 font-mono">{error_type.replace(/_/g, " ")}</span>
          </span>
        )}
      </div>

      {!correct && (
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span>Partial credit</span>
            <span className="tabular-nums">{pct(score)}</span>
          </div>
          <ProgressBar value={score} tone={tone === "danger" ? "danger" : "brand"} />
        </div>
      )}

      {(matched.length > 0 || missed.length > 0) && (
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {matched.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide opacity-70">You mentioned</div>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {matched.map((m) => (
                  <span key={m} className="badge-success">{m}</span>
                ))}
              </div>
            </div>
          )}
          {missed.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide opacity-70">Consider</div>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {missed.map((m) => (
                  <span key={m} className="badge-warn">{m}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {notes && (
        <div className="mt-4 flex items-start gap-2 text-sm opacity-90">
          <Info className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{notes}</span>
        </div>
      )}
    </div>
  );
}
