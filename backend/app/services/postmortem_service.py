"""Postmortem reads + retrieval. Stub at SKELETON; real logic in ITER_04."""

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Postmortem


async def list_postmortems(db: AsyncSession) -> list[Postmortem]:
    return []  # stub — real query in ITER_04


async def get_postmortem(db: AsyncSession, postmortem_id: str) -> Postmortem | None:
    return None  # stub — real query in ITER_04
