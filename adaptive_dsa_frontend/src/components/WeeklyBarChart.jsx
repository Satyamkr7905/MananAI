import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend as ReLegend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/**
 * WeeklyBarChart — last-7-days solved count.
 *
 * Extracted to its own file so recharts can be code-split out of the
 * analytics page first-load bundle via ``next/dynamic``.
 *
 * Props:
 *   data: [{ day, solved, accuracy? }]
 */
export default function WeeklyBarChart({ data = [] }) {
  return (
    <div className="h-64">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 10, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="day" stroke="#94a3b8" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
          <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} width={36} />
          <Tooltip
            cursor={{ fill: "#f1f5f9" }}
            contentStyle={{
              borderRadius: 12,
              border: "1px solid #e2e8f0",
              fontSize: 12,
              boxShadow: "0 4px 20px rgba(15,23,42,0.08)",
            }}
            formatter={(v, name) => (name === "solved" ? [v, "Solved"] : [`${Math.round(v * 100)}%`, "Accuracy"])}
          />
          <ReLegend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          <Bar dataKey="solved" fill="#6366f1" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
