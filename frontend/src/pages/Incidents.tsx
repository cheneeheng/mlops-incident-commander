import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import QueryBoundary from "@/components/QueryBoundary";
import { api } from "@/lib/api";
import { POLL_INTERVAL_MS } from "@/lib/config";

export default function Incidents() {
  const q = useQuery({ queryKey: ["incidents"], queryFn: api.listIncidents, refetchInterval: POLL_INTERVAL_MS });
  const incidents = q.data ?? [];

  return (
    <div>
      <h2>Incidents</h2>
      <QueryBoundary isLoading={q.isLoading} isError={q.isError} error={q.error} isEmpty={incidents.length === 0} emptyLabel="No incidents yet.">
        <div className="card overflow-x">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Status</th>
                <th>Severity</th>
                <th>Opened</th>
                <th>Closed</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((i) => (
                <tr key={i.id}>
                  <td>
                    <Link to={`/incidents/${i.id}`}>#{i.number}</Link>
                  </td>
                  <td>{i.status}</td>
                  <td>
                    <span className={`badge ${i.severity}`}>{i.severity}</span>
                  </td>
                  <td>{new Date(i.opened_at).toLocaleString()}</td>
                  <td>{i.closed_at ? new Date(i.closed_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </QueryBoundary>
    </div>
  );
}
