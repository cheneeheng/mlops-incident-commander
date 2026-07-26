"""Remediation execution + approval flow. Owns the transaction boundary and publishes SSE events.

Executors are simulated: rollback performs a real, safe deploy swap back to the known-good version
(the serving poller picks it up); retrain_trigger and pipeline_fix are recorded state transitions
with synthetic immediate completion. Executing a remediation resolves its incident.
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.postmortem import generate_postmortem
from backend.app.db import queries
from backend.app.db.models import Remediation
from backend.app.domain.enums import (
    IncidentStatus,
    RemediationActionType,
    RemediationStatus,
)
from backend.app.domain.errors import ConflictError
from backend.app.observability import log
from backend.app.services.event_service import broker

_GOOD_VERSION = "v1.0-good"
_TERMINAL = {RemediationStatus.EXECUTED, RemediationStatus.AUTO_EXECUTED}


async def execute_remediation(db: AsyncSession, remediation: Remediation, *, auto: bool) -> Remediation:
    """Perform the action, mark the remediation terminal, resolve its incident, commit, and emit."""
    if remediation.action_type == RemediationActionType.ROLLBACK:
        await queries.set_active_deploy(db, _GOOD_VERSION)

    remediation.status = RemediationStatus.AUTO_EXECUTED if auto else RemediationStatus.EXECUTED
    remediation.executed_at = datetime.now(UTC)

    incident = await queries.get_incident(db, remediation.incident_id)
    if incident is not None and incident.closed_at is None:
        incident.status = IncidentStatus.RESOLVED
        incident.closed_at = datetime.now(UTC)

    await db.commit()
    broker.publish(
        "remediation_executed",
        {
            "remediation_id": remediation.id,
            "incident_id": remediation.incident_id,
            "action_type": remediation.action_type,
            "auto": auto,
        },
    )
    # Postmortem on resolution (own sessions/commit). Non-fatal: a postmortem failure must not
    # unwind the executed remediation. Runs inline, so the approve request waits on it.
    try:
        await generate_postmortem(remediation.incident_id)
    except Exception as exc:
        log.error("postmortem_generation_failed", error=repr(exc))
    return remediation


async def approve(db: AsyncSession, remediation_id: str) -> Remediation | None:
    remediation = await queries.get_remediation(db, remediation_id)
    if remediation is None:
        return None
    if remediation.status in _TERMINAL:
        raise ConflictError("remediation already executed")
    if remediation.status == RemediationStatus.REJECTED:
        raise ConflictError("remediation already rejected")
    return await execute_remediation(db, remediation, auto=False)


async def reject(db: AsyncSession, remediation_id: str) -> Remediation | None:
    remediation = await queries.get_remediation(db, remediation_id)
    if remediation is None:
        return None
    if remediation.status in _TERMINAL:
        raise ConflictError("remediation already executed")
    if remediation.status == RemediationStatus.REJECTED:
        return remediation  # idempotent
    remediation.status = RemediationStatus.REJECTED
    await db.commit()
    broker.publish(
        "remediation_rejected",
        {"remediation_id": remediation.id, "incident_id": remediation.incident_id},
    )
    return remediation
