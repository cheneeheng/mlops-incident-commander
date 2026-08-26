"""Postmortem agent: on incident resolution, write a structured markdown postmortem, embed it, and
store it for future memory retrieval. Called by the remediation executor after an incident resolves.
Failures here are non-fatal to the remediation that triggered it."""

import json
import re
import time
from typing import Any

from anthropic import APIError

from backend.app.agents.embeddings import embed
from backend.app.agents.llm import Usage, final_text, get_client
from backend.app.agents.prompts import POSTMORTEM_SYSTEM
from backend.app.agents.telemetry import record_agent_run
from backend.app.config import get_settings
from backend.app.db.models import Hypothesis, Incident, Injection, Postmortem, Remediation
from backend.app.db.queries import (
    get_hypotheses_for_incident,
    get_incident,
    get_injection_at,
    get_remediations_for_incident,
    insert_postmortem,
)
from backend.app.db.session import SessionLocal
from backend.app.domain.enums import AgentRunStatus
from backend.app.observability import log
from backend.app.services.event_service import broker

_POSTMORTEM_MAX_TOKENS = 1500


_GROUND_TRUTH_HEADING = re.compile(r"^#+[ \t]*ground truth.*$", re.IGNORECASE | re.MULTILINE)


def strip_ground_truth(body_md: str) -> str:
    """Drop the ground-truth section so a postmortem can be shown to a diagnosing agent.

    POSTMORTEM_SYSTEM fixes it as the last of five sections and forbids ground truth in the other
    four, so cutting from its heading to the end removes the answer key and nothing else. Both
    halves of that are prompt-enforced, hence best-effort: keep the two rules in sync.
    """
    match = _GROUND_TRUTH_HEADING.search(body_md)
    return body_md[: match.start()].rstrip() if match else body_md


def _build_context(
    incident: Incident,
    hypotheses: list[Hypothesis],
    remediations: list[Remediation],
    injection: Injection | None,
) -> dict[str, Any]:
    return {
        "incident": {
            "number": incident.number,
            "severity": incident.severity,
            "status": incident.status,
            "opened_at": incident.opened_at.isoformat(),
            "closed_at": incident.closed_at.isoformat() if incident.closed_at else None,
            "trigger_metrics": incident.trigger_metrics,
        },
        "hypotheses": [
            {
                "kind": h.kind,
                "fault_type": h.fault_type,
                "confidence": h.confidence,
                "evidence": h.evidence,
            }
            for h in hypotheses
        ],
        "remediations": [
            {"action_type": r.action_type, "risk": r.risk, "status": r.status} for r in remediations
        ],
        "injection_ground_truth": (
            {"fault_type": injection.ground_truth_fault, "ended": injection.ended_at is not None}
            if injection is not None
            else None
        ),
    }


def _fallback_markdown(context: dict[str, Any]) -> str:
    incident = context["incident"]
    return (
        f"## Timeline\nIncident #{incident['number']} ({incident['severity']}) opened "
        f"{incident['opened_at']}, resolved {incident['closed_at']}.\n\n"
        "## Root cause\nPostmortem model unavailable; see hypotheses below.\n\n"
        f"## Evidence\n```json\n{json.dumps(context['hypotheses'], indent=2)}\n```\n\n"
        f"## Action taken\n```json\n{json.dumps(context['remediations'], indent=2)}\n```\n\n"
        f"## Ground truth vs diagnosis\n{json.dumps(context['injection_ground_truth'])}\n"
    )


async def _run_postmortem(context: dict[str, Any]) -> tuple[str, Usage, float]:
    usage = Usage()
    started = time.perf_counter()
    response = await get_client().messages.create(
        model=get_settings().model_strong,
        max_tokens=_POSTMORTEM_MAX_TOKENS,
        system=POSTMORTEM_SYSTEM,
        messages=[{"role": "user", "content": json.dumps(context)}],
    )
    usage.add(response.usage)
    return final_text(response), usage, (time.perf_counter() - started) * 1000.0


async def generate_postmortem(incident_id: str) -> None:
    async with SessionLocal() as db:
        incident = await get_incident(db, incident_id)
        if incident is None:
            return
        hypotheses = await get_hypotheses_for_incident(db, incident_id)
        remediations = await get_remediations_for_incident(db, incident_id)
        # The injection that was running when this incident opened, not merely the newest one:
        # a later injection is not this incident's cause, and an organic incident has none.
        injection = await get_injection_at(db, incident.opened_at)

    context = _build_context(incident, hypotheses, remediations, injection)
    try:
        body_md, usage, latency_ms = await _run_postmortem(context)
        status = AgentRunStatus.SUCCESS
    except (APIError, ValueError, TypeError) as exc:
        log.error("postmortem_llm_failed", error=repr(exc))
        body_md, usage, status, latency_ms = _fallback_markdown(context), Usage(), AgentRunStatus.FAILED, 0.0

    embedding: list[float] | None
    try:
        embedding = await embed(body_md)
    except Exception as exc:  # embedding is best-effort; a null vector just skips memory retrieval
        log.error("postmortem_embed_failed", error=repr(exc))
        embedding = None

    async with SessionLocal() as db:
        await record_agent_run(
            db,
            agent_name="postmortem",
            model=get_settings().model_strong,
            incident_id=incident_id,
            usage=usage,
            latency_ms=latency_ms,
            status=status,
        )
        postmortem = await insert_postmortem(
            db, Postmortem(incident_id=incident_id, body_md=body_md, embedding=embedding)
        )
        postmortem_id = postmortem.id
        await db.commit()

    broker.publish("postmortem_ready", {"postmortem_id": postmortem_id, "incident_id": incident_id})
    log.info("postmortem_written", incident_id=incident_id, postmortem_id=postmortem_id)
