"""Serving app: hosts the live image classifier under synthetic traffic."""

import base64

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from serving.app.middleware import LatencyInjectionMiddleware
from serving.app.model import classifier


class PredictIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_b64: str
    input_ref: str = "unknown"


class PredictOut(BaseModel):
    predicted_class: int
    confidence: float


app = FastAPI(title="MLOps Incident Commander — Serving")
app.add_middleware(LatencyInjectionMiddleware)


@app.post("/predict", response_model=PredictOut)
async def predict(payload: PredictIn) -> PredictOut:
    image_bytes = base64.b64decode(payload.image_b64)
    predicted_class, confidence = classifier.predict(image_bytes)
    # SKELETON: prediction is not yet logged; ITER_01 writes prediction_log + serving_log.
    return PredictOut(predicted_class=predicted_class, confidence=confidence)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "model_version": classifier.model_version}
