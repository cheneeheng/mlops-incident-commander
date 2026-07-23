"""Incident reads. Stub at SKELETON; real queries land in ITER_02."""

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Incident


async def list_incidents(db: AsyncSession) -> list[Incident]:
    return []  # stub — real query in ITER_02


async def get_incident(db: AsyncSession, incident_id: str) -> Incident | None:
    return None  # stub — real query in ITER_02
