# OP-02 — Configuration reference

[← Guide index](../index.md)

Configuration comes from the environment, loaded from `.env` at process start. Unknown keys in
`.env` are ignored. **Never commit `.env`.**

## Backend settings

Every value below has the default shown; only `ANTHROPIC_API_KEY` must be set by hand.

| Variable | Purpose | Default | Notes |
|----------|---------|---------|-------|
| `DATABASE_URL` | Postgres connection for both processes | `postgresql+asyncpg://icc:icc@localhost:5432/icc` | Must use the `postgresql+asyncpg://` driver. Matches `docker-compose.yml` |
| `ANTHROPIC_API_KEY` | Credential for all agent model calls | `""` | Required. With it empty, windows still aggregate but no incident is ever opened |
| `MODEL_CHEAP` | Model for the monitor agent, which runs on every window | `claude-haiku-4-5-20251001` | Chosen for cost — it is the highest-frequency call in the system |
| `MODEL_STRONG` | Model for diagnosis, second opinion, adjudication, and remediation | `claude-sonnet-5` | |
| `SERVING_URL` | Where the traffic generator POSTs predictions | `http://localhost:8001` | Read by the serving process, which hosts the generator |
| `CORS_ORIGINS` | Comma-separated allowed browser origins | `http://localhost:5173` | No wildcard. Split on commas and trimmed |
| `COST_PER_MTOK_INPUT` | Fallback input price, $ per 1M tokens | `1.0` | Used only for models absent from the built-in price table |
| `COST_PER_MTOK_OUTPUT` | Fallback output price, $ per 1M tokens | `5.0` | Same |

Costing is tiered by model: the configured `MODEL_CHEAP` is priced at $0.80/$4.00 per million input
and output tokens, `MODEL_STRONG` at $3.00/$15.00. Any other model id falls back to the two
`COST_PER_MTOK_*` values. Change `MODEL_CHEAP` or `MODEL_STRONG` and the tiering follows the new ids
automatically — but the built-in rates are illustrative, so recheck them against real pricing if the
Costs page is used for anything that matters.

> **Warning:** settings are cached process-wide. Changing `.env` has no effect until you restart the
> affected process.

## Frontend settings

Vite environment variables, read at build/dev-server start.

| Variable | Purpose | Default | Notes |
|----------|---------|---------|-------|
| `VITE_USE_STUBS` | Render hardcoded sample data instead of calling the backend | unset (real backend) | Any value other than `0` enables stubs. When on, a **sample data** badge shows in the header and no network calls are made |

The dev server listens on port 5173 and proxies `/api` to `http://localhost:8000`, which covers both
the REST endpoints and the `/api/events` SSE stream. If you move the control plane off port 8000,
update the proxy target in `frontend/vite.config.ts`.

## Fixed values (not configurable via environment)

Change these in source only, and understand the consequence first.

| Value | Where | Effect |
|-------|-------|--------|
| 30-second aggregation window | `backend/app/tasks/aggregator.py` | Also the aggregator's sleep interval; sets the whole system's detection granularity |
| ~5 requests/second traffic rate | `backend/app/tasks/traffic.py` | Lower it and windows get statistically noisy |
| 5-second active-state poll | `serving/app/main.py` | How fast serving picks up a deploy swap or a latency injection |
| Auto-execute threshold: risk `low` and confidence ≥ 0.85 | `backend/app/domain/policy.py` | The safety gate on unattended actions |
| Second-opinion trigger: primary confidence < 0.6 | `backend/app/agents/graph.py` | Lowering it cuts cost and cross-checking together |
| Diagnosis tool-call cap: 12 | `backend/app/agents/graph.py` | Hitting the cap fails the diagnosis closed to `unknown` |
| Eval timeouts: 600 s detection, 300 s hypothesis | `backend/app/eval/runner.py` | Per case |
| Known deploy versions `v1.0-good` / `v1.1-bad` | seeds, injection and remediation services | Rollback targets `v1.0-good` by name |

## Security notes

- Secrets are loaded through `pydantic-settings` from `.env` and are never hard-coded or logged.
- CORS is an explicit allowlist with credentials disabled — there is no wildcard origin.
- There is no authentication on either process. **Do not expose port 8000 or 8001 beyond localhost
  or a trusted network.** Anyone who can reach the control plane can inject faults and approve
  remediations.
- Structured JSON logs carry a `correlation_id` per request, echoed as the `X-Correlation-ID`
  response header. Secrets, PII, and full LLM content are deliberately kept out of logs.

---

[← OP-01 Install and first run](OP-01-install.md) · [Guide index](../index.md) · [OP-03 Routine operations →](OP-03-routine-operations.md)
