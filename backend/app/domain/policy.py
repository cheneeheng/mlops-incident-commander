"""Remediation policy: maps a diagnosed fault + confidence to an action and a risk level. This table
is authoritative — the remediation agent proposes, but any disagreement resolves to this table."""

from backend.app.domain.enums import FaultType, RemediationActionType, RemediationRisk

AUTO_EXECUTE_MIN_CONFIDENCE = 0.85

# fault_type -> (action, base risk)
_POLICY: dict[FaultType, tuple[RemediationActionType, RemediationRisk]] = {
    FaultType.BAD_DEPLOY: (RemediationActionType.ROLLBACK, RemediationRisk.LOW),
    FaultType.FEATURE_DRIFT: (RemediationActionType.RETRAIN_TRIGGER, RemediationRisk.MEDIUM),
    FaultType.LABEL_SKEW: (RemediationActionType.PIPELINE_FIX, RemediationRisk.MEDIUM),
    FaultType.LATENCY: (RemediationActionType.PIPELINE_FIX, RemediationRisk.MEDIUM),
    FaultType.UNKNOWN: (RemediationActionType.PIPELINE_FIX, RemediationRisk.HIGH),
}


def decide_policy(
    fault_type: FaultType, confidence: float
) -> tuple[RemediationActionType, RemediationRisk]:
    action, risk = _POLICY[fault_type]
    # A shaky diagnosis must never stay low-risk (low-risk is what auto-executes).
    if confidence < 0.5 and risk == RemediationRisk.LOW:
        risk = RemediationRisk.MEDIUM
    return action, risk


def should_auto_execute(risk: RemediationRisk, confidence: float) -> bool:
    return risk == RemediationRisk.LOW and confidence >= AUTO_EXECUTE_MIN_CONFIDENCE


def policy_table_text() -> str:
    """Human-readable policy for the remediation prompt."""
    lines = [
        f"- {fault.value}: {action.value} (risk {risk.value})"
        for fault, (action, risk) in _POLICY.items()
    ]
    lines.append(
        f"Auto-execute only when risk is low AND confidence >= {AUTO_EXECUTE_MIN_CONFIDENCE}."
    )
    return "\n".join(lines)
