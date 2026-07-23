"""Control plane FastAPI app: metrics, injections, deploys, incidents, remediations, postmortems,
evals, costs, and the SSE event stream."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.observability import CorrelationIdMiddleware, configure_logging, log
from backend.app.routers import (
    costs,
    deploys,
    evals,
    events,
    incidents,
    injections,
    metrics,
    postmortems,
    remediations,
)
from backend.app.tasks.aggregator import run_aggregator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log.info("control_plane_starting")
    # Metrics aggregator runs inside the control plane (stub loop at SKELETON, real 30s loop in ITER_01).
    aggregator_task = asyncio.create_task(run_aggregator())
    try:
        yield
    finally:
        aggregator_task.cancel()
        log.info("control_plane_stopping")


app = FastAPI(title="MLOps Incident Commander — Control Plane", lifespan=lifespan)

# gotcha (CORS registration order): the CORS middleware must be outermost, so it is added LAST
# (Starlette wraps later-added middleware on the outside). No cookies, so allow_credentials stays off.
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (
    metrics,
    injections,
    deploys,
    incidents,
    remediations,
    postmortems,
    evals,
    costs,
    events,
):
    app.include_router(module.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
