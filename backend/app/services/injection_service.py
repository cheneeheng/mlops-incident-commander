"""Injection harness CRUD. Stub at SKELETON; real logic (validation, bad_deploy activation) in ITER_01."""

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Injection
from backend.app.schemas import InjectionCreate


async def list_injections(db: AsyncSession) -> list[Injection]:
    return []  # stub — real query in ITER_01


async def create_injection(db: AsyncSession, payload: InjectionCreate) -> Injection:
    raise NotImplementedError("injection creation lands in ITER_01")


async def stop_injection(db: AsyncSession, injection_id: str) -> Injection | None:
    raise NotImplementedError("injection stop lands in ITER_01")
