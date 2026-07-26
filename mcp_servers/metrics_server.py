"""MCP stdio server: metric-window queries for the diagnosis agent. Read-only DB access.

Run standalone: python -m mcp_servers.metrics_server
"""

from datetime import datetime

from mcp.server.fastmcp import FastMCP

from backend.app.db.queries import get_windows_between
from backend.app.db.session import SessionLocal
from mcp_servers._common import window_dict

mcp = FastMCP("metrics")


@mcp.tool()
async def query_windows(start_iso: str, end_iso: str) -> list[dict]:
    """Return metric windows whose window_start falls in [start_iso, end_iso). Each has latency
    percentiles, mean confidence, prediction entropy, PSI, and the class distribution."""
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    async with SessionLocal() as db:
        windows = await get_windows_between(db, start, end)
    return [window_dict(w) for w in windows]


if __name__ == "__main__":
    mcp.run()
