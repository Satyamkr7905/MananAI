import { useId } from "react";
import { Play } from "lucide-react";

/**
 * SandboxEditor — monospace code area + language picker + run button.
 *
 * Shape matches CodeEditor (textarea-based) so the bundle stays small and the
 * UI is consistent. We deliberately don't pull Monaco in here — the run loop
 * is the value, not editor bells. Tab key inserts two spaces so indentation
 * works the way users expect, and Ctrl/Cmd+Enter triggers a run.
 */
export default function SandboxEditor({
  value,
  onChange,
  onRun,
  running,
  language,
  languages = [],
  onLanguageChange,
  disabled,
}) {
  const id = useId();

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      onRun?.();
      return;
    }
    if (e.key === "Tab") {
      e.preventDefault();
      const el = e.target;
      const start = el.selectionStart;
      const end = el.selectionEnd;
      const next = `${value.slice(0, start)}  ${value.slice(end)}`;
      onChange?.(next);
      requestAnimationFrame(() => {
        el.selectionStart = el.selectionEnd = start + 2;
      });
    }
  };

  return (
    <div className="card p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <label
            htmlFor={`${id}-lang`}
            className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
          >
            Language
          </label>
          <select
            id={`${id}-lang`}
            value={language || ""}
            onChange={(e) => onLanguageChange?.(e.target.value)}
            disabled={disabled || running || !languages.length}
            className="rounded-lg bg-slate-100 dark:bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-800 dark:text-slate-100 ring-1 ring-slate-200 dark:ring-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {languages.length === 0 && <option value="">Loading…</option>}
            {languages.map((l) => (
              <option key={l.id} value={l.id}>
                {l.label}
              </option>
            ))}
          </select>
        </div>
        <span className="text-xs text-slate-400 dark:text-slate-500">Ctrl + Enter to run</span>
      </div>

      <textarea
        id={id}
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        onKeyDown={handleKeyDown}
        spellCheck={false}
        disabled={disabled}
        rows={18}
        className="
          w-full rounded-xl bg-slate-900 text-slate-100 placeholder:text-slate-500
          font-mono text-sm leading-relaxed p-4
          focus:outline-none focus:ring-2 focus:ring-brand-500
          disabled:opacity-60 resize-y min-h-[360px]
          dark:bg-slate-950 dark:ring-1 dark:ring-slate-800
        "
        placeholder="Write your solution here..."
      />

      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={onRun}
          disabled={disabled || running || !value?.trim()}
          className="btn-primary"
        >
          <Play className="h-4 w-4" />
          {running ? "Running..." : "Run code"}
        </button>
      </div>
    </div>
  );
}
