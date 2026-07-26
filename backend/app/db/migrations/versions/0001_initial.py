"""initial schema — all 13 entities, pgvector extension, incident sequence, ivfflat index

Revision ID: 0001
Revises:
Create Date: 2026-07-23
"""
from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = postgresql.TIMESTAMP(timezone=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE SEQUENCE IF NOT EXISTS incident_number_seq")

    op.create_table(
        "deploy",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("artifact_path", sa.String(512), nullable=False),
        sa.Column("deployed_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("is_faulty", sa.Boolean, nullable=False),
    )
    op.create_index("ix_deploy_model_version", "deploy", ["model_version"])
    op.create_index("ix_deploy_is_active", "deploy", ["is_active"])

    op.create_table(
        "reference_profile",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("class_distribution", postgresql.JSONB, nullable=False),
        sa.Column("mean_confidence", sa.Float, nullable=False),
    )
    op.create_index("ix_reference_profile_model_version", "reference_profile", ["model_version"])

    op.create_table(
        "prediction_log",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("ts", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("predicted_class", sa.Integer, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("latency_ms", sa.Float, nullable=False),
        sa.Column("input_ref", sa.String(128), nullable=False),
    )
    op.create_index("ix_prediction_log_ts", "prediction_log", ["ts"])
    op.create_index("ix_prediction_log_model_version", "prediction_log", ["model_version"])

    op.create_table(
        "serving_log",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("ts", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("context", postgresql.JSONB, nullable=False),
    )
    op.create_index("ix_serving_log_ts", "serving_log", ["ts"])

    op.create_table(
        "metric_window",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("window_start", TS, nullable=False),
        sa.Column("window_end", TS, nullable=False),
        sa.Column("request_count", sa.Integer, nullable=False),
        sa.Column("latency_p50", sa.Float, nullable=False),
        sa.Column("latency_p95", sa.Float, nullable=False),
        sa.Column("latency_p99", sa.Float, nullable=False),
        sa.Column("mean_confidence", sa.Float, nullable=False),
        sa.Column("prediction_entropy", sa.Float, nullable=False),
        sa.Column("psi_score", sa.Float, nullable=False),
        sa.Column("class_distribution", postgresql.JSONB, nullable=False),
    )
    op.create_index("ix_metric_window_window_start", "metric_window", ["window_start"])

    op.create_table(
        "injection",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("fault_type", sa.String(32), nullable=False),
        sa.Column("params", postgresql.JSONB, nullable=False),
        sa.Column("started_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", TS, nullable=True),
        sa.Column("ground_truth_fault", sa.String(32), nullable=False),
    )
    op.create_index("ix_injection_fault_type", "injection", ["fault_type"])

    op.create_table(
        "incident",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("number", sa.BigInteger, server_default=sa.text("nextval('incident_number_seq')"), nullable=False),
        sa.Column("opened_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", TS, nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("trigger_metrics", postgresql.JSONB, nullable=False),
        sa.UniqueConstraint("number", name="uq_incident_number"),
    )
    op.create_index("ix_incident_status", "incident", ["status"])

    op.create_table(
        "agent_run",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("incident_id", sa.String(32), sa.ForeignKey("incident.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_name", sa.String(64), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column("cost_usd", sa.Float, nullable=False),
        sa.Column("latency_ms", sa.Float, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_run_incident_id", "agent_run", ["incident_id"])
    op.create_index("ix_agent_run_agent_name", "agent_run", ["agent_name"])
    op.create_index("ix_agent_run_created_at", "agent_run", ["created_at"])

    op.create_table(
        "hypothesis",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("incident_id", sa.String(32), sa.ForeignKey("incident.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_run_id", sa.String(32), sa.ForeignKey("agent_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fault_type", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("evidence", postgresql.JSONB, nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
    )
    op.create_index("ix_hypothesis_incident_id", "hypothesis", ["incident_id"])

    op.create_table(
        "remediation",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("incident_id", sa.String(32), sa.ForeignKey("incident.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hypothesis_id", sa.String(32), sa.ForeignKey("hypothesis.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("risk", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("executed_at", TS, nullable=True),
    )
    op.create_index("ix_remediation_incident_id", "remediation", ["incident_id"])
    op.create_index("ix_remediation_status", "remediation", ["status"])

    op.create_table(
        "postmortem",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("incident_id", sa.String(32), sa.ForeignKey("incident.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body_md", sa.Text, nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(384), nullable=True),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_postmortem_incident_id", "postmortem", ["incident_id"])
    # ivfflat cosine index for top-k postmortem retrieval (ITER_04 memory).
    op.create_index(
        "ix_postmortem_embedding",
        "postmortem",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_with={"lists": 100},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "eval_run",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("started_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", TS, nullable=True),
        sa.Column("suite_version", sa.String(32), nullable=False),
        sa.Column("detection_recall", sa.Float, nullable=True),
        sa.Column("diagnosis_accuracy", sa.Float, nullable=True),
        sa.Column("mean_ttd_s", sa.Float, nullable=True),
        sa.Column("mean_cost_usd", sa.Float, nullable=True),
    )

    op.create_table(
        "eval_case",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("eval_run_id", sa.String(32), sa.ForeignKey("eval_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario_name", sa.String(128), nullable=False),
        sa.Column("injected_fault", sa.String(32), nullable=False),
        sa.Column("detected", sa.Boolean, nullable=True),
        sa.Column("diagnosis_correct", sa.Boolean, nullable=True),
        sa.Column("ttd_seconds", sa.Float, nullable=True),
        sa.Column("cost_usd", sa.Float, nullable=True),
    )
    op.create_index("ix_eval_case_eval_run_id", "eval_case", ["eval_run_id"])


def downgrade() -> None:
    for table in (
        "eval_case",
        "eval_run",
        "postmortem",
        "remediation",
        "hypothesis",
        "agent_run",
        "incident",
        "injection",
        "metric_window",
        "serving_log",
        "prediction_log",
        "reference_profile",
        "deploy",
    ):
        op.drop_table(table)
    op.execute("DROP SEQUENCE IF EXISTS incident_number_seq")
