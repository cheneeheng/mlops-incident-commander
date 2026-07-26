"""MCP stdio server: prediction-distribution stats for the diagnosis agent. Read-only DB access.
Aggregates the per-window class distributions and PSI already computed by the aggregator, and
returns the clean-baseline reference for comparison.

Run standalone: python -m mcp_servers.preddist_server
"""

from datetime import datetime

from mcp.server.fastmcp import FastMCP

from backend.app.db.models import ReferenceProfile
from backend.app.db.queries import get_reference_profile, get_windows_between
from backend.app.db.session import SessionLocal

mcp = FastMCP("preddist")

_NUM_CLASSES = 10


@mcp.tool()
async def prediction_distribution(start_iso: str, end_iso: str) -> dict:
    """Aggregate prediction-distribution stats over metric windows in [start_iso, end_iso):
    window count, mean/max PSI, mean confidence, mean entropy, the averaged class distribution, and
    the clean-baseline reference distribution to compare against."""
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    async with SessionLocal() as db:
        windows = await get_windows_between(db, start, end)
        reference = await get_reference_profile(db, "v1.0-good")

    if not windows:
        return {"n_windows": 0, "reference_class_distribution": _ref_dist(reference)}

    psi = [w.psi_score for w in windows]
    avg_dist = {
        str(c): sum(w.class_distribution.get(str(c), 0.0) for w in windows) / len(windows)
        for c in range(_NUM_CLASSES)
    }
    return {
        "n_windows": len(windows),
        "mean_psi": sum(psi) / len(psi),
        "max_psi": max(psi),
        "mean_confidence": sum(w.mean_confidence for w in windows) / len(windows),
        "mean_entropy": sum(w.prediction_entropy for w in windows) / len(windows),
        "avg_class_distribution": avg_dist,
        "reference_class_distribution": _ref_dist(reference),
    }


def _ref_dist(reference: ReferenceProfile | None) -> dict | None:
    return reference.class_distribution if reference is not None else None


if __name__ == "__main__":
    mcp.run()
