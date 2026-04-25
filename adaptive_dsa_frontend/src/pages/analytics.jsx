import dynamic from "next/dynamic";
import { BarChart3, PieChart as PieIcon, TrendingUp } from "lucide-react";

import AppLayout from "@/components/AppLayout";
import Loader from "@/components/Loader";
import EmptyState from "@/components/EmptyState";
import { useApi } from "@/hooks/useApi";
import { getAnalytics } from "@/services/api";
import { ERROR_LABELS } from "@/utils/constants";

// Recharts is ~150KB. All three chart pieces are lazy-loaded so the
// analytics page HTML and stat panels paint before the chart bundle.
const chartFallback = (
  <div className="h-64 grid place-items-center">
    <Loader size="sm" label="Loading chart…" />
  </div>
);
const Graph = dynamic(() => import("@/components/Graph"), {
  ssr: false,
  loading: () => chartFallback,
});
const PieChart = dynamic(() => import("@/components/PieChart"), {
  ssr: false,
  loading: () => chartFallback,
});
const WeeklyBarChart = dynamic(() => import("@/components/WeeklyBarChart"), {
  ssr: false,
  loading: () => chartFallback,
});

export default function Analytics() {
  const { data, loading } = useApi(getAnalytics);

  if (loading || !data) {
    return (
      <AppLayout title="Analytics" subtitle="Understand your patterns — where you stumble and where you shine.">
        <div className="card p-12 grid place-items-center">
          <Loader label="Crunching your numbers..." />
        </div>
      </AppLayout>
    );
  }

  const mistakes = data.mistakeBreakdown || [];
  const weekly = data.weekly || [];
  const trend = data.accuracyTrend || [];

  const totalMistakes = mistakes.reduce((s, d) => s + d.count, 0);

  return (
    <AppLayout title="Analytics" subtitle="Understand your patterns — where you stumble and where you shine.">
      <div className="flex flex-col gap-6">
        {/* Top row: mistake pie + its legend table */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="card p-5 lg:col-span-3">
            <div className="flex items-center justify-between mb-2">
              <div>
                <div className="section-title">Mistake breakdown</div>
                <h2 className="text-lg font-semibold text-slate-900 mt-1">What's tripping you up</h2>
              </div>
              <PieIcon className="h-5 w-5 text-slate-400" />
            </div>
            {mistakes.length === 0 ? (
              <EmptyState title="No mistakes tracked yet" description="Your breakdown will appear after your first few attempts." />
            ) : (
              <PieChart data={mistakes} />
            )}
          </div>

          <div className="card p-5 lg:col-span-2">
            <div className="section-title">Top categories</div>
            <h2 className="text-lg font-semibold text-slate-900 mt-1 mb-3">By frequency</h2>
            <ul className="flex flex-col gap-3">
              {mistakes.length === 0 && <li className="text-sm text-slate-500">Nothing recorded yet.</li>}
              {mistakes.map((m) => {
                const p = totalMistakes ? m.count / totalMistakes : 0;
                return (
                  <li key={m.key} className="flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-700">{ERROR_LABELS[m.key] || m.key}</span>
                        <span className="text-xs text-slate-500 tabular-nums">{m.count} · {Math.round(p * 100)}%</span>
                      </div>
                      <div className="mt-1.5 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-brand-500 rounded-full transition-all"
                          style={{ width: `${p * 100}%` }}
                        />
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>

        {/* Weekly + trend */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card p-5">
            <div className="flex items-center justify-between mb-2">
              <div>
                <div className="section-title">Weekly performance</div>
                <h2 className="text-lg font-semibold text-slate-900 mt-1">Solved per day (last 7)</h2>
              </div>
              <BarChart3 className="h-5 w-5 text-slate-400" />
            </div>
            <WeeklyBarChart data={weekly} />
          </div>

          <div className="card p-5">
            <div className="flex items-center justify-between mb-2">
              <div>
                <div className="section-title">Accuracy trend</div>
                <h2 className="text-lg font-semibold text-slate-900 mt-1">14-day rolling view</h2>
              </div>
              <TrendingUp className="h-5 w-5 text-emerald-500" />
            </div>
            <Graph
              data={trend.map((p) => ({ label: p.label, value: p.accuracy }))}
              formatter={(v) => `${Math.round(v * 100)}%`}
              yDomain={[0, 1]}
            />
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
