// Mirror of backend Pydantic response models. Closed sets use `as const` unions (no TS enums).

export const FAULT_TYPES = ["feature_drift", "latency", "bad_deploy", "label_skew", "unknown"] as const;
export type FaultType = (typeof FAULT_TYPES)[number];

export const INJECTABLE_FAULTS = ["feature_drift", "latency", "bad_deploy", "label_skew"] as const;
export type InjectableFault = (typeof INJECTABLE_FAULTS)[number];

export type IncidentStatus =
  | "open"
  | "diagnosing"
  | "awaiting_approval"
  | "remediating"
  | "resolved";
export type Severity = "low" | "medium" | "high" | "critical";
export type HypothesisKind = "primary" | "second_opinion" | "adjudication";
export type RemediationActionType = "rollback" | "retrain_trigger" | "pipeline_fix";
export type RemediationRisk = "low" | "medium" | "high";
export type RemediationStatus =
  | "pending"
  | "auto_executed"
  | "approved"
  | "rejected"
  | "executed"
  | "failed";

export type MetricWindow = {
  id: string;
  window_start: string;
  window_end: string;
  request_count: number;
  latency_p50: number;
  latency_p95: number;
  latency_p99: number;
  mean_confidence: number;
  prediction_entropy: number;
  psi_score: number;
  class_distribution: Record<string, number>;
};

export type Injection = {
  id: string;
  fault_type: string;
  params: Record<string, number>;
  started_at: string;
  ended_at: string | null;
  ground_truth_fault: string;
};

export type Deploy = {
  id: string;
  model_version: string;
  artifact_path: string;
  deployed_at: string;
  is_active: boolean;
  is_faulty: boolean;
};

export type AgentRun = {
  id: string;
  incident_id: string | null;
  agent_name: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
  status: string;
  created_at: string;
};

export type Hypothesis = {
  id: string;
  incident_id: string;
  agent_run_id: string;
  fault_type: FaultType;
  confidence: number;
  evidence: unknown[];
  kind: HypothesisKind;
};

export type Remediation = {
  id: string;
  incident_id: string;
  hypothesis_id: string;
  action_type: RemediationActionType;
  risk: RemediationRisk;
  rationale: string;
  status: RemediationStatus;
  created_at: string;
  executed_at: string | null;
};

export type IncidentSummary = {
  id: string;
  number: number;
  opened_at: string;
  closed_at: string | null;
  status: IncidentStatus;
  severity: Severity;
  trigger_metrics: Record<string, unknown>;
};

export type IncidentDetail = IncidentSummary & {
  hypotheses: Hypothesis[];
  remediations: Remediation[];
  agent_runs: AgentRun[];
};

export type Postmortem = {
  id: string;
  incident_id: string;
  body_md: string;
  created_at: string;
};

export type CostBucket = { key: string; cost_usd: number; run_count: number };
export type CostSummary = {
  total_cost_usd: number;
  by_agent: CostBucket[];
  by_incident: CostBucket[];
  by_day: CostBucket[];
};

export type EvalCase = {
  id: string;
  eval_run_id: string;
  scenario_name: string;
  injected_fault: string;
  detected: boolean | null;
  diagnosis_correct: boolean | null;
  ttd_seconds: number | null;
  cost_usd: number | null;
};

export type EvalRun = {
  id: string;
  started_at: string;
  finished_at: string | null;
  suite_version: string;
  detection_recall: number | null;
  diagnosis_accuracy: number | null;
  mean_ttd_s: number | null;
  mean_cost_usd: number | null;
};

export type EvalRunDetail = EvalRun & { cases: EvalCase[] };
