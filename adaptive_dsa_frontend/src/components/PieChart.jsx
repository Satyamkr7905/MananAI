import {
  Cell,
  Legend,
  Pie,
  PieChart as RePieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { ERROR_COLORS, ERROR_LABELS } from "@/utils/constants";

/**
 * PieChart — mistake breakdown donut.
 * Each datum shape: { key: "off_by_one", count: 8 }
 */
export default function PieChart({ data = [] }) {
  const mapped = data.map((d) => ({
    ...d,
    label: ERROR_LABELS[d.key] || d.key,
    color: ERROR_COLORS[d.key] || "#94a3b8",
  }));
  const total = mapped.reduce((sum, d) => sum + d.count, 0);

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <RePieChart>
          <Pie
            data={mapped}
            dataKey="count"
            nameKey="label"
            innerRadius={55}
            outerRadius={90}
            paddingAngle={2}
            stroke="#fff"
            strokeWidth={2}
          >
            {mapped.map((entry) => (
              <Cell key={entry.key} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              borderRadius: 12,
              border: "1px solid #e2e8f0",
              fontSize: 12,
              boxShadow: "0 4px 20px rgba(15,23,42,0.08)",
            }}
            formatter={(value, _name, payload) => {
              const d = payload.payload;
              const pct = total ? `${Math.round((d.count / total) * 100)}%` : "";
              return [`${d.count}  (${pct})`, d.label];
            }}
          />
          <Legend
            verticalAlign="bottom"
            iconType="circle"
            wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
          />
        </RePieChart>
      </ResponsiveContainer>
    </div>
  );
}
