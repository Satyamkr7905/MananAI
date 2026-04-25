import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/**
 * Graph — line/area chart for a single metric over a time series.
 *
 * Props:
 *   data:      [{ label, value }]
 *   formatter: (n) => "75%" — optional, for tooltip / axis labels
 *   yDomain:   [min, max]
 */
export default function Graph({ data = [], formatter = (v) => v, yDomain }) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 10, right: 8, bottom: 0, left: -12 }}>
          <defs>
            <linearGradient id="gradBrand" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            stroke="#94a3b8"
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#94a3b8"
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            domain={yDomain}
            tickFormatter={formatter}
            width={48}
          />
          <Tooltip
            cursor={{ stroke: "#cbd5e1", strokeDasharray: "3 3" }}
            contentStyle={{
              borderRadius: 12,
              border: "1px solid #e2e8f0",
              fontSize: 12,
              boxShadow: "0 4px 20px rgba(15,23,42,0.08)",
            }}
            formatter={(v) => [formatter(v), ""]}
            labelStyle={{ color: "#475569", fontWeight: 500 }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#6366f1"
            strokeWidth={2.5}
            fill="url(#gradBrand)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
