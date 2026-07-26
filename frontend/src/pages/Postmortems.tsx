import { useQuery } from "@tanstack/react-query";

import QueryBoundary from "@/components/QueryBoundary";
import { api } from "@/lib/api";

export default function Postmortems() {
  const q = useQuery({ queryKey: ["postmortems"], queryFn: api.listPostmortems });
  const postmortems = q.data ?? [];

  return (
    <div>
      <h2>Postmortems</h2>
      <QueryBoundary isLoading={q.isLoading} isError={q.isError} error={q.error} isEmpty={postmortems.length === 0} emptyLabel="No postmortems yet.">
        {postmortems.map((p) => (
          <div key={p.id} className="card">
            <div className="muted" style={{ marginBottom: 8 }}>
              <a href={`/incidents/${p.incident_id}`}>incident {p.incident_id}</a> ·{" "}
              {new Date(p.created_at).toLocaleString()}
            </div>
            {/* less-code: markdown rendered as preformatted text; upgrade to react-markdown if rich rendering is needed. */}
            <pre style={{ whiteSpace: "pre-wrap" }}>{p.body_md}</pre>
          </div>
        ))}
      </QueryBoundary>
    </div>
  );
}
