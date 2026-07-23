import { useEffect, useRef, useState } from "react";

import { USE_STUBS } from "@/lib/config";

type FeedItem = { at: string; type: string; text: string };

// Live event feed backed by the SSE stream (ITER_03). StrictMode double-mounts effects, so the
// EventSource init is guarded with a ref to avoid opening two connections.
export default function EventFeed() {
  const [items, setItems] = useState<FeedItem[]>([]);
  const startedRef = useRef(false);

  useEffect(() => {
    if (USE_STUBS) {
      setItems([
        { at: new Date().toLocaleTimeString(), type: "incident", text: "Incident #1002 opened (high)" },
        { at: new Date().toLocaleTimeString(), type: "metric", text: "PSI crossed 0.3" },
      ]);
      return;
    }
    if (startedRef.current) return;
    startedRef.current = true;

    const es = new EventSource("/api/events");
    const onMessage = (e: MessageEvent) => {
      setItems((prev) => [{ at: new Date().toLocaleTimeString(), type: e.type, text: e.data }, ...prev].slice(0, 50));
    };
    for (const type of ["metric_window", "incident_opened", "hypothesis_ready", "remediation"]) {
      es.addEventListener(type, onMessage);
    }
    return () => es.close();
  }, []);

  return (
    <div className="card">
      <strong>Event feed</strong>
      <div style={{ marginTop: 8 }}>
        {items.length === 0 && <div className="muted">Waiting for events…</div>}
        {items.map((it, i) => (
          <div key={i} style={{ padding: "4px 0", borderBottom: "1px solid var(--border)" }}>
            <span className="muted">{it.at}</span> <span className="badge medium">{it.type}</span> {it.text}
          </div>
        ))}
      </div>
    </div>
  );
}
