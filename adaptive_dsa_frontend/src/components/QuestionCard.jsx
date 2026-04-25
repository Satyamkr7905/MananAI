import { Lightbulb, Tag } from "lucide-react";

const DIFF_LABELS = ["", "Easy", "Easy-Medium", "Medium", "Hard", "Expert"];
const DIFF_TONES  = ["", "badge-success", "badge-success", "badge-brand", "badge-warn", "badge-danger"];

/**
 * QuestionCard — left-column content on the Practice page.
 * Shows title, difficulty badge, tags, description, and "why this question" block.
 */
export default function QuestionCard({ question }) {
  if (!question) return null;
  const { id, title, description, difficulty, topic, tags = [], reason } = question;

  return (
    <div className="card p-6 flex flex-col gap-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-mono text-slate-400">{id}</div>
          <h2 className="mt-1 text-xl font-semibold text-slate-900 tracking-tight">{title}</h2>
          <div className="mt-2 flex items-center gap-2 flex-wrap">
            <span className={DIFF_TONES[difficulty] || "badge-neutral"}>
              {DIFF_LABELS[difficulty] || "Unrated"}  · {difficulty}/5
            </span>
            <span className="badge-neutral capitalize">{topic}</span>
            {tags.slice(0, 4).map((t) => (
              <span key={t} className="badge-brand">
                <Tag className="h-3 w-3" /> {t}
              </span>
            ))}
          </div>
        </div>
      </div>

      <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-wrap">{description}</p>

      {reason && (
        <div className="rounded-xl bg-brand-50/60 ring-1 ring-brand-100 p-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-brand-700 uppercase tracking-wide">
            <Lightbulb className="h-4 w-4" /> Why this question?
          </div>
          <p className="mt-1.5 text-sm text-brand-900/80 leading-relaxed">{reason}</p>
        </div>
      )}
    </div>
  );
}
