import { Filter } from "lucide-react";
import { cn } from "@/utils/cn";

/**
 * FilterBar — topic + difficulty selector for the Practice page.
 *
 * Controlled: parent owns the selected values and receives onChange events.
 * The "All" option is represented as the string "all" so the parent can
 * distinguish between "no filter" and a specific pick cleanly.
 */
const DIFFICULTY_OPTIONS = [
  { value: "all", label: "All" },
  { value: "1",   label: "1 · Easy" },
  { value: "2",   label: "2" },
  { value: "3",   label: "3 · Medium" },
  { value: "4",   label: "4" },
  { value: "5",   label: "5 · Hard" },
];

export default function FilterBar({
  topics = [],
  selectedTopic = "all",
  selectedDifficulty = "all",
  onTopicChange,
  onDifficultyChange,
  onClear,
}) {
  const hasFilter = selectedTopic !== "all" || selectedDifficulty !== "all";

  return (
    <div className="card p-4 flex flex-col md:flex-row md:items-center gap-4">
      <div className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200 shrink-0">
        <Filter className="h-4 w-4 text-slate-400 dark:text-slate-500" />
        Filter
      </div>

      {/* topic pills */}
      <div className="flex items-center gap-2 overflow-x-auto -mx-1 px-1">
        <Pill
          active={selectedTopic === "all"}
          onClick={() => onTopicChange?.("all")}
          count={topics.reduce((s, t) => s + t.count, 0)}
          solved={topics.reduce((s, t) => s + (t.solved ?? 0), 0)}
        >
          All topics
        </Pill>
        {topics.map((t) => (
          <Pill
            key={t.key}
            active={selectedTopic === t.key}
            onClick={() => onTopicChange?.(t.key)}
            count={t.count}
            solved={t.solved}
          >
            {t.label}
          </Pill>
        ))}
      </div>

      {/* difficulty dropdown */}
      <div className="flex items-center gap-2 md:ml-auto">
        <label htmlFor="diff" className="text-sm text-slate-500 dark:text-slate-400">Difficulty</label>
        <select
          id="diff"
          value={selectedDifficulty}
          onChange={(e) => onDifficultyChange?.(e.target.value)}
          className="input !py-2 !px-3 !text-sm !w-auto cursor-pointer"
        >
          {DIFFICULTY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        {hasFilter && (
          <button type="button" onClick={onClear} className="btn-subtle text-sm">
            Clear
          </button>
        )}
      </div>
    </div>
  );
}

const Pill = ({ active, onClick, count, solved, children }) => {
  const hasSolved = typeof solved === "number";
  const hasCount = typeof count === "number";
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium transition-colors shrink-0 ring-1",
        active
          ? "bg-brand-600 text-white ring-brand-600 dark:bg-brand-500 dark:ring-brand-500"
          : "bg-white text-slate-600 ring-slate-200 hover:ring-slate-300 hover:text-slate-900 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700 dark:hover:ring-slate-600 dark:hover:text-slate-100",
      )}
    >
      {children}
      {hasCount && (
        <span
          className={cn(
            "text-xs rounded-full px-1.5 py-0.5 tabular-nums",
            active
              ? "bg-white/20 text-white"
              : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
          )}
        >
          {hasSolved ? `${solved}/${count}` : count}
        </span>
      )}
    </button>
  );
};
