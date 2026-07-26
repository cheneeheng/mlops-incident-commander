"""Postmortem reads. Generation lives in the postmortem agent (agents/postmortem.py)."""

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import queries
from backend.app.db.models import Postmortem


async def list_postmortems(db: AsyncSession) -> list[Postmortem]:
    return await queries.list_postmortems(db)


async def get_postmortem(db: AsyncSession, postmortem_id: str) -> Postmortem | None:
    return await queries.get_postmortem(db, postmortem_id)
