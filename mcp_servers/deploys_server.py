"""MCP stdio server: deploy history + active version for the diagnosis agent. Read-only DB access.
Deliberately never exposes is_faulty (hidden ground truth).

Run standalone: python -m mcp_servers.deploys_server
"""

from mcp.server.fastmcp import FastMCP

from backend.app.db.queries import get_active_deploy, list_deploys
from backend.app.db.session import SessionLocal
from mcp_servers._common import deploy_dict

mcp = FastMCP("deploys")


@mcp.tool()
async def deploy_history() -> list[dict]:
    """Return all deploys, newest first: model_version, artifact_path, deployed_at, is_active."""
    async with SessionLocal() as db:
        deploys = await list_deploys(db)
    return [deploy_dict(d) for d in deploys]


@mcp.tool()
async def active_deploy() -> dict | None:
    """Return the currently active deploy, or null if none is active."""
    async with SessionLocal() as db:
        deploy = await get_active_deploy(db)
    return deploy_dict(deploy) if deploy is not None else None


if __name__ == "__main__":
    mcp.run()
