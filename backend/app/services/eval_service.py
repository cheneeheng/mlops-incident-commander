"""Eval harness. Stub at SKELETON; real runner + scoring in ITER_05."""

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import EvalRun


async def list_runs(db: AsyncSession) -> list[EvalRun]:
    return []  # stub — real query in ITER_05


async def get_run(db: AsyncSession, run_id: str) -> EvalRun | None:
    return None  # stub — real query in ITER_05


async def start_run(db: AsyncSession) -> EvalRun:
    raise NotImplementedError("eval runner lands in ITER_05")
