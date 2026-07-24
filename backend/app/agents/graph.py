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
from backend.app.agents.mcp_client import McpToolbox
from backend.app.agents.prompts import DIAGNOSIS_SYSTEM, MONITOR_SYSTEM
from backend.app.agents.telemetry import record_agent_run
from backend.app.config import get_settings
from backend.app.db.models import Hypothesis, Incident, MetricWindow, ReferenceProfile
from backend.app.db.queries import (
    get_reference_profile,
    get_window,
    insert_hypothesis,
    insert_incident,
)
from backend.app.db.session import SessionLocal
from backend.app.domain.enums import (
    AgentRunStatus,
    FaultType,
    HypothesisKind,
    IncidentStatus,
    Severity,
)
from backend.app.observability import log

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
    toolbox: McpToolbox, summary: dict[str, Any]
) -> tuple[DiagnosisOutput, Usage]:
    usage = Usage()
    client = get_client()
    model = get_settings().model_strong
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                "An incident was opened on this trigger window. Investigate the fault using the "
                "tools (tool time ranges are ISO-8601 timestamps), then return the final JSON "
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


# ---- graph nodes -------------------------------------------------------------------------------
class GraphState(TypedDict, total=False):
    window_id: str
    incident_id: str | None
    open_incident: bool
    summary: dict[str, Any]


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
        return {
            "open_incident": decision.open_incident,
            "incident_id": incident_id,
            "summary": summary,
        }


async def _diagnosis_node(state: GraphState) -> GraphState:
    incident_id = state.get("incident_id")
    summary = state.get("summary", {})
    if incident_id is None:
        return {}

    started = time.perf_counter()
    try:
        async with McpToolbox() as toolbox:
            diagnosis, usage = await _run_diagnosis(toolbox, summary)
        status = AgentRunStatus.SUCCESS
    except (APIError, OSError) as exc:
        log.error("diagnosis_failed", error=repr(exc))
        diagnosis, usage, status = _fail_closed(f"diagnosis error: {exc}"), Usage(), AgentRunStatus.FAILED
    latency_ms = (time.perf_counter() - started) * 1000.0

    async with SessionLocal() as db:
        run = await record_agent_run(
            db,
            agent_name="diagnosis",
            model=get_settings().model_strong,
            incident_id=incident_id,
            usage=usage,
            latency_ms=latency_ms,
            status=status,
        )
        await insert_hypothesis(
            db,
            Hypothesis(
                incident_id=incident_id,
                agent_run_id=run.id,
                fault_type=diagnosis.fault_type,
                confidence=diagnosis.confidence,
                evidence=[e.model_dump() for e in diagnosis.evidence],
                kind=HypothesisKind.PRIMARY,
            ),
        )
        await _mark_diagnosing(db, incident_id)
        await db.commit()
    log.info(
        "hypothesis_written",
        incident_id=incident_id,
        fault_type=diagnosis.fault_type,
        confidence=diagnosis.confidence,
    )
    return {}


async def _mark_diagnosing(db: AsyncSession, incident_id: str) -> None:
    incident = await db.get(Incident, incident_id)
    if incident is not None and incident.status == IncidentStatus.OPEN:
        incident.status = IncidentStatus.DIAGNOSING


def _route_after_monitor(state: GraphState) -> str:
    return "diagnosis" if state.get("open_incident") else "end"


def _build_graph() -> Any:
    graph = StateGraph(GraphState)
    graph.add_node("monitor", _monitor_node)
    graph.add_node("diagnosis", _diagnosis_node)
    graph.set_entry_point("monitor")
    graph.add_conditional_edges("monitor", _route_after_monitor, {"diagnosis": "diagnosis", "end": END})
    graph.add_edge("diagnosis", END)
    return graph.compile()


_APP = _build_graph()


async def process_window(window_id: str) -> None:
    """Entry point: the aggregator posts each new metric window here for the monitor to triage."""
    await _APP.ainvoke({"window_id": window_id})
