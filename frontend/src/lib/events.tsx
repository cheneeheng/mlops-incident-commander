import { useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import { USE_STUBS } from "@/lib/config";

export type FeedItem = { at: string; type: string; text: string };

// Each SSE event invalidates the React Query caches it can affect (prefix match), so pages refresh
// on server events instead of polling. Event names must match the backend's broker.publish() calls
// exactly — EventSource named-listener matching is not fuzzy.
const INVALIDATIONS: Record<string, readonly (readonly string[])[]> = {
  metrics_window: [["windows"]],
  incident_opened: [["incidents"]],
  hypothesis_ready: [["incidents"], ["incident"]],
  remediation_queued: [["approvals"], ["incidents"], ["incident"]],
  remediation_executed: [["approvals"], ["incidents"], ["incident"], ["postmortems"]],
  remediation_rejected: [["approvals"], ["incidents"], ["incident"]],
  postmortem_ready: [["postmortems"]],
};
const EVENT_TYPES = Object.keys(INVALIDATIONS);

const SAMPLE_FEED: FeedItem[] = [
  { at: "—", type: "incident_opened", text: "Incident #1002 opened (high)" },
  { at: "—", type: "metrics_window", text: "PSI crossed 0.3" },
];

const FeedContext = createContext<FeedItem[]>([]);
export const useEventFeed = (): FeedItem[] => useContext(FeedContext);

// The app's single SSE consumer (plan: one EventSource, one consumer). Mounted once in Layout: it
// opens the connection, invalidates the affected query caches on each event, and collects events for
// the feed display. The init is ref-guarded so StrictMode's double-mount opens exactly one
// connection; the stream lives for the page lifetime (Layout never unmounts), so there is
// deliberately no close-on-cleanup — closing here would kill the connection on StrictMode's first
// cleanup and leave the app with no live stream.
export function EventStreamProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [items, setItems] = useState<FeedItem[]>(USE_STUBS ? SAMPLE_FEED : []);
  const startedRef = useRef(false);

  useEffect(() => {
    if (USE_STUBS || startedRef.current) return;
    startedRef.current = true;

    const es = new EventSource("/api/events");
    const onEvent = (e: MessageEvent) => {
      for (const key of INVALIDATIONS[e.type] ?? []) {
        qc.invalidateQueries({ queryKey: key });
      }
      setItems((prev) =>
        [{ at: new Date().toLocaleTimeString(), type: e.type, text: e.data }, ...prev].slice(0, 50),
      );
    };
    for (const type of EVENT_TYPES) es.addEventListener(type, onEvent);
  }, [qc]);

  return <FeedContext.Provider value={items}>{children}</FeedContext.Provider>;
}
