"""Agent-run listing + cost aggregation. Grouping is done in Python over the agent_run rows — fine
at MVP volume and avoids per-dimension GROUP BY queries."""

from collections import defaultdict
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import queries
from backend.app.db.models import AgentRun
from backend.app.schemas import CostBucket, CostSummary


async def list_agent_runs(db: AsyncSession) -> list[AgentRun]:
    return await queries.list_agent_runs(db)


def _bucket(runs: list[AgentRun], key_of: Callable[[AgentRun], str | None]) -> list[CostBucket]:
    cost: dict[str, float] = defaultdict(float)
    count: dict[str, int] = defaultdict(int)
    for run in runs:
        key = key_of(run)
        if key is None:
            continue
        cost[key] += run.cost_usd
        count[key] += 1
    return [
        CostBucket(key=key, cost_usd=cost[key], run_count=count[key])
        for key in sorted(cost, key=lambda k: cost[k], reverse=True)
    ]


async def cost_summary(db: AsyncSession) -> CostSummary:
    runs = await queries.list_agent_runs(db)
    return CostSummary(
        total_cost_usd=sum(run.cost_usd for run in runs),
        by_agent=_bucket(runs, lambda r: r.agent_name),
        by_incident=_bucket(runs, lambda r: r.incident_id),
        by_day=_bucket(runs, lambda r: r.created_at.date().isoformat()),
    )
