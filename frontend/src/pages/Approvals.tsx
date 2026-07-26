import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import ApprovalCard from "@/components/ApprovalCard";
import QueryBoundary from "@/components/QueryBoundary";
import { api } from "@/lib/api";
import type { Hypothesis, Remediation } from "@/lib/types";

type PendingItem = { remediation: Remediation; hypothesis?: Hypothesis };

// No list-remediations endpoint exists (per API surface), so pending approvals are derived from
// incidents in `awaiting_approval` status by reading their details.
async function loadPending(): Promise<PendingItem[]> {
  const incidents = await api.listIncidents();
  const awaiting = incidents.filter((i) => i.status === "awaiting_approval");
  const details = await Promise.all(awaiting.map((i) => api.getIncident(i.id)));
  return details.flatMap((d) =>
    d.remediations
      .filter((r) => r.status === "pending")
      .map((r) => ({ remediation: r, hypothesis: d.hypotheses.find((h) => h.id === r.hypothesis_id) })),
  );
}

export default function Approvals() {
  const qc = useQueryClient();
  // SSE-driven: EventStreamProvider invalidates ["approvals"] on remediation queued/executed/rejected.
  const q = useQuery({ queryKey: ["approvals"], queryFn: loadPending });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["approvals"] });
  const approve = useMutation({ mutationFn: api.approveRemediation, onSuccess: invalidate });
  const reject = useMutation({ mutationFn: api.rejectRemediation, onSuccess: invalidate });
  const pending = approve.isPending || reject.isPending;

  const items = q.data ?? [];

  return (
    <div>
      <h2>Pending approvals</h2>
      <QueryBoundary isLoading={q.isLoading} isError={q.isError} error={q.error} isEmpty={items.length === 0} emptyLabel="No remediations awaiting approval.">
        {items.map((it) => (
          <ApprovalCard
            key={it.remediation.id}
            remediation={it.remediation}
            hypothesis={it.hypothesis}
            onApprove={(id) => approve.mutate(id)}
            onReject={(id) => reject.mutate(id)}
            pending={pending}
          />
        ))}
      </QueryBoundary>
    </div>
  );
}
