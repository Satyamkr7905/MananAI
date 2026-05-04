import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, Code2, RefreshCw, Timer } from "lucide-react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";

import AppLayout from "@/components/AppLayout";
import CodeEditor from "@/components/CodeEditor";
import FeedbackBox from "@/components/FeedbackBox";
import Loader from "@/components/Loader";
import QuestionCard from "@/components/QuestionCard";
import EmptyState from "@/components/EmptyState";
import { getNextQuestion, submitAnswer } from "@/services/api";

function formatSeconds(totalSeconds) {
  const mins = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const secs = (totalSeconds % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
}

export default function InterviewPage() {
  const router = useRouter();
  const [question, setQuestion] = useState(null);
  const [loadingQuestion, setLoadingQuestion] = useState(true);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [confidence, setConfidence] = useState(70);
  const [attemptsOnQuestion, setAttemptsOnQuestion] = useState(0);
  const [exhausted, setExhausted] = useState(false);

  const resetRound = useCallback(() => {
    setAnswer("");
    setFeedback(null);
    setElapsedSeconds(0);
    setAttemptsOnQuestion(0);
  }, []);

  const loadNextQuestion = useCallback(async () => {
    setLoadingQuestion(true);
    setExhausted(false);
    resetRound();
    try {
      const q = await getNextQuestion({
        topic: "all",
        difficulty: "all",
        mode: "interview",
      });
      if (!q) {
        setExhausted(true);
        setQuestion(null);
      } else {
        setQuestion(q);
      }
    } catch (err) {
      toast.error(err?.message || "Could not load interview question.");
    } finally {
      setLoadingQuestion(false);
    }
  }, [resetRound]);

  useEffect(() => {
    loadNextQuestion();
  }, [loadNextQuestion]);

  useEffect(() => {
    if (!question || feedback?.correct) return undefined;
    const id = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [question, feedback?.correct]);

  const timerTone = useMemo(() => {
    if (elapsedSeconds < 300) return "text-slate-600 dark:text-slate-300";
    if (elapsedSeconds < 600) return "text-amber-600 dark:text-amber-300";
    return "text-rose-600 dark:text-rose-300";
  }, [elapsedSeconds]);

  // Hand off the just-cleared question to /sandbox for a real run-and-execute
  // session. We stash it on sessionStorage instead of the URL so the prompt
  // body — which can be quite long — doesn't have to be encoded in the path.
  // Accepts an explicit `q` so the auto-redirect path can pass the question
  // directly without leaning on closure timing inside setTimeout.
  const openSandboxForQuestion = (q) => {
    const target = q || question;
    if (!target) return;
    try {
      if (typeof window !== "undefined") {
        window.sessionStorage.setItem("adt.sandbox.question", JSON.stringify(target));
      }
    } catch {
      /* sessionStorage may be disabled — non-fatal */
    }
    router.push(`/sandbox?questionId=${encodeURIComponent(target.id)}&from=interview`);
  };

  const onOpenSandbox = () => openSandboxForQuestion(question);

  const onSubmit = async () => {
    if (!question || !answer.trim()) return;
    setSubmitting(true);
    setAttemptsOnQuestion((n) => n + 1);
    try {
      const res = await submitAnswer({
        questionId: question.id,
        answer,
        hintsUsed: 0,
        selfConfidence: confidence,
        mode: "interview",
      });
      setFeedback(res);
      if (res.correct) {
        toast.success("Interview round cleared.");
        // Round cleared on logic — push them into sandbox to write the
        // executable version. Short delay so the success toast lands first.
        setTimeout(() => {
          openSandboxForQuestion(question);
        }, 900);
      }
    } catch (err) {
      toast.error(err?.message || "Could not submit interview answer.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AppLayout
      title="Interview Mode"
      subtitle="Timed, stricter scoring, no hints. Focus on approach, complexity, and edge cases."
      actions={
        <>
          <div className={`hidden sm:flex items-center gap-2 text-sm font-medium ${timerTone}`}>
            <Timer className="h-4 w-4" />
            {formatSeconds(elapsedSeconds)}
          </div>
          <button onClick={loadNextQuestion} className="btn-ghost text-sm" disabled={loadingQuestion}>
            <RefreshCw className={`h-4 w-4 ${loadingQuestion ? "animate-spin" : ""}`} />
            New round
          </button>
          {feedback?.correct && !exhausted && (
            <>
              <button onClick={onOpenSandbox} className="btn-ghost text-sm">
                <Code2 className="h-4 w-4" />
                Open in Sandbox
              </button>
              <button onClick={loadNextQuestion} className="btn-primary text-sm">
                Next round
                <ArrowRight className="h-4 w-4" />
              </button>
            </>
          )}
        </>
      }
    >
      <div className="flex flex-col gap-6">
        <div className="card p-4">
          <div className="text-xs uppercase tracking-wide font-semibold text-slate-500 dark:text-slate-400">
            Confidence before submit
          </div>
          <div className="mt-2 flex items-center gap-4">
            <input
              type="range"
              min={0}
              max={100}
              value={confidence}
              onChange={(e) => setConfidence(Number(e.target.value))}
              className="w-full accent-brand-600"
              disabled={submitting}
            />
            <span className="badge-neutral tabular-nums min-w-14 justify-center">{confidence}%</span>
          </div>
        </div>

        {loadingQuestion ? (
          <div className="card p-12 grid place-items-center">
            <Loader label="Setting up your interview round..." />
          </div>
        ) : exhausted ? (
          <EmptyState
            title="No interview questions left"
            description="You've completed the currently available interview rounds."
          />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3 flex flex-col gap-6">
              <QuestionCard question={question} />
              {attemptsOnQuestion > 0 && (
                <div className="text-xs text-slate-500 dark:text-slate-400">Attempts this round: {attemptsOnQuestion}</div>
              )}
              {feedback && <FeedbackBox result={feedback} />}
              {feedback?.counterfactual && (
                <div className="card p-4 border border-brand-200 dark:border-brand-800">
                  <div className="text-xs font-semibold uppercase tracking-wide text-brand-700 dark:text-brand-300">
                    Counterfactual follow-up
                  </div>
                  <p className="mt-1.5 text-sm text-slate-700 dark:text-slate-200">{feedback.counterfactual}</p>
                </div>
              )}
            </div>
            <div className="lg:col-span-2">
              <CodeEditor
                value={answer}
                onChange={setAnswer}
                onSubmit={onSubmit}
                disabled={submitting || feedback?.correct}
              />
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
