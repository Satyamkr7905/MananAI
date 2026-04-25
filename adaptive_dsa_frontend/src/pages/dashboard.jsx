import dynamic from "next/dynamic";
import Link from "next/link";
import { Activity, ArrowRight, Award, BarChart3, CheckCircle2, Flame, Target, TrendingUp, XCircle } from "lucide-react";

import AppLayout from "@/components/AppLayout";
import StatsCard from "@/components/StatsCard";
import TopicCard from "@/components/TopicCard";
import Highlight from "@/components/Highlight";
import Loader from "@/components/Loader";
import EmptyState from "@/components/EmptyState";
import { useEffect, useMemo, useState } from "react";
import { useApi } from "@/hooks/useApi";
import { getStats, getUserImprovement, isRealBackendConfigured } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import { num, pct } from "@/utils/formatters";

const Graph = dynamic(() => import("@/components/Graph"), {
  ssr: false,
  loading: () => (
    <div className="h-64 grid place-items-center">
      <Loader size="sm" label="Loading chart…" />
    </div>
  ),
});

export default function Dashboard() {
  const { user } = useAuth();
  const [mockTick, setMockTick] = useState(0);
  useEffect(() => {
    const h = () => setMockTick((t) => t + 1);
    if (typeof window === "undefined") return;
    window.addEventListener("adt-mock-changed", h);
    return () => window.removeEventListener("adt-mock-changed", h);
  }, []);
  const { data, loading } = useApi(getStats);
  const useServer = useMemo(() => isRealBackendConfigured(), [mockTick]);
  const { data: imp, loading: impLoading } = useApi(getUserImprovement, { skip: !useServer, deps: [useServer] });

  const firstName = (user?.name || user?.email || "there").split(/\s|@/)[0];

  return (
    <AppLayout
      title={`Welcome back, ${firstName}`}
      subtitle="Here's how your learning is trending."
      actions={
        <Link href="/practice" className="btn-primary text-sm">
          Start practicing
          <ArrowRight className="h-4 w-4" />
        </Link>
      }
    >
      {loading || !data ? (
        <div className="card p-12 grid place-items-center">
          <Loader label="Loading your stats..." />
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {/* Stat cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatsCard
              label="Current streak"
              value={data.streak}
              suffix={data.streak === 1 ? "day" : "days"}
              delta="Keep it rolling — longest was 12 days"
              tone="warn"
              icon={Flame}
            />
            <StatsCard
              label="Questions solved"
              value={num(data.totalSolved)}
              delta="+4 this week"
              tone="brand"
              icon={BarChart3}
            />
            <StatsCard
              label="Accuracy"
              value={pct(data.accuracy)}
              delta="+6 pts vs. last week"
              tone="success"
              icon={Target}
            />
            <StatsCard
              label="Current level"
              value={data.level}
              suffix="/ 5"
              delta="Avg across topics"
              tone="neutral"
              icon={Award}
            />
          </div>

          {isRealBackendConfigured() && (imp || impLoading) && (
            <div className="card p-5">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <div className="section-title">Server improvement log</div>
                  <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mt-1">Recent attempts (AI + DB)</h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                    Signed-in practice is recorded so you can track accuracy in this window.
                  </p>
                </div>
                <Activity className="h-5 w-5 text-brand-600 shrink-0" />
              </div>
              {impLoading && !imp ? (
                <Loader size="sm" label="Loading activity…" />
              ) : imp?.summary && (
                <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600 dark:text-slate-300 mb-3">
                  <span>
                    <strong className="text-slate-900 dark:text-slate-100">{imp.summary.attemptsInWindow}</strong> attempts
                  </span>
                  {imp.summary.accuracyInWindow != null && (
                    <span>
                      · {pct(imp.summary.accuracyInWindow)} correct in this window
                    </span>
                  )}
                </div>
              )}
              {imp?.events?.length > 0 && (
                <ul className="divide-y divide-slate-100 dark:divide-slate-800 text-sm max-h-48 overflow-y-auto pr-1">
                  {imp.events.slice(0, 8).map((e) => {
                    const c = e.payload?.correct;
                    return (
                      <li key={e.id} className="py-2 flex items-center gap-2 text-slate-700 dark:text-slate-200">
                        {c ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                        ) : (
                          <XCircle className="h-4 w-4 text-rose-500 shrink-0" />
                        )}
                        <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
                          {e.payload?.questionId || e.type}
                        </span>
                        {e.at && (
                          <span className="ml-auto text-xs text-slate-400">
                            {new Date(e.at).toLocaleString()}
                          </span>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
              {imp && !impLoading && !imp.events?.length && (
                <p className="text-sm text-slate-500">Submit answers in Practice to build your log.</p>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Progress chart */}
            <div className="card p-5 lg:col-span-2">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="section-title">Progress</div>
                  <h2 className="text-lg font-semibold text-slate-900 mt-1">Accuracy over the last 14 days</h2>
                </div>
                <TrendingUp className="h-5 w-5 text-emerald-500" />
              </div>
              <Graph
                data={data.progressSeries.map((p) => ({ label: p.label, value: p.accuracy }))}
                formatter={(v) => `${Math.round(v * 100)}%`}
                yDomain={[0, 1]}
              />
            </div>

            {/* Highlights */}
            <div className="card p-5">
              <div className="section-title">Highlights</div>
              <h2 className="text-lg font-semibold text-slate-900 mt-1 mb-2">Recent wins</h2>
              {data.highlights.length === 0 ? (
                <EmptyState title="No highlights yet" description="Solve your first question to unlock achievements." />
              ) : (
                <ul className="divide-y divide-slate-100 -mt-1">
                  {data.highlights.map((h) => (
                    <li key={h.id}><Highlight item={h} /></li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Topic strength */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="section-title">Topic strength</div>
                <h2 className="text-lg font-semibold text-slate-900 mt-1">Where you stand per topic</h2>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.topics.map((t) => {
                const variant =
                  t.topic === data.strongest.topic ? "strongest" :
                  t.topic === data.weakest.topic   ? "weakest"   : null;
                return <TopicCard key={t.topic} topic={t} variant={variant} />;
              })}
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
