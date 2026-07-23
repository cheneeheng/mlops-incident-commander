import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import QueryBoundary from "@/components/QueryBoundary";
import ScorecardTable from "@/components/ScorecardTable";
import { api } from "@/lib/api";

function pct(v: number | null): string {
  return v === null ? "—" : `${(v * 100).toFixed(0)}%`;
}

export default function Evals() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);
  const runs = useQuery({ queryKey: ["evalRuns"], queryFn: api.listEvalRuns });
  const detail = useQuery({
    queryKey: ["evalRun", selected],
    queryFn: () => api.getEvalRun(selected as string),
    enabled: selected !== null,
  });

  const start = useMutation({
    mutationFn: api.startEvalRun,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["evalRuns"] }),
  });

  const runList = runs.data ?? [];

  return (
    <div>
      <h2>Evaluation scorecards</h2>
      <div className="card">
        <button disabled={start.isPending} onClick={() => start.mutate()}>
          Run eval suite
        </button>
        <span className="muted" style={{ marginLeft: 12 }}>
          Replays the labeled scenario suite and scores detection, diagnosis, MTTD, and cost.
        </span>
      </div>

      <QueryBoundary isLoading={runs.isLoading} isError={runs.isError} error={runs.error} isEmpty={runList.length === 0} emptyLabel="No eval runs yet.">
        <div className="card overflow-x">
          <table>
            <thead>
              <tr>
                <th>Suite</th>
                <th>Started</th>
                <th>Recall</th>
                <th>Diagnosis acc</th>
                <th>Mean MTTD</th>
                <th>Mean cost</th>
              </tr>
            </thead>
            <tbody>
              {runList.map((r) => (
                <tr key={r.id} style={{ cursor: "pointer" }} onClick={() => setSelected(r.id)}>
                  <td>{r.suite_version}</td>
                  <td>{new Date(r.started_at).toLocaleString()}</td>
                  <td>{pct(r.detection_recall)}</td>
                  <td>{pct(r.diagnosis_accuracy)}</td>
                  <td>{r.mean_ttd_s?.toFixed(1) ?? "—"}s</td>
                  <td>{r.mean_cost_usd !== null ? `$${r.mean_cost_usd.toFixed(4)}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </QueryBoundary>

      {selected && (
        <div className="card">
          <strong>Run detail</strong>
          <QueryBoundary isLoading={detail.isLoading} isError={detail.isError} error={detail.error}>
            {detail.data && <ScorecardTable cases={detail.data.cases} />}
          </QueryBoundary>
        </div>
      )}
    </div>
  );
}
