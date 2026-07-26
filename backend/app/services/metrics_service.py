"""Metric window reads. No mutation, so no commit."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import queries
from backend.app.db.models import MetricWindow


async def list_windows(db: AsyncSession, since: datetime | None) -> list[MetricWindow]:
    return await queries.list_windows(db, since)
