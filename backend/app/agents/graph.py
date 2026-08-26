"""LangGraph agent graph. ITER_02 wires the monitor (Haiku) and diagnosis (Sonnet) nodes; ITER_03
adds remediation and ITER_04 the second-opinion/adjudicator/postmortem nodes.

Flow: the aggregator posts each new metric window to process_window. The monitor triages the window
against the clean baseline; if it opens an incident, the diagnosis node investigates via the MCP
tool servers and writes a schema-valid primary hypothesis. Every model call's tokens/cost/latency
are recorded as an agent_run.
"""

import json
import time
from typing import Any, TypedDict

from anthropic import APIError
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.llm import (
    Usage,
    extract_json,
    final_text,
    get_client,
    truncate_tool_result,
)
from backend.app.agents.embeddings import embed
from backend.app.agents.mcp_client import McpToolbox
from backend.app.agents.postmortem import strip_ground_truth
from backend.app.agents.prompts import (
    ADJUDICATOR_SYSTEM,
    DIAGNOSIS_SYSTEM,
    MONITOR_SYSTEM,
    REMEDIATION_SYSTEM,
)
from backend.app.agents.telemetry import record_agent_run
from backend.app.config import get_settings
from backend.app.db.models import Hypothesis, Incident, MetricWindow, ReferenceProfile, Remediation
from backend.app.db.queries import (
    get_hypotheses_for_incident,
    get_reference_profile,
    get_window,
    insert_hypothesis,
    insert_incident,
    insert_remediation,
    similar_postmortems,
)
from backend.app.db.session import SessionLocal
from backend.app.domain.enums import (
    AgentRunStatus,
    FaultType,
    HypothesisKind,
    IncidentStatus,
    RemediationActionType,
    RemediationRisk,
    RemediationStatus,
    Severity,
)
from backend.app.domain.policy import decide_policy, policy_table_text, should_auto_execute
from backend.app.observability import log
from backend.app.services.event_service import broker
from backend.app.services.remediation_service import execute_remediation

_TOOL_CALL_CAP = 12
_MONITOR_MAX_TOKENS = 512
_DIAGNOSIS_MAX_TOKENS = 1024


# ---- validated LLM output (extra='forbid'; validated before any state mutation) ----------------
class MonitorDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    open_incident: bool
    severity: Severity
    reason: str


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: str
    finding: str


class DiagnosisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fault_type: FaultType
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    reasoning: str


class RemediationProposal(BaseModel):
    # The policy table is authoritative for action/risk; only the rationale is kept from the LLM.
    model_config = ConfigDict(extra="forbid")
    action_type: RemediationActionType
    risk: RemediationRisk
    rationale: str


class AdjudicatorOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fault_type: FaultType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


def _window_summary(window: MetricWindow) -> dict[str, Any]:
    return {
        "window_start": window.window_start.isoformat(),
        "window_end": window.window_end.isoformat(),
        "request_count": window.request_count,
        "latency_p50": window.latency_p50,
        "latency_p95": window.latency_p95,
        "latency_p99": window.latency_p99,
        "mean_confidence": window.mean_confidence,
        "prediction_entropy": window.prediction_entropy,
        "psi_score": window.psi_score,
        "class_distribution": window.class_distribution,
    }


def _baseline(reference: ReferenceProfile | None) -> dict[str, Any]:
    if reference is None:
        return {}
    return {
        "class_distribution": reference.class_distribution,
        "mean_confidence": reference.mean_confidence,
    }


# ---- monitor -----------------------------------------------------------------------------------
async def _run_monitor(
    summary: dict[str, Any], baseline: dict[str, Any]
) -> tuple[MonitorDecision, Usage, float]:
    usage = Usage()
    started = time.perf_counter()
    response = await get_client().messages.create(
        model=get_settings().model_cheap,
        max_tokens=_MONITOR_MAX_TOKENS,
        system=MONITOR_SYSTEM,
        messages=[{"role": "user", "content": json.dumps({"window": summary, "baseline": baseline})}],
    )
    usage.add(response.usage)
    decision = MonitorDecision.model_validate(extract_json(final_text(response)))
    return decision, usage, (time.perf_counter() - started) * 1000.0


