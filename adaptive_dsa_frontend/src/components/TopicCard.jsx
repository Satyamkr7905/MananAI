import { Check, AlertTriangle } from "lucide-react";
import ProgressBar from "./ProgressBar";
import { pct } from "@/utils/formatters";
import { cn } from "@/utils/cn";

/**
 * TopicCard — one row per DSA topic with level, progress, and accuracy.
 * `variant` draws an optional "Strongest" / "Weakest" ribbon on top.
 */
export default function TopicCard({ topic, variant }) {
  const { display, level, progress, accuracy, solved } = topic;

  const tone = progress >= 0.6 ? "success" : progress >= 0.3 ? "brand" : "warn";

  const ribbon =
    variant === "strongest" ? (
      <span className="badge-success"><Check className="h-3 w-3" /> Strongest</span>
    ) : variant === "weakest" ? (
      <span className="badge-warn"><AlertTriangle className="h-3 w-3" /> Needs work</span>
    ) : null;

  return (
    <div className={cn("card p-5 flex flex-col gap-3")}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-medium text-slate-900 dark:text-slate-100">{display}</div>
          <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Level {level}/5 · {solved} solved</div>
        </div>
        {ribbon}
      </div>

      <ProgressBar value={progress} tone={tone} />

      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>{pct(progress)} complete</span>
        <span className="tabular-nums">Accuracy {pct(accuracy)}</span>
      </div>
    </div>
  );
}
