"""Metric window queries. Stub at SKELETON; real aggregation reads land in ITER_01."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import MetricWindow


async def list_windows(db: AsyncSession, since: datetime | None) -> list[MetricWindow]:
    return []  # stub — real query in ITER_01