# ---- diagnosis ---------------------------------------------------------------------------------
def _fail_closed(reason: str) -> DiagnosisOutput:
    return DiagnosisOutput(
        fault_type=FaultType.UNKNOWN, confidence=0.1, evidence=[], reasoning=reason
    )


async def _run_diagnosis(
    toolbox: McpToolbox, summary: dict[str, Any], memory: str
) -> tuple[DiagnosisOutput, Usage]:
    usage = Usage()
    client = get_client()
    model = get_settings().model_strong
    prefix = f"{memory}\n\n" if memory else ""
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                f"{prefix}An incident was opened on this trigger window. Investigate the fault using "
                "the tools (tool time ranges are ISO-8601 timestamps), then return the final JSON "
                f"hypothesis.\n\nTrigger window:\n{json.dumps(summary)}"
            ),
        }
    ]
    tool_calls = 0
    while True:
        response = await client.messages.create(
            model=model,
            max_tokens=_DIAGNOSIS_MAX_TOKENS,
            system=DIAGNOSIS_SYSTEM,
            messages=messages,
            tools=toolbox.tool_specs,
        )
        usage.add(response.usage)
        if response.stop_reason != "tool_use":
            try:
                return DiagnosisOutput.model_validate(extract_json(final_text(response))), usage
            except (ValueError, TypeError) as exc:
                return _fail_closed(f"unparseable diagnosis output: {exc}"), usage

        # gotcha (LLM role constraint): assistant tool_use echoed back, results as user tool_result
        # blocks; system stays out of the messages array.
        messages.append({"role": "assistant", "content": response.content})
        results: list[dict[str, Any]] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool_calls += 1
            output = await toolbox.call_tool(block.name, dict(block.input))
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": truncate_tool_result(output),
                }
            )
        messages.append({"role": "user", "content": results})
        if tool_calls >= _TOOL_CALL_CAP:
            return _fail_closed("tool-call cap reached before a conclusion"), usage


# ---- adjudication ------------------------------------------------------------------------------
async def _run_adjudicator(
    primary: Hypothesis, second: Hypothesis
) -> tuple[AdjudicatorOutput, Usage, float]:
    usage = Usage()
    started = time.perf_counter()
    payload = {
        "primary": {
            "fault_type": primary.fault_type,
            "confidence": primary.confidence,
            "evidence": primary.evidence,
        },
        "second_opinion": {
            "fault_type": second.fault_type,
            "confidence": second.confidence,
            "evidence": second.evidence,
        },
    }
    response = await get_client().messages.create(
        model=get_settings().model_strong,
        max_tokens=_MONITOR_MAX_TOKENS,
        system=ADJUDICATOR_SYSTEM,
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )
    usage.add(response.usage)
    output = AdjudicatorOutput.model_validate(extract_json(final_text(response)))
    return output, usage, (time.perf_counter() - started) * 1000.0


# ---- remediation -------------------------------------------------------------------------------
async def _run_remediation(
    fault_type: FaultType, confidence: float
) -> tuple[RemediationProposal, Usage, float]:
    usage = Usage()
    started = time.perf_counter()
    payload = {
        "hypothesis": {"fault_type": fault_type, "confidence": confidence},
        "policy_table": policy_table_text(),
    }
    response = await get_client().messages.create(
        model=get_settings().model_strong,
        max_tokens=_MONITOR_MAX_TOKENS,
        system=REMEDIATION_SYSTEM,
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )
    usage.add(response.usage)
    proposal = RemediationProposal.model_validate(extract_json(final_text(response)))
    return proposal, usage, (time.perf_counter() - started) * 1000.0


# ---- graph nodes -------------------------------------------------------------------------------
class GraphState(TypedDict, total=False):
    window_id: str
    incident_id: str | None
    open_incident: bool
    summary: dict[str, Any]
    # Accepted diagnosis driving remediation (primary, or the adjudicated result).
    fault_type: FaultType
    confidence: float
    hypothesis_id: str
    # Carried for the adjudicator when a second opinion is triggered.
    primary_fault: FaultType
    primary_confidence: float
    second_fault: FaultType
    second_confidence: float


