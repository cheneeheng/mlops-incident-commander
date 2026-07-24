"""MCP stdio server: serving-log search for the diagnosis agent. Read-only DB access.

Run standalone: python -m mcp_servers.logs_server
"""

from mcp.server.fastmcp import FastMCP

from backend.app.db.queries import search_serving_logs
from backend.app.db.session import SessionLocal
from mcp_servers._common import serving_log_dict

mcp = FastMCP("logs")


@mcp.tool()
async def search_logs(query: str, limit: int = 50) -> list[dict]:
    """Return serving-log rows whose message contains `query` (case-insensitive), newest first.
    Useful for confirming weight reloads, model-load events, and errors."""
    async with SessionLocal() as db:
        rows = await search_serving_logs(db, query, limit=min(limit, 200))
    return [serving_log_dict(row) for row in rows]


if __name__ == "__main__":
    mcp.run()
