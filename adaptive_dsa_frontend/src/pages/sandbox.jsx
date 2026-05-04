import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import { ArrowLeft, BookOpen, Code2, Search, Terminal, X } from "lucide-react";
import toast from "react-hot-toast";

import AppLayout from "@/components/AppLayout";
import Loader from "@/components/Loader";
import QuestionCard from "@/components/QuestionCard";
import SandboxEditor from "@/components/SandboxEditor";
import { getAllQuestions, getSandboxLanguages, runCode } from "@/services/api";

// Sandbox page — reached after the user's logic is judged correct on
// Practice / Interview. We pass the question through sessionStorage so the
// editor can show the prompt next to a real code area, and the backend
// proxies execution to Piston so untrusted code never runs in-process.
const SESSION_KEY = "adt.sandbox.question";
const DRAFT_KEY = "adt.sandbox.draft"; // language => last draft

export default function Sandbox() {
  const router = useRouter();
  const { questionId, from } = router.query;

  const [languages, setLanguages] = useState([]);
  const [language, setLanguage] = useState("");
  const [source, setSource] = useState("");
  const [stdin, setStdin] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [question, setQuestion] = useState(null);
  const [loadingLangs, setLoadingLangs] = useState(true);

  // question picker — lazily loads the catalogue the first time it's opened.
  const [pickerOpen, setPickerOpen] = useState(false);
  const [bank, setBank] = useState([]);
  const [bankLoading, setBankLoading] = useState(false);
  const [bankLoaded, setBankLoaded] = useState(false);
  const [pickerQuery, setPickerQuery] = useState("");
  const pickerRef = useRef(null);

  // Pull whichever question the user just solved out of sessionStorage so we
  // can show the prompt alongside the code area. If they reached /sandbox
  // directly, that's fine too — the editor still works as a scratchpad.
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = window.sessionStorage.getItem(SESSION_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && (!questionId || parsed.id === questionId)) {
        setQuestion(parsed);
      }
    } catch {
      /* ignore session parse errors */
    }
  }, [questionId]);

  useEffect(() => {
    let cancelled = false;
    getSandboxLanguages()
      .then((res) => {
        if (cancelled) return;
        const list = res?.languages || [];
        setLanguages(list);
        if (list.length && !language) setLanguage(list[0].id);
      })
      .catch((err) => {
        toast.error(err?.message || "Could not load sandbox languages.");
      })
      .finally(() => {
        if (!cancelled) setLoadingLangs(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const currentLang = useMemo(
    () => languages.find((l) => l.id === language) || null,
    [languages, language],
  );

  // When the language changes, restore the user's last draft for that
  // language if there is one, else seed with the language's starter
  // template. This keeps in-progress code per language without overwriting
  // it when they flip between languages to compare.
  useEffect(() => {
    if (!currentLang) return;
    if (typeof window === "undefined") return;
    let drafts = {};
    try {
      drafts = JSON.parse(window.sessionStorage.getItem(DRAFT_KEY) || "{}");
    } catch {
      drafts = {};
    }
    const next = drafts[currentLang.id];
    setSource(typeof next === "string" && next.length ? next : currentLang.starter || "");
    setResult(null);
  }, [currentLang]);

  // Persist drafts so flipping languages or reloading doesn't nuke progress.
  useEffect(() => {
    if (!currentLang) return;
    if (typeof window === "undefined") return;
    try {
      const drafts = JSON.parse(window.sessionStorage.getItem(DRAFT_KEY) || "{}");
      drafts[currentLang.id] = source;
      window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify(drafts));
    } catch {
      /* sessionStorage may be full / disabled — non-fatal */
    }
  }, [source, currentLang]);

  // Lazy-load the question catalogue the first time the user opens the
  // picker, then keep it cached for the rest of the session.
  const ensureBankLoaded = useCallback(async () => {
    if (bankLoaded || bankLoading) return;
    setBankLoading(true);
    try {
      const list = await getAllQuestions();
      setBank(Array.isArray(list) ? list : []);
      setBankLoaded(true);
    } catch (err) {
      toast.error(err?.message || "Could not load question catalogue.");
    } finally {
      setBankLoading(false);
    }
  }, [bankLoaded, bankLoading]);

  const togglePicker = () => {
    setPickerOpen((open) => {
      const next = !open;
      if (next) ensureBankLoaded();
      else setPickerQuery("");
      return next;
    });
  };

  // Close the picker on outside click and on Escape so it doesn't trap focus.
  useEffect(() => {
    if (!pickerOpen) return undefined;
    const onDocClick = (e) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) {
        setPickerOpen(false);
        setPickerQuery("");
      }
    };
    const onKey = (e) => {
      if (e.key === "Escape") {
        setPickerOpen(false);
        setPickerQuery("");
      }
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [pickerOpen]);

  const filteredBank = useMemo(() => {
    const q = pickerQuery.trim().toLowerCase();
    if (!q) return bank;
    return bank.filter((item) => {
      const haystack = [
        item.title,
        item.id,
        item.topic,
        ...(Array.isArray(item.tags) ? item.tags : []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [bank, pickerQuery]);

  const selectQuestion = (q) => {
    if (!q) return;
    setQuestion(q);
    setResult(null);
    try {
      if (typeof window !== "undefined") {
        window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(q));
      }
    } catch {
      /* sessionStorage may be disabled — non-fatal */
    }
    setPickerOpen(false);
    setPickerQuery("");
    toast.success(`Loaded: ${q.title || q.id}`);
  };

  const onRun = useCallback(async () => {
    if (!currentLang || !source.trim()) return;
    setRunning(true);
    setResult(null);
    try {
      const res = await runCode({ language: currentLang.id, source, stdin });
      setResult(res);
      if (res?.exitCode === 0 && !res?.stderr) {
        toast.success("Ran cleanly.");
      } else if (res?.compileExitCode && res.compileExitCode !== 0) {
        toast.error("Compile error — check the output panel.");
      } else if (res?.exitCode && res.exitCode !== 0) {
        toast.error(`Exited with code ${res.exitCode}`);
      }
    } catch (err) {
      toast.error(err?.message || "Could not run your code.");
    } finally {
      setRunning(false);
    }
  }, [currentLang, source, stdin]);

  const backHref = from === "interview" ? "/interview" : "/practice";

  return (
    <AppLayout
      title="Sandbox"
      subtitle={
        question
          ? "Logic locked in — now write the actual code and run it."
          : "Pick a language, write code, and run it. Backed by Piston for safe execution."
      }
      actions={
        <div className="flex items-center gap-2">
          <div className="relative" ref={pickerRef}>
            <button
              type="button"
              onClick={togglePicker}
              className="btn-ghost text-sm"
              aria-haspopup="listbox"
              aria-expanded={pickerOpen}
            >
              <BookOpen className="h-4 w-4" />
              {question ? "Change question" : "Pick question"}
            </button>
            {pickerOpen && (
              <QuestionPicker
                loading={bankLoading}
                items={filteredBank}
                totalCount={bank.length}
                query={pickerQuery}
                onQueryChange={setPickerQuery}
                onSelect={selectQuestion}
                onClose={() => {
                  setPickerOpen(false);
                  setPickerQuery("");
                }}
              />
            )}
          </div>
          <Link href={backHref} className="btn-ghost text-sm">
            <ArrowLeft className="h-4 w-4" />
            {from === "interview" ? "Back to interview" : "Back to practice"}
          </Link>
        </div>
      }
    >
      <div className="flex flex-col gap-6">
        {loadingLangs ? (
          <div className="card p-12 grid place-items-center">
            <Loader label="Loading sandbox..." />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-2 flex flex-col gap-6">
              {question ? (
                <QuestionCard question={question} />
              ) : (
                <div className="card p-5 flex items-start gap-3">
                  <div className="h-9 w-9 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-900/40 dark:text-brand-300 grid place-items-center shrink-0">
                    <Code2 className="h-4 w-4" />
                  </div>
                  <div className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed">
                    No question selected. Solve one in{" "}
                    <Link href="/practice" className="text-brand-600 dark:text-brand-300 font-medium">
                      Practice
                    </Link>{" "}
                    or{" "}
                    <Link href="/interview" className="text-brand-600 dark:text-brand-300 font-medium">
                      Interview
                    </Link>{" "}
                    first to bring its prompt here, or just use the editor as a
                    code scratchpad.
                  </div>
                </div>
              )}

              <div className="card p-5">
                <div className="flex items-center gap-2 mb-2">
                  <Terminal className="h-4 w-4 text-slate-500 dark:text-slate-400" />
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                    Standard input
                  </span>
                </div>
                <textarea
                  value={stdin}
                  onChange={(e) => setStdin(e.target.value)}
                  rows={4}
                  spellCheck={false}
                  placeholder="Optional — anything your program reads from stdin"
                  className="
                    w-full rounded-xl bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100
                    placeholder:text-slate-400 dark:placeholder:text-slate-500
                    font-mono text-xs leading-relaxed p-3
                    ring-1 ring-slate-200 dark:ring-slate-800
                    focus:outline-none focus:ring-2 focus:ring-brand-500
                    resize-y min-h-[88px]
                  "
                />
              </div>
            </div>

            <div className="lg:col-span-3 flex flex-col gap-6">
              <SandboxEditor
                value={source}
                onChange={setSource}
                onRun={onRun}
                running={running}
                language={language}
                languages={languages}
                onLanguageChange={setLanguage}
              />

              <OutputPanel running={running} result={result} />
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

function OutputPanel({ running, result }) {
  const stdout = result?.stdout || "";
  const stderr = result?.stderr || "";
  const compileStderr = result?.compileStderr || "";
  const exitCode = result?.exitCode;
  const compileExitCode = result?.compileExitCode;

  const hasOutput = Boolean(stdout || stderr || compileStderr);
  const compileFailed = typeof compileExitCode === "number" && compileExitCode !== 0;
  const runFailed = typeof exitCode === "number" && exitCode !== 0;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-slate-500 dark:text-slate-400" />
          <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">Output</span>
        </div>
        {result && (
          <span
            className={
              compileFailed || runFailed
                ? "badge-danger tabular-nums"
                : "badge-success tabular-nums"
            }
          >
            exit {compileFailed ? `compile ${compileExitCode}` : (exitCode ?? "—")}
          </span>
        )}
      </div>

      {running ? (
        <div className="py-6 grid place-items-center">
          <Loader label="Running..." />
        </div>
      ) : !result ? (
        <div className="rounded-xl bg-slate-50 dark:bg-slate-800/60 ring-1 ring-slate-100 dark:ring-slate-700 p-4 text-sm text-slate-500 dark:text-slate-400">
          Run your code to see the output here.
        </div>
      ) : !hasOutput ? (
        <div className="rounded-xl bg-slate-50 dark:bg-slate-800/60 ring-1 ring-slate-100 dark:ring-slate-700 p-4 text-sm text-slate-500 dark:text-slate-400">
          (no output)
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {compileStderr && (
            <OutputBlock label="Compile errors" tone="danger" text={compileStderr} />
          )}
          {stdout && <OutputBlock label="stdout" tone="neutral" text={stdout} />}
          {stderr && <OutputBlock label="stderr" tone="warn" text={stderr} />}
        </div>
      )}
    </div>
  );
}

const DIFF_LABELS = ["", "Easy", "Easy-Medium", "Medium", "Hard", "Expert"];

function QuestionPicker({
  loading,
  items,
  totalCount,
  query,
  onQueryChange,
  onSelect,
  onClose,
}) {
  return (
    <div
      className="
        absolute right-0 mt-2 w-[min(28rem,90vw)] z-30
        rounded-2xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-700
        shadow-xl overflow-hidden animate-fade-in
      "
      role="dialog"
      aria-label="Pick a question"
    >
      <div className="flex items-center gap-2 p-3 border-b border-slate-100 dark:border-slate-800">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            autoFocus
            placeholder="Search by title, topic, or tag…"
            className="
              w-full pl-8 pr-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800
              ring-1 ring-slate-200 dark:ring-slate-700 text-sm
              text-slate-800 dark:text-slate-100
              placeholder:text-slate-400 dark:placeholder:text-slate-500
              focus:outline-none focus:ring-2 focus:ring-brand-500
            "
          />
        </div>
        <button
          type="button"
          onClick={onClose}
          className="btn-subtle !p-2"
          aria-label="Close picker"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="max-h-[60vh] overflow-y-auto">
        {loading ? (
          <div className="p-6 grid place-items-center">
            <Loader label="Loading questions..." />
          </div>
        ) : items.length === 0 ? (
          <div className="p-6 text-sm text-slate-500 dark:text-slate-400">
            {totalCount === 0
              ? "No questions available."
              : "No questions match that search."}
          </div>
        ) : (
          <ul className="py-1">
            {items.map((q) => (
              <li key={q.id}>
                <button
                  type="button"
                  onClick={() => onSelect(q)}
                  className="
                    w-full text-left px-4 py-3 flex items-start gap-3
                    hover:bg-slate-50 dark:hover:bg-slate-800/60
                    focus:outline-none focus:bg-slate-50 dark:focus:bg-slate-800/60
                  "
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                        {q.title || q.id}
                      </span>
                      {typeof q.difficulty === "number" && (
                        <span className="badge-neutral text-[10px]">
                          {DIFF_LABELS[q.difficulty] || `lvl ${q.difficulty}`}
                        </span>
                      )}
                      {q.topic && (
                        <span className="badge-brand text-[10px] capitalize">{q.topic}</span>
                      )}
                    </div>
                    <div className="mt-0.5 text-xs text-slate-400 dark:text-slate-500 font-mono">
                      {q.id}
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function OutputBlock({ label, tone, text }) {
  const toneClasses = {
    danger:
      "ring-rose-200 dark:ring-rose-800 bg-rose-50/70 dark:bg-rose-900/20 text-rose-900 dark:text-rose-100",
    warn:
      "ring-amber-200 dark:ring-amber-800 bg-amber-50/70 dark:bg-amber-900/20 text-amber-900 dark:text-amber-100",
    neutral:
      "ring-slate-200 dark:ring-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100",
  }[tone || "neutral"];

  return (
    <div className={`rounded-xl ring-1 p-3 ${toneClasses}`}>
      <div className="text-[11px] font-semibold uppercase tracking-wide opacity-70 mb-1.5">
        {label}
      </div>
      <pre className="font-mono text-xs leading-relaxed whitespace-pre-wrap break-words max-h-72 overflow-auto">
{text}
      </pre>
    </div>
  );
}