async def _monitor_node(state: GraphState) -> GraphState:
    async with SessionLocal() as db:
        window = await get_window(db, state["window_id"])
        if window is None:
            log.warning("monitor_window_missing", window_id=state["window_id"])
            return {"open_incident": False, "incident_id": None}
        summary = _window_summary(window)
        reference = await get_reference_profile(db, "v1.0-good")

        try:
            decision, usage, latency_ms = await _run_monitor(summary, _baseline(reference))
        except (APIError, ValueError, TypeError) as exc:
            log.error("monitor_failed", error=repr(exc))
            return {"open_incident": False, "incident_id": None}

        incident_id: str | None = None
        if decision.open_incident:
            incident = await insert_incident(
                db,
                Incident(
                    status=IncidentStatus.OPEN,
                    severity=decision.severity,
                    trigger_metrics=summary,
                ),
            )
            incident_id = incident.id
            log.info(
                "incident_opened",
                incident_id=incident_id,
                number=incident.number,
                severity=decision.severity,
                reason=decision.reason,
            )

        await record_agent_run(
            db,
            agent_name="monitor",
            model=get_settings().model_cheap,
            incident_id=incident_id,
            usage=usage,
            latency_ms=latency_ms,
            status=AgentRunStatus.SUCCESS,
        )
        await db.commit()

    if incident_id is not None:
        broker.publish(
            "incident_opened",
            {"incident_id": incident_id, "severity": decision.severity, "reason": decision.reason},
        )
    return {
        "open_incident": decision.open_incident,
        "incident_id": incident_id,
        "summary": summary,
    }


async def _retrieve_memory(summary: dict[str, Any]) -> str:
    """Top-3 similar past postmortems as advisory context for diagnosis (empty on none/failure)."""
    try:
        vector = await embed(json.dumps(summary))
        async with SessionLocal() as db:
            posts = await similar_postmortems(db, vector, k=3)
    except Exception as exc:  # retrieval is best-effort; never block diagnosis on it
        log.error("memory_retrieval_failed", error=repr(exc))
        return ""
    if not posts:
        return ""
    # Ground truth is stripped before any postmortem reaches a diagnosing agent: recalling a
    # past incident's answer key would let diagnosis read the label instead of inferring it.
    blocks = [  # ~500 tokens each
        f"[past postmortem {p.id}]\n{strip_ground_truth(p.body_md)[:2000]}" for p in posts
    ]
    return "Advisory context — similar past incidents (advisory only, not ground truth):\n" + (
        "\n\n".join(blocks)
    )


async def _diagnose_once(
    incident_id: str, summary: dict[str, Any], memory: str, kind: HypothesisKind, agent_name: str
) -> tuple[FaultType, float, str]:
    """One independent diagnosis run: investigate via MCP, persist a hypothesis of `kind`, emit."""
    started = time.perf_counter()
    try:
        async with McpToolbox() as toolbox:
            diagnosis, usage = await _run_diagnosis(toolbox, summary, memory)
        status = AgentRunStatus.SUCCESS
    except (APIError, OSError) as exc:
        log.error("diagnosis_failed", agent=agent_name, error=repr(exc))
        diagnosis, usage, status = _fail_closed(f"diagnosis error: {exc}"), Usage(), AgentRunStatus.FAILED
    latency_ms = (time.perf_counter() - started) * 1000.0

    async with SessionLocal() as db:
        run = await record_agent_run(
            db,
            agent_name=agent_name,
            model=get_settings().model_strong,
            incident_id=incident_id,
            usage=usage,
            latency_ms=latency_ms,
            status=status,
        )
        hypothesis = await insert_hypothesis(
            db,
            Hypothesis(
                incident_id=incident_id,
                agent_run_id=run.id,
                fault_type=diagnosis.fault_type,
                confidence=diagnosis.confidence,
                evidence=[e.model_dump() for e in diagnosis.evidence],
                kind=kind,
            ),
        )
        hypothesis_id = hypothesis.id
        await _mark_diagnosing(db, incident_id)
        await db.commit()

    broker.publish(
        "hypothesis_ready",
        {
            "incident_id": incident_id,
            "hypothesis_id": hypothesis_id,
            "kind": kind,
            "fault_type": diagnosis.fault_type,
            "confidence": diagnosis.confidence,
        },
    )
    log.info(
        "hypothesis_written",
        incident_id=incident_id,
        kind=kind,
        fault_type=diagnosis.fault_type,
        confidence=diagnosis.confidence,
    )
    return diagnosis.fault_type, diagnosis.confidence, hypothesis_id


