// Hardcoded sample data for USE_STUBS mode. Shapes match lib/types.ts exactly.
import type {
  AgentRun,
  CostSummary,
  Deploy,
  EvalRunDetail,
  IncidentDetail,
  IncidentSummary,
  Injection,
  MetricWindow,
  Postmortem,
  Remediation,
} from "@/lib/types";

const now = Date.now();
const iso = (msAgo: number) => new Date(now - msAgo).toISOString();

export const sampleWindows: MetricWindow[] = Array.from({ length: 20 }, (_, i) => {
  const drift = i > 12 ? (i - 12) * 0.05 : 0;
  return {
    id: `win_${i}`,
    window_start: iso((20 - i) * 30_000),
    window_end: iso((19 - i) * 30_000),
    request_count: 150,
    latency_p50: 40 + drift * 20,
    latency_p95: 90 + drift * 120,
    latency_p99: 130 + drift * 200,
    mean_confidence: 0.82 - drift,
    prediction_entropy: 1.1 + drift * 1.5,
    psi_score: drift * 3.2,
    class_distribution: { "0": 0.1, "1": 0.1, "2": 0.1, "3": 0.1, "4": 0.1, "5": 0.1, "6": 0.1, "7": 0.1, "8": 0.1, "9": 0.1 },
  };
});

export const sampleInjections: Injection[] = [
  {
    id: "inj_001",
    fault_type: "feature_drift",
    params: { brightness: 0.4, noise: 0.2 },
    started_at: iso(6 * 60_000),
    ended_at: null,
    ground_truth_fault: "feature_drift",
  },
  {
    id: "inj_000",
    fault_type: "latency",
    params: { added_ms: 150 },
    started_at: iso(60 * 60_000),
    ended_at: iso(40 * 60_000),
    ground_truth_fault: "latency",
  },
];

export const sampleDeploys: Deploy[] = [
  { id: "dep_good", model_version: "v1.0-good", artifact_path: "weights/v1.0-good.pt", deployed_at: iso(86_400_000), is_active: true, is_faulty: false },
  { id: "dep_bad", model_version: "v1.1-bad", artifact_path: "weights/v1.1-bad.pt", deployed_at: iso(43_200_000), is_active: false, is_faulty: true },
];

export const sampleIncidents: IncidentSummary[] = [
  { id: "inc_1002", number: 1002, opened_at: iso(5 * 60_000), closed_at: null, status: "awaiting_approval", severity: "high", trigger_metrics: { psi_score: 0.31 } },
  { id: "inc_1001", number: 1001, opened_at: iso(90 * 60_000), closed_at: iso(70 * 60_000), status: "resolved", severity: "medium", trigger_metrics: { latency_p95: 240 } },
];

const sampleAgentRuns: AgentRun[] = [
  { id: "run_a", incident_id: "inc_1002", agent_name: "monitor", model: "haiku", input_tokens: 900, output_tokens: 120, cost_usd: 0.0011, latency_ms: 640, status: "success", created_at: iso(5 * 60_000) },
  { id: "run_b", incident_id: "inc_1002", agent_name: "diagnosis", model: "sonnet", input_tokens: 4200, output_tokens: 480, cost_usd: 0.018, latency_ms: 3400, status: "success", created_at: iso(4.5 * 60_000) },
];

const sampleRemediations: Remediation[] = [
  { id: "rem_1", incident_id: "inc_1002", hypothesis_id: "hyp_1", action_type: "rollback", risk: "low", status: "pending", created_at: iso(4 * 60_000), executed_at: null },
];

export const sampleIncidentDetail: IncidentDetail = {
  ...sampleIncidents[0],
  hypotheses: [
    { id: "hyp_1", incident_id: "inc_1002", agent_run_id: "run_b", fault_type: "feature_drift", confidence: 0.88, evidence: [{ tool: "preddist_server.psi", value: 0.31 }], kind: "primary" },
  ],
  remediations: sampleRemediations,
  agent_runs: sampleAgentRuns,
};

export const sampleCostSummary: CostSummary = {
  total_cost_usd: 0.0191,
  by_agent: [
    { key: "monitor", cost_usd: 0.0011, run_count: 1 },
    { key: "diagnosis", cost_usd: 0.018, run_count: 1 },
  ],
  by_incident: [{ key: "inc_1002", cost_usd: 0.0191, run_count: 2 }],
  by_day: [{ key: new Date(now).toISOString().slice(0, 10), cost_usd: 0.0191, run_count: 2 }],
};

export const samplePostmortems: Postmortem[] = [
  {
    id: "pmt_1",
    incident_id: "inc_1001",
    body_md: "# Incident #1001 — latency degradation\n\n**Root cause:** injected latency fault (+150ms).\n\n**Action:** rollback to v1.0-good.\n\n**Ground truth:** latency.",
    created_at: iso(69 * 60_000),
  },
];

export const sampleEvalRun: EvalRunDetail = {
  id: "evr_1",
  started_at: iso(30 * 60_000),
  finished_at: iso(10 * 60_000),
  suite_version: "2026.07",
  detection_recall: 0.92,
  diagnosis_accuracy: 0.83,
  mean_ttd_s: 47.5,
  mean_cost_usd: 0.019,
  cases: [
    { id: "evc_1", eval_run_id: "evr_1", scenario_name: "feature_drift/high", injected_fault: "feature_drift", detected: true, diagnosis_correct: true, ttd_seconds: 42, cost_usd: 0.02 },
    { id: "evc_2", eval_run_id: "evr_1", scenario_name: "latency/medium", injected_fault: "latency", detected: true, diagnosis_correct: false, ttd_seconds: 55, cost_usd: 0.017 },
    { id: "evc_3", eval_run_id: "evr_1", scenario_name: "control/none", injected_fault: "none", detected: false, diagnosis_correct: null, ttd_seconds: null, cost_usd: null },
  ],
};
