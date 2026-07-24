"""Synthetic traffic generator: samples CIFAR-10 test images at ~5 req/s, applies the active
injection transforms (feature_drift = brightness/noise shift; label_skew = altered class mix), and
POSTs each to the serving app's /predict.

Runs inside the serving process (it targets the serving app), started by serving/app/main.py. It
records nothing itself — ground truth lives on the injection row; prediction_log is written by
/predict.
"""

import asyncio
import base64
import io
import random
from collections import defaultdict

import httpx
import numpy as np
from PIL import Image
from torchvision.datasets import CIFAR10

from backend.app.config import get_settings
from backend.app.db.models import Injection
from backend.app.db.queries import get_active_injections
from backend.app.db.session import SessionLocal
from backend.app.domain.enums import FaultType
from backend.app.observability import log

_DATA_ROOT = "data"
_REQ_INTERVAL_S = 0.2  # ~5 req/s
_rng = random.Random()


def _apply_feature_drift(img: Image.Image, params: dict[str, float]) -> Image.Image:
    """Brightness offset + additive Gaussian noise, in normalized [0, 1] space."""
    brightness = float(params.get("brightness", 0.0))
    noise = float(params.get("noise", 0.0))
    if brightness == 0.0 and noise == 0.0:
        return img
    arr = np.asarray(img, dtype=np.float32) / 255.0
    if brightness:
        arr = arr + brightness
    if noise:
        arr = arr + _rng_normal(noise, arr.shape)
    arr = np.clip(arr, 0.0, 1.0)
    return Image.fromarray((arr * 255.0).astype(np.uint8))


def _rng_normal(std: float, shape: tuple[int, ...]) -> np.ndarray:
    return np.random.normal(0.0, std, shape).astype(np.float32)


def _choose_index(by_class: dict[int, list[int]], skew: list[Injection], n: int) -> int:
    """Under an active label_skew, draw from the skewed class with probability `fraction`."""
    if skew:
        params = skew[0].params
        cls = int(params.get("class", 0))
        fraction = float(params.get("fraction", 0.7))
        if _rng.random() < fraction and by_class.get(cls):
            return _rng.choice(by_class[cls])
    return _rng.randrange(n)


def _encode_png(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


async def run_traffic_generator() -> None:
    settings = get_settings()
    # Blocking one-time load/download; keep it off the event loop.
    dataset = await asyncio.to_thread(CIFAR10, root=_DATA_ROOT, train=False, download=True)
    by_class: dict[int, list[int]] = defaultdict(list)
    for idx, label in enumerate(dataset.targets):
        by_class[int(label)].append(idx)
    n = len(dataset)
    log.info("traffic_generator_started", dataset_size=n, serving_url=settings.serving_url)

    async with httpx.AsyncClient(base_url=settings.serving_url, timeout=10.0) as client:
        while True:
            try:
                async with SessionLocal() as db:
                    active = await get_active_injections(db)
                skew = [i for i in active if i.fault_type == FaultType.LABEL_SKEW]
                drift = [i for i in active if i.fault_type == FaultType.FEATURE_DRIFT]

                idx = _choose_index(by_class, skew, n)
                img, _ = dataset[idx]
                if drift:
                    img = _apply_feature_drift(img, drift[0].params)

                await client.post(
                    "/predict",
                    json={"image_b64": _encode_png(img), "input_ref": f"cifar_test_{idx}"},
                )
            except Exception as exc:  # keep the generator alive across transient errors
                log.error("traffic_error", error=repr(exc))
            await asyncio.sleep(_REQ_INTERVAL_S)
