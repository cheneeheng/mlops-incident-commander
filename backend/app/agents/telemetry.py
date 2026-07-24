"""Agent-run telemetry: persist one agent_run per agent invocation (tokens from the accumulated API
usage, cost from the per-model tier table, wall-clock latency). Callers own the transaction."""

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.llm import Usage
from backend.app.config import get_settings
from backend.app.db.models import AgentRun
from backend.app.db.queries import insert_agent_run
from backend.app.domain.enums import AgentRunStatus


async def record_agent_run(
    db: AsyncSession,
    *,
    agent_name: str,
    model: str,
    incident_id: str | None,
    usage: Usage,
    latency_ms: float,
    status: AgentRunStatus,
) -> AgentRun:
    run = AgentRun(
        incident_id=incident_id,
        agent_name=agent_name,
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=get_settings().cost_usd(model, usage.input_tokens, usage.output_tokens),
        latency_ms=latency_ms,
        status=status,
    )
    return await insert_agent_run(db, run)