async def _diagnosis_node(state: GraphState) -> GraphState:
    incident_id = state.get("incident_id")
    summary = state.get("summary", {})
    if incident_id is None:
        return {}
    memory = await _retrieve_memory(summary)
    fault_type, confidence, hypothesis_id = await _diagnose_once(
        incident_id, summary, memory, HypothesisKind.PRIMARY, "diagnosis"
    )
    return {
        "fault_type": fault_type,
        "confidence": confidence,
        "hypothesis_id": hypothesis_id,
        "primary_fault": fault_type,
        "primary_confidence": confidence,
    }


async def _second_opinion_node(state: GraphState) -> GraphState:
    incident_id = state.get("incident_id")
    summary = state.get("summary", {})
    if incident_id is None:
        return {}
    memory = await _retrieve_memory(summary)
    fault_type, confidence, _ = await _diagnose_once(
        incident_id, summary, memory, HypothesisKind.SECOND_OPINION, "second_opinion"
    )
    return {"second_fault": fault_type, "second_confidence": confidence}


async def _adjudicator_node(state: GraphState) -> GraphState:
    incident_id = state.get("incident_id")
    if incident_id is None:
        return {}
    async with SessionLocal() as db:
        hypotheses = await get_hypotheses_for_incident(db, incident_id)
    primary = next((h for h in hypotheses if h.kind == HypothesisKind.PRIMARY), None)
    second = next((h for h in hypotheses if h.kind == HypothesisKind.SECOND_OPINION), None)
    if primary is None or second is None:
        return {}

    if primary.fault_type == second.fault_type:
        # Agreement short-circuits the adjudicator LLM: accept the higher-confidence read.
        accepted_fault = FaultType(primary.fault_type)
        accepted_confidence = max(primary.confidence, second.confidence)
        reasoning = "both independent diagnoses agree"
        usage, run_status, latency_ms = Usage(), AgentRunStatus.SUCCESS, 0.0
    else:
        started = time.perf_counter()
        try:
            output, usage, latency_ms = await _run_adjudicator(primary, second)
            accepted_fault, accepted_confidence, reasoning = (
                output.fault_type,
                output.confidence,
                output.reasoning,
            )
            run_status = AgentRunStatus.SUCCESS
        except (APIError, ValueError, TypeError) as exc:
            log.error("adjudicator_failed", error=repr(exc))
            better = primary if primary.confidence >= second.confidence else second
            accepted_fault = FaultType(better.fault_type)
            accepted_confidence = better.confidence
            reasoning = "adjudicator unavailable; took the higher-confidence diagnosis"
            usage, run_status = Usage(), AgentRunStatus.FAILED
            latency_ms = (time.perf_counter() - started) * 1000.0

    async with SessionLocal() as db:
        run = await record_agent_run(
            db,
            agent_name="adjudicator",
            model=get_settings().model_strong,
            incident_id=incident_id,
            usage=usage,
            latency_ms=latency_ms,
            status=run_status,
        )
        hypothesis = await insert_hypothesis(
            db,
            Hypothesis(
                incident_id=incident_id,
                agent_run_id=run.id,
                fault_type=accepted_fault,
                confidence=accepted_confidence,
                evidence=[{"reasoning": reasoning}],
                kind=HypothesisKind.ADJUDICATION,
            ),
        )
        hypothesis_id = hypothesis.id
        await db.commit()

    broker.publish(
        "hypothesis_ready",
        {
            "incident_id": incident_id,
            "hypothesis_id": hypothesis_id,
            "kind": HypothesisKind.ADJUDICATION,
            "fault_type": accepted_fault,
            "confidence": accepted_confidence,
        },
    )
    log.info(
        "adjudication_written",
        incident_id=incident_id,
        fault_type=accepted_fault,
        confidence=accepted_confidence,
    )
    return {
        "fault_type": accepted_fault,
        "confidence": accepted_confidence,
        "hypothesis_id": hypothesis_id,
    }


