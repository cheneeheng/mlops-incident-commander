"""Metrics aggregator: every 30s, roll up the last window of prediction_log into a metric_window
(latency percentiles, mean confidence, prediction entropy, class distribution, PSI vs the reference
profile). Posting windows into the agent graph lands in ITER_02."""

import asyncio
import math
from datetime import UTC, datetime, timedelta

import numpy as np

from backend.app.db.models import MetricWindow
from backend.app.db.queries import (
    get_predictions_between,
    get_reference_profile,
    insert_metric_window,
)
from backend.app.db.session import SessionLocal
from backend.app.observability import log

_WINDOW_S = 30.0
_NUM_CLASSES = 10  # CIFAR-10; kept local so the control plane doesn't import the serving CNN stack.
_EPS = 1e-6


def _class_distribution(classes: list[int]) -> dict[str, float]:
    counts = np.bincount(classes, minlength=_NUM_CLASSES)[:_NUM_CLASSES]
    total = float(counts.sum())
    return {str(i): float(counts[i]) / total for i in range(_NUM_CLASSES)}


def _entropy(distribution: dict[str, float]) -> float:
    return float(-sum(p * math.log(p) for p in distribution.values() if p > 0.0))


def _psi(actual: dict[str, float], expected: dict[str, float]) -> float:
    """Population Stability Index across class bins; eps-floored to stay finite on empty bins."""
    score = 0.0
    for key in expected:
        a = max(actual.get(key, 0.0), _EPS)
        e = max(expected.get(key, 0.0), _EPS)
        score += (a - e) * math.log(a / e)
    return float(score)


async def _compute_window() -> None:
    window_end = datetime.now(UTC)
    window_start = window_end - timedelta(seconds=_WINDOW_S)
    async with SessionLocal() as db:
        predictions = await get_predictions_between(db, window_start, window_end)
        if not predictions:
            log.debug("aggregator_empty_window")
            return

        latencies = np.array([p.latency_ms for p in predictions], dtype=np.float64)
        confidences = np.array([p.confidence for p in predictions], dtype=np.float64)
        classes = [p.predicted_class for p in predictions]
        model_version = predictions[-1].model_version

        distribution = _class_distribution(classes)
        reference = await get_reference_profile(db, model_version)
        if reference is None:
            reference = await get_reference_profile(db, "v1.0-good")
        psi = _psi(distribution, reference.class_distribution) if reference is not None else 0.0

        window = MetricWindow(
            window_start=window_start,
            window_end=window_end,
            request_count=len(predictions),
            latency_p50=float(np.percentile(latencies, 50)),
            latency_p95=float(np.percentile(latencies, 95)),
            latency_p99=float(np.percentile(latencies, 99)),
            mean_confidence=float(confidences.mean()),
            prediction_entropy=_entropy(distribution),
            psi_score=psi,
            class_distribution=distribution,
        )
        await insert_metric_window(db, window)
        await db.commit()
        log.info(
            "metric_window_written",
            request_count=len(predictions),
            latency_p95=window.latency_p95,
            psi=psi,
            mean_confidence=window.mean_confidence,
        )


async def run_aggregator() -> None:
    while True:
        try:
            await _compute_window()
        except Exception as exc:  # keep the loop alive across transient DB errors
            log.error("aggregator_error", error=repr(exc))
        await asyncio.sleep(_WINDOW_S)
