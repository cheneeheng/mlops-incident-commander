import type { EvalCase } from "@/lib/types";

const yn = (v: boolean | null) => (v === null ? "—" : v ? "yes" : "no");

// The interview results table: per-case detection / diagnosis / TTD / cost.
export default function ScorecardTable({ cases }: { cases: EvalCase[] }) {
  return (
    <div className="overflow-x">
      <table>
        <thead>
          <tr>
            <th>Scenario</th>
            <th>Injected fault</th>
            <th>Detected</th>
            <th>Diagnosis correct</th>
            <th>TTD (s)</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.id}>
              <td>
                <a href={`#${c.id}`}>{c.scenario_name}</a>
              </td>
              <td>{c.injected_fault}</td>
              <td>{yn(c.detected)}</td>
              <td>{yn(c.diagnosis_correct)}</td>
              <td>{c.ttd_seconds?.toFixed(1) ?? "—"}</td>
              <td>{c.cost_usd !== null ? `$${c.cost_usd.toFixed(4)}` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
