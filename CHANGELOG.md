# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-07-26

Initial release — the v1 MVP of the incident loop, end to end: inject a labeled fault, watch the
agents open an incident, diagnose it, propose a risk-gated remediation, and write a postmortem.

### Added

- **Serving plane** (`serving/`, `:8001`) — a CIFAR-10 CNN classifier behind FastAPI with
  latency-injection middleware, plus the synthetic traffic generator that drives it continuously.
- **Control plane** (`backend/`, `:8000`) — REST + SSE API over Postgres 16 + pgvector for metrics,
  injections, deploys, incidents, remediations, postmortems, evals, and cost. Routers → services →
  db layer, with application-generated prefixed IDs and closed status enums.
- **Metrics aggregator** — rolls the prediction log into 30-second windows (latency percentiles,
  mean confidence, entropy, class distribution, PSI against a reference profile) and hands each
  window to the agent graph.
- **Agent graph** (LangGraph) — `monitor` triages each window and opens an incident when warranted;
  `diagnosis` investigates through the MCP tool servers and writes a schema-validated hypothesis;
  below 0.6 confidence a `second_opinion` runs independently and an `adjudicator` reconciles the
  two; `remediation` proposes an action. All LLM output is validated before any state mutation, and
  every node fails closed on a parse or API failure.
- **Policy-gated remediation** — a policy table, not the model, maps `(fault_type, confidence)` to
  `(action, risk)`. Auto-execution requires LOW risk and confidence ≥ 0.85; everything else waits
  for human approval.
- **Four read-only MCP tool servers** — the stdio tool surface the diagnosis agent queries, with a
  per-incident tool-call cap. Ground truth (`is_faulty`) is deliberately withheld from the agents.
- **Postmortem memory** — postmortems are embedded into pgvector; diagnosis retrieves the top-3
  similar past incidents as advisory context, best-effort and never blocking.
- **Injection harness** — labeled feature drift, latency degradation, bad deploy, and label skew
  faults, driven from the API or the dashboard.
- **Eval harness and scorecard** — replays a labeled scenario suite through the live pipeline and
  scores detection recall, diagnosis accuracy, mean time-to-detect, and mean cost per incident.
- **Agent telemetry** — every model call is metered as an `agent_run` with tokens, dollar cost, and
  latency, surfaced on a cost dashboard.
- **React + Vite dashboard** (`:5173`) — eight screens over the control plane, with SSE-driven
  react-query invalidation and a stub mode that renders sample data with no backend.
- **Documentation** — README, the conceptual model, the living `ARCHITECTURE.md`, a user and
  operator guide under `docs/guide/`, and runnable API demos under `examples/`.
- **CI** — a workflow that parse-validates every Mermaid diagram in tracked markdown.

[Unreleased]: https://github.com/cheneeheng/mlops-incident-commander/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/cheneeheng/mlops-incident-commander/releases/tag/v0.1.0