async def _mark_diagnosing(db: AsyncSession, incident_id: str) -> None:
    incident = await db.get(Incident, incident_id)
    if incident is not None and incident.status == IncidentStatus.OPEN:
        incident.status = IncidentStatus.DIAGNOSING


async def _remediation_node(state: GraphState) -> GraphState:
    incident_id = state.get("incident_id")
    hypothesis_id = state.get("hypothesis_id")
    if incident_id is None or hypothesis_id is None:
        return {}
    fault_type = state.get("fault_type", FaultType.UNKNOWN)
    confidence = state.get("confidence", 0.0)

    # Policy is authoritative for action + risk; the LLM only supplies a rationale (logged).
    action, risk = decide_policy(fault_type, confidence)
    started = time.perf_counter()
    try:
        proposal, usage, _ = await _run_remediation(fault_type, confidence)
        rationale = proposal.rationale
        run_status = AgentRunStatus.SUCCESS
    except (APIError, ValueError, TypeError) as exc:
        log.error("remediation_llm_failed", error=repr(exc))
        rationale, usage, run_status = "policy fallback (LLM unavailable)", Usage(), AgentRunStatus.FAILED
    latency_ms = (time.perf_counter() - started) * 1000.0

    auto = should_auto_execute(risk, confidence)
    async with SessionLocal() as db:
        await record_agent_run(
            db,
            agent_name="remediation",
            model=get_settings().model_strong,
            incident_id=incident_id,
            usage=usage,
            latency_ms=latency_ms,
            status=run_status,
        )
        remediation = await insert_remediation(
            db,
            Remediation(
                incident_id=incident_id,
                hypothesis_id=hypothesis_id,
                action_type=action,
                risk=risk,
                status=RemediationStatus.PENDING,
            ),
        )
        if auto:
            await execute_remediation(db, remediation, auto=True)  # commits + emits executed
        else:
            incident = await db.get(Incident, incident_id)
            if incident is not None and incident.status != IncidentStatus.RESOLVED:
                incident.status = IncidentStatus.AWAITING_APPROVAL
            await db.commit()
            broker.publish(
                "remediation_queued",
                {
                    "remediation_id": remediation.id,
                    "incident_id": incident_id,
                    "action_type": action,
                    "risk": risk,
                },
            )
    log.info(
        "remediation_created",
        incident_id=incident_id,
        action_type=action,
        risk=risk,
        auto=auto,
        rationale=rationale,
    )
    return {}


def _route_after_monitor(state: GraphState) -> str:
    return "diagnosis" if state.get("open_incident") else "end"


def _route_after_diagnosis(state: GraphState) -> str:
    # Low-confidence primary triggers an independent second opinion + adjudication.
    return "second_opinion" if state.get("confidence", 1.0) < 0.6 else "remediation"


# Returns Any: langgraph's compiled graph type has no usable stub (module is ignore-missing-imports).
def _build_graph() -> Any:
    graph = StateGraph(GraphState)
    graph.add_node("monitor", _monitor_node)
    graph.add_node("diagnosis", _diagnosis_node)
    graph.add_node("second_opinion", _second_opinion_node)
    graph.add_node("adjudicator", _adjudicator_node)
    graph.add_node("remediation", _remediation_node)
    graph.set_entry_point("monitor")
    graph.add_conditional_edges("monitor", _route_after_monitor, {"diagnosis": "diagnosis", "end": END})
    graph.add_conditional_edges(
        "diagnosis",
        _route_after_diagnosis,
        {"second_opinion": "second_opinion", "remediation": "remediation"},
    )
    graph.add_edge("second_opinion", "adjudicator")
    graph.add_edge("adjudicator", "remediation")
    graph.add_edge("remediation", END)
    return graph.compile()


_APP = _build_graph()


async def process_window(window_id: str) -> None:
    """Entry point: the aggregator posts each new metric window here for the monitor to triage."""
    await _APP.ainvoke({"window_id": window_id})
