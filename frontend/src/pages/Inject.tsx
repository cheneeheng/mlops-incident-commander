import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import QueryBoundary from "@/components/QueryBoundary";
import { api } from "@/lib/api";
import { INJECTABLE_FAULTS, type InjectableFault } from "@/lib/types";

export default function Inject() {
  const qc = useQueryClient();
  const [fault, setFault] = useState<InjectableFault>("feature_drift");
  const q = useQuery({ queryKey: ["injections"], queryFn: api.listInjections });

  const create = useMutation({
    mutationFn: () => api.createInjection(fault, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["injections"] }),
  });
  const stop = useMutation({
    mutationFn: (id: string) => api.stopInjection(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["injections"] }),
  });

  const injections = q.data ?? [];
  const active = injections.filter((i) => i.ended_at === null);
  const past = injections.filter((i) => i.ended_at !== null);

  return (
    <div>
      <h2>Fault injection</h2>
      <div className="card">
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <select value={fault} onChange={(e) => setFault(e.target.value as InjectableFault)}>
            {INJECTABLE_FAULTS.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
          <button disabled={create.isPending} onClick={() => create.mutate()}>
            Inject fault
          </button>
        </div>
        {create.isError && <div className="state">Failed to inject.</div>}
      </div>

      <QueryBoundary isLoading={q.isLoading} isError={q.isError} error={q.error}>
        <div className="card">
          <strong>Active injections</strong>
          {active.length === 0 && <div className="muted">None active.</div>}
          {active.map((i) => (
            <div key={i.id} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0" }}>
              <span>
                {i.fault_type} <span className="muted">(ground truth: {i.ground_truth_fault})</span>
              </span>
              <button className="secondary" disabled={stop.isPending} onClick={() => stop.mutate(i.id)}>
                Stop
              </button>
            </div>
          ))}
        </div>

        <div className="card overflow-x">
          <strong>Past injections</strong>
          <table>
            <thead>
              <tr>
                <th>Fault</th>
                <th>Ground truth</th>
                <th>Started</th>
                <th>Ended</th>
              </tr>
            </thead>
            <tbody>
              {past.map((i) => (
                <tr key={i.id}>
                  <td>{i.fault_type}</td>
                  <td>{i.ground_truth_fault}</td>
                  <td>{new Date(i.started_at).toLocaleTimeString()}</td>
                  <td>{i.ended_at ? new Date(i.ended_at).toLocaleTimeString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </QueryBoundary>
    </div>
  );
}
