"""Agent-run listing + cost aggregation. Stub at SKELETON; real in ITER_02."""

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AgentRun
from backend.app.schemas import CostSummary


async def list_agent_runs(db: AsyncSession) -> list[AgentRun]:
    return []  # stub — real query in ITER_02


async def cost_summary(db: AsyncSession) -> CostSummary:
    return CostSummary(total_cost_usd=0.0, by_agent=[], by_incident=[], by_day=[])
