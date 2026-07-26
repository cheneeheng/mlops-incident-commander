"""Serving app: hosts the live image classifier under synthetic traffic.

Lifespan loads the active deploy's weights, starts a 5s poller (reflects the active deploy + active
latency injection from the DB into serving.app.state, reloading weights on a version change), and
starts the traffic generator. /predict runs the CNN and logs to prediction_log.
"""

import asyncio
import base64
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import PredictionLog, ServingLog
from backend.app.db.queries import (
    get_active_deploy,
    get_active_injections,
    insert_prediction,
    insert_serving_log,
)
from backend.app.db.session import SessionLocal, get_db
from backend.app.domain.enums import FaultType
from backend.app.observability import configure_logging, log
from backend.app.tasks.traffic import run_traffic_generator
from serving.app import state
from serving.app.middleware import LatencyInjectionMiddleware
from serving.app.model import classifier

_POLL_INTERVAL_S = 5.0


class PredictIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_b64: str
    input_ref: str = "unknown"


class PredictOut(BaseModel):
    predicted_class: int
    confidence: float


async def _poll_active_state() -> None:
    """Every 5s: reload weights if the active deploy version changed, and refresh the injected
    latency from active latency injections."""
    while True:
        try:
            async with SessionLocal() as db:
                deploy = await get_active_deploy(db)
                if deploy is not None and deploy.model_version != state.runtime.active_model_version:
                    classifier.load_active(deploy.model_version, deploy.artifact_path)
                    state.runtime.active_model_version = deploy.model_version
                    await insert_serving_log(
                        db,
                        ServingLog(
                            level="info",
                            message="weights_reloaded",
                            context={"model_version": deploy.model_version},
                        ),
                    )
                    await db.commit()
                    log.info("weights_reloaded", model_version=deploy.model_version)

                injections = await get_active_injections(db)
                state.runtime.added_latency_ms = sum(
                    float(inj.params.get("added_latency_ms", 0.0))
                    for inj in injections
                    if inj.fault_type == FaultType.LATENCY
                )
        except Exception as exc:  # keep the poller alive across transient DB errors
            log.error("poller_error", error=repr(exc))
        await asyncio.sleep(_POLL_INTERVAL_S)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log.info("serving_starting")
    async with SessionLocal() as db:
        deploy = await get_active_deploy(db)
        if deploy is not None:
            classifier.load_active(deploy.model_version, deploy.artifact_path)
            state.runtime.active_model_version = deploy.model_version
            await insert_serving_log(
                db,
                ServingLog(
                    level="info",
                    message="model_loaded",
                    context={"model_version": deploy.model_version},
                ),
            )
            await db.commit()
            log.info("model_loaded", model_version=deploy.model_version)
        else:
            log.warning("no_active_deploy_at_startup")

    poller = asyncio.create_task(_poll_active_state())
    traffic = asyncio.create_task(run_traffic_generator())
    try:
        yield
    finally:
        poller.cancel()
        traffic.cancel()
        log.info("serving_stopping")


app = FastAPI(title="MLOps Incident Commander — Serving", lifespan=lifespan)
app.add_middleware(LatencyInjectionMiddleware)


@app.post("/predict", response_model=PredictOut)
async def predict(payload: PredictIn, db: AsyncSession = Depends(get_db)) -> PredictOut:
    image_bytes = base64.b64decode(payload.image_b64)
    started = time.perf_counter()
    predicted_class, confidence = classifier.predict(image_bytes)
    inference_ms = (time.perf_counter() - started) * 1000.0
    # Logged latency reflects what the request incurred (inference + injected latency), so the
    # aggregator's p95 rises under a latency injection. See DECISION_LOG entry 3.
    await insert_prediction(
        db,
        PredictionLog(
            model_version=classifier.model_version,
            predicted_class=predicted_class,
            confidence=confidence,
            latency_ms=inference_ms + state.runtime.added_latency_ms,
            input_ref=payload.input_ref,
        ),
    )
    await db.commit()
    return PredictOut(predicted_class=predicted_class, confidence=confidence)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "model_version": classifier.model_version}
