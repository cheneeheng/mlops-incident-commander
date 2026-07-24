"""Deploy history + activation. Owns the transaction boundary (one commit per mutation)."""

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import queries
from backend.app.db.models import Deploy


async def list_deploys(db: AsyncSession) -> list[Deploy]:
    return await queries.list_deploys(db)


async def activate(db: AsyncSession, model_version: str) -> Deploy | None:
    deploy = await queries.set_active_deploy(db, model_version)
    if deploy is not None:
        await db.commit()
    return deploy
