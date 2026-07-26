import { useQuery } from "@tanstack/react-query";

import QueryBoundary from "@/components/QueryBoundary";
import { api } from "@/lib/api";
import type { CostBucket } from "@/lib/types";

function BucketTable({ title, buckets }: { title: string; buckets: CostBucket[] }) {
  return (
    <div className="card overflow-x">
      <strong>{title}</strong>
      <table>
        <thead>
          <tr>
            <th>Key</th>
            <th>Runs</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          {buckets.map((b) => (
            <tr key={b.key}>
              <td>{b.key}</td>
              <td>{b.run_count}</td>
              <td>${b.cost_usd.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Costs() {
  const q = useQuery({ queryKey: ["costs"], queryFn: api.costSummary });

  return (
    <div>
      <h2>Agent costs</h2>
      <QueryBoundary isLoading={q.isLoading} isError={q.isError} error={q.error}>
        {q.data && (
          <>
            <div className="card">
              <div className="muted">Total spend</div>
              <div style={{ fontSize: 28, fontWeight: 700 }}>${q.data.total_cost_usd.toFixed(4)}</div>
              <div className="muted">
                {q.data.by_incident.length > 0 &&
                  `~$${(q.data.total_cost_usd / q.data.by_incident.length).toFixed(4)} to triage each incident`}
              </div>
            </div>
            <div className="grid grid-2">
              <BucketTable title="By agent" buckets={q.data.by_agent} />
              <BucketTable title="By incident" buckets={q.data.by_incident} />
            </div>
            <BucketTable title="By day" buckets={q.data.by_day} />
          </>
        )}
      </QueryBoundary>
    </div>
  );
}
