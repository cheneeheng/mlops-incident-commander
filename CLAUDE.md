# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make install       # uv sync + npm install (frontend)
make db            # Postgres 16 + pgvector via docker compose
make migrate       # alembic upgrade head (tables, pgvector extension, ivfflat index)
make seed          # seed-weights (CNN checkpoints) + seed-db (deploy + reference-profile rows)

# run in three shells:
make serving       # serving app :8001 — also starts the synthetic traffic generator
make control       # control plane :8000 — also starts the metrics aggregator + agent graph
make frontend      # dashboard :5173 (Vite proxies /api -> :8000)

make lint          # ruff check .
make typecheck     # mypy backend serving mcp_servers   (strict = true)
cd frontend && npm run typecheck   # tsc -b --noEmit for the UI
```

Requires `.env` (copy `.env.example`) with `ANTHROPIC_API_KEY` — the agents call Anthropic.

`pytest` is configured (`asyncio_mode = "auto"`, no separate suite yet). Run one test with
`uv run pytest path/to/test_x.py::test_name`. Migrations must be created with the `alembic`
skill's rules; `make migrate` applies them.

## Architecture

Two independent FastAPI processes share one Postgres database. There is **no service-to-service
API for control** — they coordinate through the DB and one HTTP path (traffic → serving `/predict`).

- **Control plane** (`backend/`, `:8000`) — REST + SSE, the LangGraph agent graph, and the metrics
  aggregator background loop. Started via `backend.app.main:app`.
- **Serving** (`serving/`, `:8001`) — the CIFAR-10 CNN classifier with latency-injection middleware,
  plus the synthetic traffic generator loop (`backend/app/tasks/traffic.py`, runs in *this* process).
- `serving/` and the traffic loop **import from `backend.app.db`** — the DB models/session package is
  shared across both processes, not duplicated.

### The core pipeline (this is the system)

The whole product is one loop; understanding it requires reading `tasks/aggregator.py`,
`agents/graph.py`, and `domain/policy.py` together:

1. Traffic generator POSTs images to serving `/predict`; each prediction is written to
   `prediction_log`. Active injections (`tasks/traffic.py`) transform images before sending — feature
   drift and label skew are applied client-side; latency is injected by serving middleware.
2. **Aggregator** (`run_aggregator`, every 30s) rolls `prediction_log` into a `metric_window`
   (latency percentiles, mean confidence, entropy, class distribution, PSI vs the reference profile),
   commits it, then calls `process_window(window_id)`.
3. **LangGraph agent graph** (`agents/graph.py`) triages the window:
   `monitor` (cheap model) → opens an incident if warranted → `diagnosis` (strong model) investigates
   via MCP tools and writes a schema-valid primary hypothesis → if `confidence < 0.6`,
   `second_opinion` runs an independent diagnosis and `adjudicator` reconciles the two → `remediation`
   proposes an action → auto-execute or await human approval.
4. SSE events (`incident_opened`, `hypothesis_ready`, `remediation_queued/executed`, `metrics_window`)
   are published to the in-process broker and streamed to the dashboard, which invalidates its
   react-query caches on receipt.

### Non-negotiable invariants (violating these breaks the design)

- **The policy table is authoritative, not the LLM** (`domain/policy.py`). `decide_policy` maps
  `(fault_type, confidence)` → `(action, risk)`; the remediation agent only supplies a *rationale*
  (logged). Auto-execute happens only when `risk == LOW and confidence >= 0.85` (`should_auto_execute`).
  A `confidence < 0.5` LOW-risk action is bumped to MEDIUM so it can never auto-execute.
- **All LLM output is validated before any state mutation.** Every LLM-output model uses
  `ConfigDict(extra="forbid")` and is `model_validate`d; on parse/API failure the node **fails closed**
  (e.g. `_fail_closed` → `FaultType.UNKNOWN`, low confidence) rather than mutating state on garbage.
- **`is_faulty` is hidden ground truth.** `mcp_servers/_common.py::deploy_dict` deliberately omits it —
  the diagnosis agent must infer a bad deploy from metrics, never read the flag. Same for the injection
  row's ground truth: only the eval runner reads it, to score.
- **Layer boundaries:** routers → services → `db/queries.py`. Route handlers hold no business logic;
  services hold no SQL; the db layer holds no business logic. Public IDs are prefixed/app-generated
  (`domain/ids.py`); status fields are closed enums (`domain/enums.py`) with validated transitions.

### Agents & MCP

- `agents/graph.py` is the graph; nodes each open their own `SessionLocal()` and commit independently
  (they must see the aggregator's committed window). Every model call is metered as an `agent_run`
  (tokens, `cost_usd` via `config.py::cost_usd`, latency) through `agents/telemetry.py`.
- The four MCP servers (`mcp_servers/*_server.py`) are **read-only stdio tool servers** the diagnosis
  agent spawns via `McpToolbox`; tool time ranges are ISO-8601. Tool-call count is capped
  (`_TOOL_CALL_CAP = 12`).
- Postmortem memory: `agents/postmortem.py` embeds postmortems (`sentence-transformers` → pgvector);
  diagnosis retrieves the top-3 similar past postmortems as **advisory** context (best-effort — never
  blocks diagnosis on retrieval failure).

### Eval harness

`backend/app/eval/runner.py` (spawned by `POST /api/eval/runs`) replays the labeled scenario suite
(`eval/scenarios.py`) through the **live** pipeline — it drives injections and scores the resulting
incidents/hypotheses against ground truth (detection recall, diagnosis accuracy, mean TTD, mean cost).
It assumes serving + traffic + aggregator + agent graph are all running.

### Gotchas (flagged in-source)

- **`get_settings()` is `lru_cache`d** — tests mutating the environment must call
  `get_settings.cache_clear()`.
- **CORS middleware is added last** in `main.py` so Starlette wraps it outermost; don't reorder.
- **Frontend stubs:** `frontend/src/lib/config.ts` — `VITE_USE_STUBS=1` renders sample data with no
  backend; defaults to the real control plane. All `fetch` goes through `$lib/api` (aliased `@/lib`).
