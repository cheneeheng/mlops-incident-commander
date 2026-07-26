"""All ORM models in one registry. Full target schema stated upfront (SKELETON §02); iterations
make entities 'live' but add no new tables. IDs are app-generated prefixed tokens; status/enum
columns store StrEnum values as text and are validated at the API boundary by Pydantic."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Sequence,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.domain.ids import new_id

# gotcha (incident numbering): human-facing incident numbers come from a DB sequence, never MAX+1,
# so concurrent opens can't collide.
incident_number_seq = Sequence("incident_number_seq")


def _id(entity: str):  # type: ignore[no-untyped-def]
    return mapped_column(String(32), primary_key=True, default=lambda: new_id(entity))


class Deploy(Base):
    __tablename__ = "deploy"
    id: Mapped[str] = _id("deploy")
    model_version: Mapped[str] = mapped_column(String(64), index=True)
    artifact_path: Mapped[str] = mapped_column(String(512))
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_faulty: Mapped[bool] = mapped_column(Boolean, default=False)  # hidden ground truth


class ReferenceProfile(Base):
    __tablename__ = "reference_profile"
    id: Mapped[str] = _id("reference_profile")
    model_version: Mapped[str] = mapped_column(String(64), index=True)
    class_distribution: Mapped[dict] = mapped_column(JSONB)
    mean_confidence: Mapped[float] = mapped_column(Float)


class PredictionLog(Base):
    __tablename__ = "prediction_log"
    id: Mapped[str] = _id("prediction_log")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    model_version: Mapped[str] = mapped_column(String(64), index=True)
    predicted_class: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[float] = mapped_column(Float)
    input_ref: Mapped[str] = mapped_column(String(128))


class ServingLog(Base):
    __tablename__ = "serving_log"
    id: Mapped[str] = _id("serving_log")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    level: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)


class MetricWindow(Base):
    __tablename__ = "metric_window"
    id: Mapped[str] = _id("metric_window")
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    request_count: Mapped[int] = mapped_column(Integer)
    latency_p50: Mapped[float] = mapped_column(Float)
    latency_p95: Mapped[float] = mapped_column(Float)
    latency_p99: Mapped[float] = mapped_column(Float)
    mean_confidence: Mapped[float] = mapped_column(Float)
    prediction_entropy: Mapped[float] = mapped_column(Float)
    psi_score: Mapped[float] = mapped_column(Float)
    class_distribution: Mapped[dict] = mapped_column(JSONB)


class Injection(Base):
    __tablename__ = "injection"
    id: Mapped[str] = _id("injection")
    fault_type: Mapped[str] = mapped_column(String(32), index=True)
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ground_truth_fault: Mapped[str] = mapped_column(String(32))


class Incident(Base):
    __tablename__ = "incident"
    id: Mapped[str] = _id("incident")
    number: Mapped[int] = mapped_column(
        BigInteger, incident_number_seq, server_default=incident_number_seq.next_value(), unique=True
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    trigger_metrics: Mapped[dict] = mapped_column(JSONB, default=dict)


class AgentRun(Base):
    __tablename__ = "agent_run"
    id: Mapped[str] = _id("agent_run")
    incident_id: Mapped[str | None] = mapped_column(
        ForeignKey("incident.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(64))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Hypothesis(Base):
    __tablename__ = "hypothesis"
    id: Mapped[str] = _id("hypothesis")
    incident_id: Mapped[str] = mapped_column(ForeignKey("incident.id", ondelete="CASCADE"), index=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_run.id", ondelete="CASCADE"))
    fault_type: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    evidence: Mapped[list] = mapped_column(JSONB, default=list)  # tool-call citations
    kind: Mapped[str] = mapped_column(String(32), default="primary")


class Remediation(Base):
    __tablename__ = "remediation"
    id: Mapped[str] = _id("remediation")
    incident_id: Mapped[str] = mapped_column(ForeignKey("incident.id", ondelete="CASCADE"), index=True)
    hypothesis_id: Mapped[str] = mapped_column(ForeignKey("hypothesis.id", ondelete="CASCADE"))
    action_type: Mapped[str] = mapped_column(String(32))
    risk: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Postmortem(Base):
    __tablename__ = "postmortem"
    id: Mapped[str] = _id("postmortem")
    incident_id: Mapped[str] = mapped_column(ForeignKey("incident.id", ondelete="CASCADE"), index=True)
    body_md: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvalRun(Base):
    __tablename__ = "eval_run"
    id: Mapped[str] = _id("eval_run")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suite_version: Mapped[str] = mapped_column(String(32))
    detection_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    diagnosis_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    mean_ttd_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    mean_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)


class EvalCase(Base):
    __tablename__ = "eval_case"
    id: Mapped[str] = _id("eval_case")
    eval_run_id: Mapped[str] = mapped_column(ForeignKey("eval_run.id", ondelete="CASCADE"), index=True)
    scenario_name: Mapped[str] = mapped_column(String(128))
    injected_fault: Mapped[str] = mapped_column(String(32))
    detected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    diagnosis_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ttd_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
