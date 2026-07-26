"""In-process SSE event broker: fan-out from many producers to many client consumers.

gotcha (SSE heartbeat): a dedicated heartbeat producer pings every 15s so proxies don't drop idle
connections and the single consumer loop always has something to yield. Real event producers
(metrics window, incident opened, hypothesis ready, remediation queued/executed) publish in ITER_03.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

HEARTBEAT_SECONDS = 15


@dataclass
class EventBroker:
    _subscribers: set[asyncio.Queue[str]] = field(default_factory=set)

    def publish(self, event_type: str, data: dict) -> None:
        """Format one SSE frame and push to every subscriber (non-blocking, drops if full)."""
        frame = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        for q in self._subscribers:
            try:
                q.put_nowait(frame)
            except asyncio.QueueFull:
                pass

    async def subscribe(self) -> AsyncIterator[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        self._subscribers.add(q)
        try:
            while True:
                try:
                    yield await asyncio.wait_for(q.get(), timeout=HEARTBEAT_SECONDS)
                except TimeoutError:
                    yield ": heartbeat\n\n"  # SSE comment; keeps the connection warm
        finally:
            self._subscribers.discard(q)


# Single process-wide broker instance.
broker = EventBroker()
