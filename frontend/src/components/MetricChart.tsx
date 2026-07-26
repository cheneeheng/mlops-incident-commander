import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// Chart axis config kept at module level (stable-reference gotcha — no new object identity per render).
const AXIS = { stroke: "#8b98a5", fontSize: 11 } as const;
const GRID = "#2d3742";

export type ChartPoint = { label: string; value: number };

export default function MetricChart({
  title,
  data,
  color = "#4a9eff",
  unit = "",
}: {
  title: string;
  data: ChartPoint[];
  color?: string;
  unit?: string;
}) {
  return (
    <div className="card">
      <div className="muted" style={{ marginBottom: 8 }}>
        {title}
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid stroke={GRID} strokeDasharray="3 3" />
          <XAxis dataKey="label" tick={AXIS} />
          <YAxis tick={AXIS} unit={unit} />
          <Tooltip contentStyle={{ background: "#1a212b", border: "1px solid #2d3742" }} />
          <Line type="monotone" dataKey="value" stroke={color} dot={false} strokeWidth={2} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
