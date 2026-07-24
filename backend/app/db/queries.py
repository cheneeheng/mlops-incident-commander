"""Data-access layer: all SQL lives here. No business logic. Functions never commit — the calling
service owns the transaction boundary (one commit per request)."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    AgentRun,
    Deploy,
    Hypothesis,
    Incident,
    Injection,
    MetricWindow,
    Postmortem,
    PredictionLog,
    Remediation,
    ReferenceProfile,
    ServingLog,
)

# ---- deploys ---------------------------------------------------------------
async def list_deploys(db: AsyncSession) -> list[Deploy]:
    rows = await db.scalars(select(Deploy).order_by(Deploy.deployed_at.desc()))
    return list(rows)


async def get_active_deploy(db: AsyncSession) -> Deploy | None:
    return await db.scalar(select(Deploy).where(Deploy.is_active.is_(True)))


async def get_deploy_by_version(db: AsyncSession, model_version: str) -> Deploy | None:
    return await db.scalar(select(Deploy).where(Deploy.model_version == model_version))


async def set_active_deploy(db: AsyncSession, model_version: str) -> Deploy | None:
    """Flip the active flag to the named version (deactivating all others). Returns it, or None."""
    target = await get_deploy_by_version(db, model_version)
    if target is None:
        return None
    await db.execute(update(Deploy).values(is_active=False))
    target.is_active = True
    await db.flush()
    return target


# ---- injections ------------------------------------------------------------
async def list_injections(db: AsyncSession) -> list[Injection]:
    rows = await db.scalars(select(Injection).order_by(Injection.started_at.desc()))
    return list(rows)


async def get_injection(db: AsyncSession, injection_id: str) -> Injection | None:
    return await db.get(Injection, injection_id)


async def get_active_injections(db: AsyncSession) -> list[Injection]:
    rows = await db.scalars(select(Injection).where(Injection.ended_at.is_(None)))
    return list(rows)


async def get_latest_injection(db: AsyncSession) -> Injection | None:
    return await db.scalar(select(Injection).order_by(Injection.started_at.desc()).limit(1))


async def insert_injection(db: AsyncSession, injection: Injection) -> Injection:
    db.add(injection)
    await db.flush()
    return injection


# ---- reference profile -----------------------------------------------------
async def get_reference_profile(db: AsyncSession, model_version: str) -> ReferenceProfile | None:
    return await db.scalar(
        select(ReferenceProfile).where(ReferenceProfile.model_version == model_version)
    )


# ---- prediction / serving logs (written by the serving process) ------------
async def insert_prediction(db: AsyncSession, row: PredictionLog) -> None:
    db.add(row)


async def insert_serving_log(db: AsyncSession, row: ServingLog) -> None:
    db.add(row)


async def get_predictions_between(
    db: AsyncSession, start: datetime, end: datetime
) -> list[PredictionLog]:
    rows = await db.scalars(
        select(PredictionLog).where(PredictionLog.ts >= start, PredictionLog.ts < end)
    )
    return list(rows)


# ---- metric windows --------------------------------------------------------
async def insert_metric_window(db: AsyncSession, row: MetricWindow) -> MetricWindow:
    db.add(row)
    await db.flush()
    return row


async def list_windows(db: AsyncSession, since: datetime | None) -> list[MetricWindow]:
    stmt = select(MetricWindow).order_by(MetricWindow.window_start.asc())
    if since is not None:
        stmt = stmt.where(MetricWindow.window_start >= since)
    rows = await db.scalars(stmt)
    return list(rows)


async def get_window(db: AsyncSession, window_id: str) -> MetricWindow | None:
    return await db.get(MetricWindow, window_id)


async def get_windows_between(
    db: AsyncSession, start: datetime, end: datetime
) -> list[MetricWindow]:
    rows = await db.scalars(
        select(MetricWindow)
        .where(MetricWindow.window_start >= start, MetricWindow.window_start < end)
        .order_by(MetricWindow.window_start.asc())
    )
    return list(rows)


# ---- incidents -------------------------------------------------------------
async def insert_incident(db: AsyncSession, incident: Incident) -> Incident:
    db.add(incident)
    await db.flush()  # populate server-side id + sequence-backed number
    await db.refresh(incident)
    return incident


async def list_incidents(db: AsyncSession) -> list[Incident]:
    rows = await db.scalars(select(Incident).order_by(Incident.opened_at.desc()))
    return list(rows)


async def get_incident(db: AsyncSession, incident_id: str) -> Incident | None:
    return await db.get(Incident, incident_id)


# ---- agent runs ------------------------------------------------------------
async def insert_agent_run(db: AsyncSession, run: AgentRun) -> AgentRun:
    db.add(run)
    await db.flush()
    return run


async def list_agent_runs(db: AsyncSession) -> list[AgentRun]:
    rows = await db.scalars(select(AgentRun).order_by(AgentRun.created_at.desc()))
    return list(rows)


async def get_agent_runs_for_incident(db: AsyncSession, incident_id: str) -> list[AgentRun]:
    rows = await db.scalars(
        select(AgentRun)
        .where(AgentRun.incident_id == incident_id)
        .order_by(AgentRun.created_at.asc())
    )
    return list(rows)


# ---- hypotheses ------------------------------------------------------------
async def insert_hypothesis(db: AsyncSession, hypothesis: Hypothesis) -> Hypothesis:
    db.add(hypothesis)
    await db.flush()
    return hypothesis


async def get_hypotheses_for_incident(db: AsyncSession, incident_id: str) -> list[Hypothesis]:
    rows = await db.scalars(
        select(Hypothesis).where(Hypothesis.incident_id == incident_id)
    )
    return list(rows)


# ---- remediations ----------------------------------------------------------
async def insert_remediation(db: AsyncSession, remediation: Remediation) -> Remediation:
    db.add(remediation)
    await db.flush()
    return remediation


async def get_remediation(db: AsyncSession, remediation_id: str) -> Remediation | None:
    return await db.get(Remediation, remediation_id)


async def get_remediations_for_incident(db: AsyncSession, incident_id: str) -> list[Remediation]:
    rows = await db.scalars(
        select(Remediation)
        .where(Remediation.incident_id == incident_id)
        .order_by(Remediation.created_at.asc())
    )
    return list(rows)


# ---- postmortems -----------------------------------------------------------
async def insert_postmortem(db: AsyncSession, postmortem: Postmortem) -> Postmortem:
    db.add(postmortem)
    await db.flush()
    return postmortem


async def list_postmortems(db: AsyncSession) -> list[Postmortem]:
    rows = await db.scalars(select(Postmortem).order_by(Postmortem.created_at.desc()))
    return list(rows)


async def get_postmortem(db: AsyncSession, postmortem_id: str) -> Postmortem | None:
    return await db.get(Postmortem, postmortem_id)


async def similar_postmortems(
    db: AsyncSession, embedding: list[float], k: int = 3
) -> list[Postmortem]:
    """Top-k postmortems by cosine distance to the given embedding (nearest first)."""
    rows = await db.scalars(
        select(Postmortem)
        .where(Postmortem.embedding.is_not(None))
        .order_by(Postmortem.embedding.cosine_distance(embedding))
        .limit(k)
    )
    return list(rows)


# ---- serving log search (MCP logs tool) ------------------------------------
async def search_serving_logs(db: AsyncSession, query: str, limit: int = 50) -> list[ServingLog]:
    rows = await db.scalars(
        select(ServingLog)
        .where(ServingLog.message.ilike(f"%{query}%"))
        .order_by(ServingLog.ts.desc())
        .limit(limit)
    )
    return list(rows)
