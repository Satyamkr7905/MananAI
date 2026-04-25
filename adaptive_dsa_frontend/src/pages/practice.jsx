import { useCallback, useEffect, useState } from "react";
import { RefreshCw, ArrowRight, PartyPopper, BookOpen } from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";

import AppLayout from "@/components/AppLayout";
import CodeEditor from "@/components/CodeEditor";
import FeedbackBox from "@/components/FeedbackBox";
import FilterBar from "@/components/FilterBar";
import HintPanel from "@/components/HintPanel";
import Loader from "@/components/Loader";
import QuestionCard from "@/components/QuestionCard";
import EmptyState from "@/components/EmptyState";
import { getHint, getNextQuestion, getTopics, submitAnswer } from "@/services/api";
import {
  getSolvedFirstTryIds,
  recordCorrectAttempt,
} from "@/services/userProgress";

// Practice page — topic + difficulty filters and the never-repeat rule.
// never-repeat: a correct answer on the first attempt with zero hints
// marks the question "mastered", and we store that per-user in localStorage.
// mastered IDs are excluded from future rotations so the tutor don't waste
// your time on problems you've already nailed clean.
export default function Practice() {
  // ---- filters ----
  const [topics, setTopics] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState("all");
  const [selectedDifficulty, setSelectedDifficulty] = useState("all");

  // ---- question ----
  const [question, setQuestion] = useState(null);
  const [loadingQuestion, setLoadingQuestion] = useState(true);
  const [exhausted, setExhausted] = useState(false);
  const [masteredSet, setMasteredSet] = useState([]);

  // ---- interaction ----
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [attemptsOnQuestion, setAttemptsOnQuestion] = useState(0);
  const [hints, setHints] = useState([]);
  const [loadingHint, setLoadingHint] = useState(false);

  const resetInteraction = () => {
    setAnswer("");
    setFeedback(null);
    setHints([]);
    setAttemptsOnQuestion(0);
  };

  const loadNextQuestion = useCallback(async () => {
    setLoadingQuestion(true);
    setExhausted(false);
    resetInteraction();
    try {
      const solved = getSolvedFirstTryIds();
      setMasteredSet(solved);
      const q = await getNextQuestion({
        topic: selectedTopic,
        difficulty: selectedDifficulty,
        excludeIds: solved,
      });
      if (!q) {
        setQuestion(null);
        setExhausted(true);
      } else {
        setQuestion(q);
      }
    } catch {
      // api.js already toasts real-backend errors — nothing to do here.
    } finally {
      setLoadingQuestion(false);
    }
  }, [selectedTopic, selectedDifficulty]);

  useEffect(() => {
    getTopics().then(setTopics).catch(() => setTopics([]));
  }, []);

  // reload question whenever the filters change.
  useEffect(() => {
    loadNextQuestion();
  }, [loadNextQuestion]);

  // ---- submit ----

  const onSubmit = async () => {
    if (!answer.trim() || !question) return;
    setSubmitting(true);
    const thisAttemptNumber = attemptsOnQuestion + 1;
    setAttemptsOnQuestion(thisAttemptNumber);
    try {
      const res = await submitAnswer({
        questionId: question.id,
        answer,
        hintsUsed: hints.length,
      });
      setFeedback(res);

      if (res.correct) {
        const firstAttempt = thisAttemptNumber === 1;
        const noHints = hints.length === 0;
        const { solvedFirstTryNoHint } = recordCorrectAttempt({
          question,
          score: res.score,
          hintsUsed: hints.length,
          firstAttempt,
        });
        setMasteredSet(solvedFirstTryNoHint);

        if (firstAttempt && noHints) {
          toast.success("Nailed it first try — you won't see this one again.", { icon: "🏆" });
        } else {
          toast.success("Correct! Recorded in your history.");
        }
      }
    } catch (err) {
      toast.error(err?.message || "Could not submit your answer.");
    } finally {
      setSubmitting(false);
    }
  };

  const onRequestHint = async () => {
    if (!question) return;
    const level = Math.min(3, hints.length + 1);
    setLoadingHint(true);
    try {
      const h = await getHint({ questionId: question.id, level });
      setHints((prev) => [...prev, h.text]);
    } catch (err) {
      toast.error(err?.message || "Hint unavailable right now.");
    } finally {
      setLoadingHint(false);
    }
  };

  // ---- render ----

  const onClearFilters = () => {
    setSelectedTopic("all");
    setSelectedDifficulty("all");
  };

  return (
    <AppLayout
      title="Practice"
      subtitle={
        masteredSet.length
          ? `${masteredSet.length} question${masteredSet.length === 1 ? "" : "s"} mastered · they're excluded from your rotation.`
          : "The tutor picks questions based on your learning zone."
      }
      actions={
        <>
          <button onClick={loadNextQuestion} className="btn-ghost text-sm" disabled={loadingQuestion}>
            <RefreshCw className={`h-4 w-4 ${loadingQuestion ? "animate-spin" : ""}`} />
            Skip
          </button>
          {feedback?.correct && !exhausted && (
            <button onClick={loadNextQuestion} className="btn-primary text-sm">
              Next question
              <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </>
      }
    >
      <div className="flex flex-col gap-6">
        <FilterBar
          topics={topics}
          selectedTopic={selectedTopic}
          selectedDifficulty={selectedDifficulty}
          onTopicChange={setSelectedTopic}
          onDifficultyChange={setSelectedDifficulty}
          onClear={onClearFilters}
        />

        {loadingQuestion ? (
          <div className="card p-12 grid place-items-center">
            <Loader label="Picking your next question..." />
          </div>
        ) : exhausted ? (
          <EmptyState
            icon={PartyPopper}
            title="You've crushed everything in this filter."
            description={
              selectedTopic === "all" && selectedDifficulty === "all"
                ? "You've mastered every question we have. Come back after the next content drop — or clear specific items from your solved list."
                : "Every question matching your current filter has been solved first-try, no hints. Try a different topic or difficulty."
            }
            action={
              <div className="flex gap-2">
                <button onClick={onClearFilters} className="btn-ghost text-sm">
                  Clear filters
                </button>
                <Link href="/history" className="btn-primary text-sm">
                  <BookOpen className="h-4 w-4" />
                  View history
                </Link>
              </div>
            }
          />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3 flex flex-col gap-6">
              <QuestionCard question={question} />
              {feedback && <FeedbackBox result={feedback} />}
              <HintPanel
                hints={hints}
                onRequestHint={onRequestHint}
                loading={loadingHint}
                disabled={submitting || feedback?.correct}
              />
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
