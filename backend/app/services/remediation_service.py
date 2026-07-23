"""Remediation approval flow. Stub at SKELETON; real logic + idempotency in ITER_03."""

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Remediation


async def approve(db: AsyncSession, remediation_id: str) -> Remediation | None:
    raise NotImplementedError("approval lands in ITER_03")


async def reject(db: AsyncSession, remediation_id: str) -> Remediation | None:
    raise NotImplementedError("rejection lands in ITER_03")
