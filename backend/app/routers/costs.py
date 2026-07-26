from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas import AgentRunOut, CostSummary
from backend.app.services import cost_service

router = APIRouter(prefix="/api", tags=["costs"])


@router.get("/agent-runs", response_model=list[AgentRunOut])
async def list_agent_runs(db: AsyncSession = Depends(get_db)):
    return await cost_service.list_agent_runs(db)


@router.get("/costs/summary", response_model=CostSummary)
async def costs_summary(db: AsyncSession = Depends(get_db)):
    return await cost_service.cost_summary(db)
