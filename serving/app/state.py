"""Process-wide serving runtime cache. Single writer: the 5s poller in main.py, which reflects the
active deploy and active latency injection from the DB into these fields. Read by the latency
middleware and the /predict handler."""

from dataclasses import dataclass


@dataclass
class ServingState:
    added_latency_ms: float = 0.0
    active_model_version: str = ""


runtime = ServingState()
