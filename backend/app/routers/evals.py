from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas import EvalRunDetail, EvalRunOut
from backend.app.services import eval_service

router = APIRouter(prefix="/api", tags=["evals"])


@router.post("/eval/runs", response_model=EvalRunOut, status_code=202)
async def start_run(demo: bool = False, db: AsyncSession = Depends(get_db)):
    return await eval_service.start_run(db, demo=demo)


@router.get("/eval/runs", response_model=list[EvalRunOut])
async def list_runs(db: AsyncSession = Depends(get_db)):
    return await eval_service.list_runs(db)


@router.get("/eval/runs/{run_id}", response_model=EvalRunDetail)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await eval_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="eval run not found")
    return run
