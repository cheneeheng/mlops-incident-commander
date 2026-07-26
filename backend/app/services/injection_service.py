"""Injection harness: create/stop fault injections. Owns the transaction boundary (one commit per
mutation). fault_type is validated as injectable at the schema boundary (see InjectionCreate)."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import queries
from backend.app.db.models import Injection
from backend.app.domain.enums import FaultType
from backend.app.schemas import InjectionCreate

# The bad_deploy fault swaps the active model; stopping it reverts to the known-good version.
_BAD_VERSION = "v1.1-bad"
_GOOD_VERSION = "v1.0-good"


async def list_injections(db: AsyncSession) -> list[Injection]:
    return await queries.list_injections(db)


async def create_injection(db: AsyncSession, payload: InjectionCreate) -> Injection:
    injection = Injection(
        fault_type=payload.fault_type,
        params=payload.params,
        ground_truth_fault=payload.fault_type,
    )
    await queries.insert_injection(db, injection)
    if payload.fault_type == FaultType.BAD_DEPLOY:
        await queries.set_active_deploy(db, _BAD_VERSION)
    await db.commit()
    return injection


async def stop_injection(db: AsyncSession, injection_id: str) -> Injection | None:
    injection = await queries.get_injection(db, injection_id)
    if injection is None:
        return None
    if injection.ended_at is None:
        injection.ended_at = datetime.now(UTC)
        if injection.fault_type == FaultType.BAD_DEPLOY:
            await queries.set_active_deploy(db, _GOOD_VERSION)
        await db.commit()
    return injection
