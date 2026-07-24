"""Shared JSON serializers for the MCP tool servers. Datetimes become ISO strings so tool results
are directly JSON-serializable.

Note: deploy_dict deliberately omits `is_faulty` — that column is hidden ground truth for the
injection harness. The diagnosis agent must infer a bad deploy from metrics, never read the flag.
"""

from backend.app.db.models import Deploy, MetricWindow, ServingLog


def window_dict(w: MetricWindow) -> dict:
    return {
        "id": w.id,
        "window_start": w.window_start.isoformat(),
        "window_end": w.window_end.isoformat(),
        "request_count": w.request_count,
        "latency_p50": w.latency_p50,
        "latency_p95": w.latency_p95,
        "latency_p99": w.latency_p99,
        "mean_confidence": w.mean_confidence,
        "prediction_entropy": w.prediction_entropy,
        "psi_score": w.psi_score,
        "class_distribution": w.class_distribution,
    }


def deploy_dict(d: Deploy) -> dict:
    return {
        "model_version": d.model_version,
        "artifact_path": d.artifact_path,
        "deployed_at": d.deployed_at.isoformat(),
        "is_active": d.is_active,
    }


def serving_log_dict(row: ServingLog) -> dict:
    return {
        "ts": row.ts.isoformat(),
        "level": row.level,
        "message": row.message,
        "context": row.context,
    }
