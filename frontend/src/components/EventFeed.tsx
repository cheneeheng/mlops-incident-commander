import { useEventFeed } from "@/lib/events";

// Live event feed backed by the app's single SSE stream (opened by EventStreamProvider in Layout).
export default function EventFeed() {
  const items = useEventFeed();

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
