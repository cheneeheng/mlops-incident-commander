import { useQuery } from "@tanstack/react-query";

import EventFeed from "@/components/EventFeed";
import MetricChart, { type ChartPoint } from "@/components/MetricChart";
import QueryBoundary from "@/components/QueryBoundary";
import { api } from "@/lib/api";
import { POLL_INTERVAL_MS } from "@/lib/config";
import type { MetricWindow } from "@/lib/types";

const hhmmss = (iso: string) => new Date(iso).toLocaleTimeString();

function series(windows: MetricWindow[], pick: (w: MetricWindow) => number): ChartPoint[] {
  return windows.map((w) => ({ label: hhmmss(w.window_end), value: pick(w) }));
}

export default function Dashboard() {
  // Polling now (ITER_01); switches to SSE-driven invalidation in ITER_03.
  const q = useQuery({ queryKey: ["windows"], queryFn: api.listWindows, refetchInterval: POLL_INTERVAL_MS });
  const windows = q.data ?? [];

  return (
    <div>
      <h2>Live metrics</h2>
      <QueryBoundary isLoading={q.isLoading} isError={q.isError} error={q.error} isEmpty={windows.length === 0}>
        <div className="grid grid-2">
          <MetricChart title="Latency p95 (ms)" data={series(windows, (w) => w.latency_p95)} color="#4a9eff" />
          <MetricChart title="PSI score" data={series(windows, (w) => w.psi_score)} color="#f85149" />
          <MetricChart title="Prediction entropy" data={series(windows, (w) => w.prediction_entropy)} color="#d29922" />
          <MetricChart title="Mean confidence" data={series(windows, (w) => w.mean_confidence)} color="#3fb950" />
        </div>
      </QueryBoundary>
      <EventFeed />
    </div>
  );
}
