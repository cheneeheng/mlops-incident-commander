// Centralized API client. Components never call fetch directly — they call these typed methods.
// When USE_STUBS is set, methods return sample data so the UI works without a live backend.
import { USE_STUBS } from "@/lib/config";
import * as sample from "@/lib/sampleData";
import type {
  AgentRun,
  CostSummary,
  Deploy,
  EvalRun,
  EvalRunDetail,
  IncidentDetail,
  IncidentSummary,
  Injection,
  InjectableFault,
  MetricWindow,
  Postmortem,
  Remediation,
} from "@/lib/types";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new ApiError(res.status, `${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export const api = {
  listWindows: (): Promise<MetricWindow[]> =>
    USE_STUBS ? Promise.resolve(sample.sampleWindows) : request("/metrics/windows"),

  listInjections: (): Promise<Injection[]> =>
    USE_STUBS ? Promise.resolve(sample.sampleInjections) : request("/injections"),

  createInjection: (fault_type: InjectableFault, params: Record<string, number>): Promise<Injection> =>
    request("/injections", { method: "POST", body: JSON.stringify({ fault_type, params }) }),

  stopInjection: (id: string): Promise<Injection> =>
    request(`/injections/${id}/stop`, { method: "POST" }),

  listDeploys: (): Promise<Deploy[]> =>
    USE_STUBS ? Promise.resolve(sample.sampleDeploys) : request("/deploys"),

  activateDeploy: (model_version: string): Promise<Deploy> =>
    request("/deploys/activate", { method: "POST", body: JSON.stringify({ model_version }) }),

  listIncidents: (): Promise<IncidentSummary[]> =>
    USE_STUBS ? Promise.resolve(sample.sampleIncidents) : request("/incidents"),

  getIncident: (id: string): Promise<IncidentDetail> =>
    USE_STUBS ? Promise.resolve(sample.sampleIncidentDetail) : request(`/incidents/${id}`),

  approveRemediation: (id: string): Promise<Remediation> =>
    request(`/remediations/${id}/approve`, { method: "POST" }),

  rejectRemediation: (id: string): Promise<Remediation> =>
    request(`/remediations/${id}/reject`, { method: "POST" }),

  listPostmortems: (): Promise<Postmortem[]> =>
    USE_STUBS ? Promise.resolve(sample.samplePostmortems) : request("/postmortems"),

  getPostmortem: (id: string): Promise<Postmortem> =>
    USE_STUBS
      ? Promise.resolve(sample.samplePostmortems[0])
      : request(`/postmortems/${id}`),

  listAgentRuns: (): Promise<AgentRun[]> =>
    USE_STUBS ? Promise.resolve(sample.sampleIncidentDetail.agent_runs) : request("/agent-runs"),

  costSummary: (): Promise<CostSummary> =>
    USE_STUBS ? Promise.resolve(sample.sampleCostSummary) : request("/costs/summary"),

  listEvalRuns: (): Promise<EvalRun[]> =>
    USE_STUBS ? Promise.resolve([sample.sampleEvalRun]) : request("/eval/runs"),

  getEvalRun: (id: string): Promise<EvalRunDetail> =>
    USE_STUBS ? Promise.resolve(sample.sampleEvalRun) : request(`/eval/runs/${id}`),

  startEvalRun: (): Promise<EvalRun> => request("/eval/runs", { method: "POST" }),
};

export { ApiError };
