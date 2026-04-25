import { useId } from "react";
import { Send } from "lucide-react";

/**
 * CodeEditor — a styled monospace textarea.
 *
 * We deliberately avoid Monaco for the MVP — the Python backend grades free
 * text (pseudocode / plain English descriptions of the approach), so a simple
 * textarea is a better fit and keeps the bundle lean. The component is named
 * CodeEditor so it can be swapped for a richer editor later with zero surface
 * area changes.
 */
export default function CodeEditor({
  value,
  onChange,
  onSubmit,
  disabled,
  placeholder = "Describe your approach, or paste pseudocode / code here...",
}) {
  const id = useId();

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      onSubmit?.();
    }
  };

  return (
    <div className="card p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <label htmlFor={id} className="text-sm font-medium text-slate-700">
          Your answer
        </label>
        <span className="text-xs text-slate-400">Ctrl + Enter to submit</span>
      </div>
      <textarea
        id={id}
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        spellCheck={false}
        disabled={disabled}
        rows={10}
        className="
          w-full rounded-xl bg-slate-900 text-slate-100 placeholder:text-slate-500
          font-mono text-sm leading-relaxed p-4
          focus:outline-none focus:ring-2 focus:ring-brand-500
          disabled:opacity-60 resize-y min-h-[220px]
        "
      />
      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={onSubmit}
          disabled={disabled || !value?.trim()}
          className="btn-primary"
        >
          <Send className="h-4 w-4" />
          Submit answer
        </button>
      </div>
    </div>
  );
}
