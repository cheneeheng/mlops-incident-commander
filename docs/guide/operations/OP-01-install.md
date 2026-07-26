# OP-01 — Install and first run

**Audience:** operators. Assumes a shell, Docker, and the repository checked out.

## System overview

Two independent FastAPI processes share one Postgres database. There is **no service-to-service API
for control** — they coordinate through the database plus one HTTP path (traffic → serving
`/predict`).

```
                     ┌──────────────────────────────┐
  browser :5173 ───► │ control plane :8000          │
   (Vite proxies     │  REST + SSE                  │
    /api → :8000)    │  metrics aggregator (30s)    │
                     │  LangGraph agent graph       │
                     └───────────┬──────────────────┘
                                 │ SQLAlchemy
                     ┌───────────▼──────────────────┐
                     │ Postgres 16 + pgvector :5432 │
                     └───────────▲──────────────────┘
                                 │ SQLAlchemy
                     ┌───────────┴──────────────────┐
                     │ serving :8001                │
                     │  CNN /predict                │
                     │  latency-injection middleware│
                     │  traffic generator (~5 req/s)│
                     │  5s active-state poller      │
                     └──────────────────────────────┘
```

The four MCP tool servers are not long-running services — the diagnosis agent spawns them as
read-only stdio subprocesses on demand.

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node 20 and npm
- Docker (for Postgres)
- An Anthropic API key — the agents call the Anthropic API, and the system does nothing useful
  without one

## Install

1. Install Python and frontend dependencies.

   ```bash
   make install
   ```

   This runs `uv sync` and `cd frontend && npm install`.

2. Create the environment file and fill in the API key.

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and replace the placeholder `ANTHROPIC_API_KEY=sk-ant-xxxxxxxx` with a real key. Every
   other value works as-is for local development — see
   [OP-02 — Configuration](OP-02-configuration.md). `.env` is never committed.

3. Start Postgres.

   ```bash
   make db
   ```

   This brings up `pgvector/pgvector:pg16` on port 5432 with database, user, and password all `icc`,
   and a named volume `pgdata`. Confirm it is healthy:

   ```bash
   docker compose ps
   ```

   The `db` service must show a healthy state before you migrate.

4. Create the schema.

   ```bash
   make migrate
   ```

   This runs `alembic upgrade head`, creating all tables, the pgvector extension, and the ivfflat
   index.

5. Seed the model checkpoints and the baseline rows.

   ```bash
   make seed
   ```

   This writes `weights/v1.0-good.pt` and `weights/v1.1-bad.pt`, then inserts the two deploy rows
   (`v1.0-good` active and healthy, `v1.1-bad` inactive and faulty) and the `v1.0-good` reference
   profile. Both seed steps are idempotent — re-running prints `=` lines for rows that already
   exist.

**Verify installation:** `make seed` prints a line for each of the two deploys and the reference
profile, and `weights/` contains both `.pt` files.

## First run

Run these in three separate shells. Order matters only in that the control plane's aggregator has
nothing to aggregate until serving is producing traffic.

1. Shell 1 — serving on `:8001`. This also starts the synthetic traffic generator and the 5-second
   active-state poller.

   ```bash
   make serving
   ```

   On the first run the traffic generator downloads the CIFAR-10 test set into `data/`, which takes
   a minute. Wait for the log line `traffic_generator_started`.

2. Shell 2 — control plane on `:8000`. This also starts the metrics aggregator and the agent graph.

   ```bash
   make control
   ```

3. Shell 3 — dashboard on `:5173`.

   ```bash
   make frontend
   ```

**Verify the whole stack:**

```bash
curl http://localhost:8001/healthz
curl http://localhost:8000/health
```

Expected output:

```
{"status":"ok","model_version":"v1.0-good"}
{"status":"ok"}
```

Then open <http://localhost:5173>. Within about a minute the **Dashboard** charts should show their
first point, and the control plane log should contain a `metric_window_written` entry.

**If it fails:** see [OP-05 — Incident runbook](OP-05-runbook.md). The most common first-run failures
are a `db` container that is not yet healthy (every process logs connection errors) and a missing or
invalid `ANTHROPIC_API_KEY` (metrics flow, but no incident is ever opened and the control plane logs
`monitor_failed`).

**Next:** [OP-02 — Configuration](OP-02-configuration.md).
