import type { AgentRun, Hypothesis, Remediation } from "@/lib/types";

// Renders the incident story: trigger -> hypotheses (with confidence + evidence) -> remediations -> agent runs.
export default function IncidentTimeline({
  triggerMetrics,
  hypotheses,
  remediations,
  agentRuns,
}: {
  triggerMetrics: Record<string, unknown>;
  hypotheses: Hypothesis[];
  remediations: Remediation[];
  agentRuns: AgentRun[];
}) {
  return (
    <div>
      <div className="card">
        <strong>Trigger metrics</strong>
        <pre>{JSON.stringify(triggerMetrics, null, 2)}</pre>
      </div>

      {hypotheses.map((h) => (
        <div key={h.id} className="card">
          <strong>Hypothesis ({h.kind})</strong> — {h.fault_type}{" "}
          <span className="muted">confidence {(h.confidence * 100).toFixed(0)}%</span>
          <div className="muted" style={{ marginTop: 6 }}>
            Evidence:
          </div>
          <pre>{JSON.stringify(h.evidence, null, 2)}</pre>
        </div>
      ))}

      {remediations.map((r) => (
        <div key={r.id} className="card">
          <strong>Remediation</strong> — {r.action_type}{" "}
          <span className={`badge ${r.risk}`}>{r.risk} risk</span>{" "}
          <span className="muted">{r.status}</span>
        </div>
      ))}

      <div className="card">
        <strong>Agent runs</strong>
        <div className="overflow-x">
          <table>
            <thead>
              <tr>
                <th>Agent</th>
                <th>Model</th>
                <th>Tokens</th>
                <th>Cost</th>
                <th>Latency</th>
              </tr>
            </thead>
            <tbody>
              {agentRuns.map((a) => (
                <tr key={a.id}>
                  <td>{a.agent_name}</td>
                  <td>{a.model}</td>
                  <td>{a.input_tokens + a.output_tokens}</td>
                  <td>${a.cost_usd.toFixed(4)}</td>
                  <td>{a.latency_ms.toFixed(0)} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
