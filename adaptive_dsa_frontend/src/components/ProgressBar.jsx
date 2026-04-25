import { cn } from "@/utils/cn";

/**
 * ProgressBar — inline progress indicator.
 * `value` is in [0, 1]. Tone drives color.
 */
const TONES = {
  brand:   "bg-brand-500",
  success: "bg-emerald-500",
  warn:    "bg-amber-500",
  danger:  "bg-rose-500",
  neutral: "bg-slate-400",
};

export default function ProgressBar({ value = 0, tone = "brand", size = "md", className }) {
  const clamped = Math.max(0, Math.min(1, value));
  const height = size === "sm" ? "h-1.5" : size === "lg" ? "h-3" : "h-2";
  return (
    <div className={cn("w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden", height, className)}>
      <div
        className={cn("h-full rounded-full transition-[width] duration-500 ease-out", TONES[tone] || TONES.brand)}
        style={{ width: `${(clamped * 100).toFixed(1)}%` }}
      />
    </div>
  );
}
