"""Incident reads. list returns ORM rows (serialized as IncidentSummary); get assembles the full
IncidentDetail from the incident plus its hypotheses, remediations, and agent runs."""

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import queries
from backend.app.db.models import Incident
from backend.app.schemas import (
    AgentRunOut,
    HypothesisOut,
    IncidentDetail,
    IncidentSummary,
    RemediationOut,
)


async def list_incidents(db: AsyncSession) -> list[Incident]:
    return await queries.list_incidents(db)


async def get_incident(db: AsyncSession, incident_id: str) -> IncidentDetail | None:
    incident = await queries.get_incident(db, incident_id)
    if incident is None:
        return None
    hypotheses = await queries.get_hypotheses_for_incident(db, incident_id)
    remediations = await queries.get_remediations_for_incident(db, incident_id)
    agent_runs = await queries.get_agent_runs_for_incident(db, incident_id)
    return IncidentDetail(
        **IncidentSummary.model_validate(incident).model_dump(),
        hypotheses=[HypothesisOut.model_validate(h) for h in hypotheses],
        remediations=[RemediationOut.model_validate(r) for r in remediations],
        agent_runs=[AgentRunOut.model_validate(a) for a in agent_runs],
    )
