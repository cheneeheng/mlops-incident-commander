"""Eval harness service: start a scored run (spawns the background runner) and read runs/scorecards.
The runner drives the live pipeline; start_run returns immediately with the created eval_run (202)."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import queries
from backend.app.db.models import EvalRun
from backend.app.eval.runner import run_suite
from backend.app.eval.scenarios import SUITE_VERSION
from backend.app.schemas import EvalCaseOut, EvalRunDetail, EvalRunOut

# Hold references so background runner tasks are not garbage-collected mid-flight.
_background_tasks: set[asyncio.Task[None]] = set()


async def list_runs(db: AsyncSession) -> list[EvalRun]:
    return await queries.list_eval_runs(db)


async def get_run(db: AsyncSession, run_id: str) -> EvalRunDetail | None:
    run = await queries.get_eval_run(db, run_id)
    if run is None:
        return None
    cases = await queries.get_eval_cases_for_run(db, run_id)
    return EvalRunDetail(
        **EvalRunOut.model_validate(run).model_dump(),
        cases=[EvalCaseOut.model_validate(case) for case in cases],
    )


async def start_run(db: AsyncSession, demo: bool = False) -> EvalRun:
    run = EvalRun(suite_version=SUITE_VERSION)
    await queries.insert_eval_run(db, run)
    await db.commit()
    task = asyncio.create_task(run_suite(run.id, demo=demo))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return run
