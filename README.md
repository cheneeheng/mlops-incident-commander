# MLOps Incident Commander

A multi-agent system that supervises a live ML model. A FastAPI service serves a small image
classifier under continuous synthetic traffic; an injection harness introduces labeled faults
(feature drift, latency degradation, bad deploy, label skew). Agents running in one LangGraph
process detect incidents, diagnose root cause through custom MCP tool servers, propose risk-gated
remediations, and write postmortems that feed future diagnoses. Every agent run is metered for
tokens, dollars, and latency, and a scored eval harness replays a labeled incident suite.

**Core flow:** inject fault → monitor opens incident → diagnosis produces cited hypothesis →
remediation queued → human approves → postmortem appears.

## Architecture

- `backend/` — control plane FastAPI app: metrics, injections, deploys, incidents, remediations,
  postmortems, evals, costs, SSE events. Routers → services → db layer. LangGraph agent graph and
  background tasks (metrics aggregator) live here.
- `serving/` — the live image classifier (CNN) with latency-injection middleware.
- `mcp_servers/` — four read-only MCP stdio tool servers the diagnosis agent queries.
- `frontend/` — React + Vite + TypeScript dashboard (8 screens).
- `scripts/` — utilities (CNN weight seeding).

Design rationale — component diagrams, the detect → diagnose → remediate → postmortem flow, the state
machines, and the Key Decisions log (why the two processes share one database, why the policy table
outranks the LLM, why detection is model judgment rather than a threshold) —
lives in [`.agents_workspace/ARCHITECTURE.md`](.agents_workspace/ARCHITECTURE.md).

## Prerequisites

- Python 3.12, [uv](https://docs.astral.sh/uv/), Node 20, Docker.
- Copy `.env.example` to `.env` and fill `ANTHROPIC_API_KEY` (the agents call Anthropic).

## Run

```bash
make install         # uv sync + npm install
make db              # Postgres 16 + pgvector via Docker Compose
make migrate         # alembic upgrade head (creates all tables, extension, ivfflat index)
make seed-weights    # generate CNN weights (v1.0-good, v1.1-bad) into weights/

# in separate shells:
make serving         # serving app on :8001 (also runs the synthetic traffic generator)
make control         # control plane on :8000 (runs the metrics aggregator + agent graph)
make frontend        # dashboard on :5173 (proxies /api to :8000)
```

The frontend renders sample data until a backend is live. Set `VITE_USE_STUBS=0` (or edit
`frontend/src/lib/config.ts`) to use the real control plane.

## Development

```bash
make lint            # ruff
make typecheck       # mypy (backend) — cd frontend && npm run typecheck for the UI
```
