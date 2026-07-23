"""Closed-set domain enums. External callers may only send these values (never free-form strings)."""

from enum import StrEnum


class FaultType(StrEnum):
    FEATURE_DRIFT = "feature_drift"
    LATENCY = "latency"
    BAD_DEPLOY = "bad_deploy"
    LABEL_SKEW = "label_skew"
    UNKNOWN = "unknown"  # diagnosis taxonomy only; never a valid injection fault_type


# The faults the injection harness can produce (ground truth). Excludes UNKNOWN.
INJECTABLE_FAULTS: frozenset[FaultType] = frozenset(
    {FaultType.FEATURE_DRIFT, FaultType.LATENCY, FaultType.BAD_DEPLOY, FaultType.LABEL_SKEW}
)


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    OPEN = "open"
    DIAGNOSING = "diagnosing"
    AWAITING_APPROVAL = "awaiting_approval"
    REMEDIATING = "remediating"
    RESOLVED = "resolved"


class HypothesisKind(StrEnum):
    PRIMARY = "primary"
    SECOND_OPINION = "second_opinion"
    ADJUDICATION = "adjudication"


class AgentRunStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class RemediationActionType(StrEnum):
    ROLLBACK = "rollback"
    RETRAIN_TRIGGER = "retrain_trigger"
    PIPELINE_FIX = "pipeline_fix"


class RemediationRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RemediationStatus(StrEnum):
    PENDING = "pending"
    AUTO_EXECUTED = "auto_executed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
