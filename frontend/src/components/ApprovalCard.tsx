import type { Hypothesis, Remediation } from "@/lib/types";

// Presentational: renders a pending remediation and calls back on approve/reject.
export default function ApprovalCard({
  remediation,
  hypothesis,
  onApprove,
  onReject,
  pending,
}: {
  remediation: Remediation;
  hypothesis?: Hypothesis;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  pending: boolean;
}) {
  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <strong>{remediation.action_type}</strong>{" "}
          <span className={`badge ${remediation.risk}`}>{remediation.risk} risk</span>
        </div>
        <a href={`/incidents/${remediation.incident_id}`}>incident {remediation.incident_id}</a>
      </div>
      {remediation.rationale && (
        <p className="muted" style={{ margin: "8px 0" }}>
          {remediation.rationale}
        </p>
      )}
      {hypothesis && (
        <div className="muted" style={{ margin: "8px 0" }}>
          Diagnosis: {hypothesis.fault_type} ({(hypothesis.confidence * 100).toFixed(0)}% confidence)
        </div>
      )}
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button disabled={pending} onClick={() => onApprove(remediation.id)}>
          Approve
        </button>
        <button className="secondary" disabled={pending} onClick={() => onReject(remediation.id)}>
          Reject
        </button>
      </div>
    </div>
  );
}
