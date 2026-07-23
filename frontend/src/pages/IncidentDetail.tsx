import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import IncidentTimeline from "@/components/IncidentTimeline";
import QueryBoundary from "@/components/QueryBoundary";
import { api } from "@/lib/api";

export default function IncidentDetail() {
  const { id = "" } = useParams();
  const q = useQuery({ queryKey: ["incident", id], queryFn: () => api.getIncident(id) });

  return (
    <div>
      <h2>Incident detail</h2>
      <QueryBoundary isLoading={q.isLoading} isError={q.isError} error={q.error}>
        {q.data && (
          <>
            <div className="card">
              <strong>Incident #{q.data.number}</strong>{" "}
              <span className={`badge ${q.data.severity}`}>{q.data.severity}</span>{" "}
              <span className="muted">{q.data.status}</span>
            </div>
            <IncidentTimeline
              triggerMetrics={q.data.trigger_metrics}
              hypotheses={q.data.hypotheses}
              remediations={q.data.remediations}
              agentRuns={q.data.agent_runs}
            />
          </>
        )}
      </QueryBoundary>
    </div>
  );
}
