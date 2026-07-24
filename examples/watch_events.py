#!/usr/bin/env python
"""Tail the control plane's live SSE stream — the same feed the dashboard consumes.

Run this in one shell, then trigger activity in another (e.g. examples/incident_lifecycle.py) to
watch incident_opened / hypothesis_ready / remediation_queued / remediation_executed frames arrive
in real time. Ctrl-C to stop.

    uv run python examples/watch_events.py
"""

import os

import httpx

BASE_URL = os.environ.get("ICC_BASE_URL", "http://localhost:8000")


def main() -> None:
    print(f"Streaming {BASE_URL}/api/events  (Ctrl-C to stop)\n")
    with httpx.stream("GET", f"{BASE_URL}/api/events", timeout=None) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line:  # skip the blank frame separators; ':' lines are heartbeat comments
                print(line, flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped.")
