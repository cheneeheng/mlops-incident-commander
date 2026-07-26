"""Pydantic v2 request/response models. Input models forbid extra fields (trust boundary)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.domain.enums import (
    INJECTABLE_FAULTS,
    FaultType,
    HypothesisKind,
    RemediationActionType,
    RemediationRisk,
    RemediationStatus,
    Severity,
)

_ORM = ConfigDict(from_attributes=True)


# ---- metrics ---------------------------------------------------------------
class MetricWindowOut(BaseModel):
    model_config = _ORM
    id: str
    window_start: datetime
    window_end: datetime
    request_count: int
    latency_p50: float
    latency_p95: float
    latency_p99: float
    mean_confidence: float
    prediction_entropy: float
    psi_score: float
    class_distribution: dict[str, float]


# ---- injections ------------------------------------------------------------
class InjectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fault_type: FaultType
    params: dict[str, float] = Field(default_factory=dict)

    @field_validator("fault_type")
    @classmethod
    def _must_be_injectable(cls, value: FaultType) -> FaultType:
        # UNKNOWN is a diagnosis-taxonomy value, never an injectable fault. Reject at the boundary.
        if value not in INJECTABLE_FAULTS:
            raise ValueError(f"fault_type {value!r} is not injectable")
        return value


class InjectionOut(BaseModel):
    model_config = _ORM
    id: str
    fault_type: str
    params: dict
    started_at: datetime
    ended_at: datetime | None
    ground_truth_fault: str


# ---- deploys ---------------------------------------------------------------
class DeployActivate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_version: str


class DeployOut(BaseModel):
    model_config = _ORM
    id: str
    model_version: str
    artifact_path: str
    deployed_at: datetime
    is_active: bool
    is_faulty: bool


# ---- agent runs / cost -----------------------------------------------------
class AgentRunOut(BaseModel):
    model_config = _ORM
    id: str
    incident_id: str | None
    agent_name: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    status: str
    created_at: datetime


class CostBucket(BaseModel):
    key: str
    cost_usd: float
    run_count: int


class CostSummary(BaseModel):
    total_cost_usd: float
    by_agent: list[CostBucket]
    by_incident: list[CostBucket]
    by_day: list[CostBucket]


# ---- hypotheses / incidents ------------------------------------------------
class HypothesisOut(BaseModel):
    model_config = _ORM
    id: str
    incident_id: str
    agent_run_id: str
    fault_type: FaultType
    confidence: float
    evidence: list
    kind: HypothesisKind


class RemediationOut(BaseModel):
    model_config = _ORM
    id: str
    incident_id: str
    hypothesis_id: str
    action_type: RemediationActionType
    risk: RemediationRisk
    status: RemediationStatus
    created_at: datetime
    executed_at: datetime | None


class IncidentSummary(BaseModel):
    model_config = _ORM
    id: str
    number: int
    opened_at: datetime
    closed_at: datetime | None
    status: str
    severity: Severity
    trigger_metrics: dict


class IncidentDetail(IncidentSummary):
    hypotheses: list[HypothesisOut] = Field(default_factory=list)
    remediations: list[RemediationOut] = Field(default_factory=list)
    agent_runs: list[AgentRunOut] = Field(default_factory=list)


# ---- postmortems -----------------------------------------------------------
class PostmortemOut(BaseModel):
    model_config = _ORM
    id: str
    incident_id: str
    body_md: str
    created_at: datetime


class SimilarPostmortem(BaseModel):
    id: str
    incident_id: str
    similarity: float
    body_md: str


# ---- evals -----------------------------------------------------------------
class EvalCaseOut(BaseModel):
    model_config = _ORM
    id: str
    eval_run_id: str
    scenario_name: str
    injected_fault: str
    detected: bool | None
    diagnosis_correct: bool | None
    ttd_seconds: float | None
    cost_usd: float | None


class EvalRunOut(BaseModel):
    model_config = _ORM
    id: str
    started_at: datetime
    finished_at: datetime | None
    suite_version: str
    detection_recall: float | None
    diagnosis_accuracy: float | None
    mean_ttd_s: float | None
    mean_cost_usd: float | None


class EvalRunDetail(EvalRunOut):
    cases: list[EvalCaseOut] = Field(default_factory=list)


# ---- serving ---------------------------------------------------------------
class PredictOut(BaseModel):
    predicted_class: int
    confidence: float
