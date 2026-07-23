"""Data-access layer: all SQL lives here. No business logic. Functions never commit — the calling
service owns the transaction boundary (one commit per request)."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Deploy,
    Injection,
    MetricWindow,
    PredictionLog,
    ReferenceProfile,
    ServingLog,
)

# ---- deploys ---------------------------------------------------------------
async def list_deploys(db: AsyncSession) -> list[Deploy]:
    rows = await db.scalars(select(Deploy).order_by(Deploy.deployed_at.desc()))
    return list(rows)


async def get_active_deploy(db: AsyncSession) -> Deploy | None:
    return await db.scalar(select(Deploy).where(Deploy.is_active.is_(True)))


async def get_deploy_by_version(db: AsyncSession, model_version: str) -> Deploy | None:
    return await db.scalar(select(Deploy).where(Deploy.model_version == model_version))


async def set_active_deploy(db: AsyncSession, model_version: str) -> Deploy | None:
    """Flip the active flag to the named version (deactivating all others). Returns it, or None."""
    target = await get_deploy_by_version(db, model_version)
    if target is None:
        return None
    await db.execute(update(Deploy).values(is_active=False))
    target.is_active = True
    await db.flush()
    return target


# ---- injections ------------------------------------------------------------
async def list_injections(db: AsyncSession) -> list[Injection]:
    rows = await db.scalars(select(Injection).order_by(Injection.started_at.desc()))
    return list(rows)


async def get_injection(db: AsyncSession, injection_id: str) -> Injection | None:
    return await db.get(Injection, injection_id)


async def get_active_injections(db: AsyncSession) -> list[Injection]:
    rows = await db.scalars(select(Injection).where(Injection.ended_at.is_(None)))
    return list(rows)


async def insert_injection(db: AsyncSession, injection: Injection) -> Injection:
    db.add(injection)
    await db.flush()
    return injection


# ---- reference profile -----------------------------------------------------
async def get_reference_profile(db: AsyncSession, model_version: str) -> ReferenceProfile | None:
    return await db.scalar(
        select(ReferenceProfile).where(ReferenceProfile.model_version == model_version)
    )


# ---- prediction / serving logs (written by the serving process) ------------
async def insert_prediction(db: AsyncSession, row: PredictionLog) -> None:
    db.add(row)


async def insert_serving_log(db: AsyncSession, row: ServingLog) -> None:
    db.add(row)


async def get_predictions_between(
    db: AsyncSession, start: datetime, end: datetime
) -> list[PredictionLog]:
    rows = await db.scalars(
        select(PredictionLog).where(PredictionLog.ts >= start, PredictionLog.ts < end)
    )
    return list(rows)


# ---- metric windows --------------------------------------------------------
async def insert_metric_window(db: AsyncSession, row: MetricWindow) -> MetricWindow:
    db.add(row)
    await db.flush()
    return row


async def list_windows(db: AsyncSession, since: datetime | None) -> list[MetricWindow]:
    stmt = select(MetricWindow).order_by(MetricWindow.window_start.asc())
    if since is not None:
        stmt = stmt.where(MetricWindow.window_start >= since)
    rows = await db.scalars(stmt)
    return list(rows)
