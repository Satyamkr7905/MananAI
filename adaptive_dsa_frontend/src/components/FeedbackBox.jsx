import { useEffect } from "react";
import { CheckCircle2, XCircle, Info, Target } from "lucide-react";
import { pct } from "@/utils/formatters";
import { cn } from "@/utils/cn";
import ProgressBar from "./ProgressBar";
import { useMascot } from "@/context/MascotContext";

// FeedbackBox — shows the evaluator's verdict after the user submits.
// backend shape: { correct, score, error_type, matched, missed, notes }
// we lean on partial credit so the user see progress, not just pass/fail,
// and the tone is friendly — never "wrong" or "off-track".

const ERROR_LABELS = {
  off_by_one: "watch your loop bounds",
  base_case_issue: "pin down the base case",
  time_complexity_issue: "look for a faster, one-pass idea",
  state_definition: "define each dp cell in plain English first",
  logic: "small logic gap",
};

function leadMessage(correct, score) {
  if (correct && score >= 0.85) return "Correct!";
  if (correct) return "Nice — you got the main idea.";
  if (score >= 0.35) return "Nearly there — one small piece to add.";
  if (score > 0) return "You've got a start — let's sharpen it.";
  return "Let's think through the pattern together.";
}

export default function FeedbackBox({ result }) {
  const { setMood } = useMascot();

  // React to each new submission: the mascot celebrates a win, shows a
  // "thinking" nudge for partial answers, and mourns a miss.
  useEffect(() => {
    if (!result) return;
    if (result.correct) {
      if ((result.score ?? 0) >= 0.85) {
        setMood("excited", "You crushed it!");
      } else {
        setMood("happy", "Nice — main idea locked in!");
      }
    } else if ((result.score ?? 0) >= 0.35) {
      setMood("thinking", "So close — one more piece to add.");
    } else {
      setMood("sad", "Let's figure this one out together.");
    }
  }, [result, setMood]);

  if (!result) return null;
  const {
    correct,
    score = 0,
    error_type,
    matched = [],
    missed = [],
    notes,
  } = result;

  const tone = correct ? "success" : score >= 0.35 ? "brand" : "danger";
  const Icon = correct ? CheckCircle2 : score >= 0.35 ? Target : XCircle;

  const toneClasses = {
    success:
      "ring-emerald-200 bg-emerald-50 text-emerald-900 dark:ring-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-100",
    brand:
      "ring-brand-200   bg-brand-50   text-brand-900   dark:ring-brand-800   dark:bg-brand-900/30   dark:text-brand-100",
    danger:
      "ring-rose-200    bg-rose-50    text-rose-900    dark:ring-rose-800    dark:bg-rose-900/30    dark:text-rose-100",
  }[tone];

  const lead = leadMessage(correct, score);
  const errorLabel = error_type ? ERROR_LABELS[error_type] : null;

  return (
    <div className={cn("rounded-2xl ring-1 p-5 animate-fade-in", toneClasses)}>
      <div className="flex items-center gap-2">
        <Icon className="h-5 w-5" />
        <span className="font-semibold">{lead}</span>
        {errorLabel && !correct && (
          <span className="badge-neutral ml-1">
            tip: <span className="ml-1">{errorLabel}</span>
          </span>
        )}
      </div>

      {!correct && (
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span>How close you got</span>
            <span className="tabular-nums">{pct(score)}</span>
          </div>
          <ProgressBar value={score} tone={tone === "danger" ? "danger" : "brand"} />
        </div>
      )}

      {(matched.length > 0 || missed.length > 0) && (
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {matched.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide opacity-70">
                You mentioned
              </div>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {matched.map((m) => (
                  <span key={m} className="badge-success">
                    {m}
                  </span>
                ))}
              </div>
            </div>
          )}
          {missed.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide opacity-70">
                Worth adding
              </div>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {missed.map((m) => (
                  <span key={m} className="badge-warn">
                    {m}
                  </span>
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
