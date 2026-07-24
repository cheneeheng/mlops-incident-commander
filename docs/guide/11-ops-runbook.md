# 11 — Incident runbook

One entry per failure mode: detection → diagnosis → remediation → verification. Read
[10 — Monitoring](10-ops-monitoring.md) first for the health checks referenced throughout.

---

## No metric windows are being produced

**Detection:** Dashboard charts flat or empty; no `metric_window_written` in the control plane log;
`curl -N http://localhost:8000/api/events` shows no `metrics_window` events.

**Diagnosis:** work outward from the data source.

1. Is traffic flowing? Look for `traffic_generator_started` in the serving log, and for repeated
   `traffic_error` entries.
2. Is serving up? `curl http://localhost:8001/healthz`.
3. Is the database up? `docker compose ps`.
4. Is the aggregator erroring? Look for repeated `aggregator_error` in the control plane log.

A single `aggregator_empty_window` at DEBUG is normal right after startup — there is simply nothing
in the last 30 seconds yet.

**Remediation:**
- Serving down → restart it (`make serving`).
- Database down → `make db`, wait for healthy, then restart both application processes.
- Traffic generator never started → it downloads CIFAR-10 into `data/` on first run; check for
  network or disk-permission errors in the serving log.
- Aggregator erroring persistently → restart the control plane (`make control`).

**Verify:** a `metric_window_written` line appears within 30 seconds, and the Dashboard charts
advance.

---

## Windows are produced but no incident is ever opened

**Detection:** `metric_window_written` lines are healthy, an injection is clearly active, but no
`incident_opened` follows over several windows.

**Diagnosis:**
1. Check for `monitor_failed` in the control plane log. That is the model call failing — almost
   always a missing, invalid, or rate-limited `ANTHROPIC_API_KEY`.
2. If no `monitor_failed` appears, the monitor is running and choosing not to open an incident. Look
   at the window values: if PSI and latency really are near baseline, the injection is not biting.

**Remediation:**
- Bad key → fix `ANTHROPIC_API_KEY` in `.env` and **restart the control plane**. Settings are cached
  per process, so an edit alone changes nothing.
- Rate limiting → wait, or move `MODEL_CHEAP` to a model with headroom.
- Injection not biting → confirm it is listed under **Active injections**, and prefer `bad_deploy`
  for an unmistakable signal.

**Verify:** an `incident_opened` line appears, and the incident shows on the **Incidents** page.

---

## Incidents stall in `open` or `diagnosing`

**Detection:** an incident exists on the **Incidents** page but never gains a hypothesis or a
remediation.

**Diagnosis:** the diagnosis agent spawns four MCP stdio tool servers as subprocesses. Failures show
as an incident that stops advancing. Check the control plane log for exceptions around the incident's
timestamp, and confirm the Anthropic API is reachable.

**Remediation:**
1. Confirm the MCP servers start standalone:

   ```bash
   uv run python -m mcp_servers.metrics_server
   ```

   It should start and wait on stdio; `Ctrl+C` to exit. An import or database error here is the
   cause.
2. Restart the control plane.

Note that a diagnosis which reaches its 12-tool-call cap does **not** stall — it fails closed to
`unknown` with confidence 0.1, producing a high-risk `pipeline_fix` that requires approval. That is
correct behaviour, not a fault.

**Verify:** the incident gains a hypothesis and a remediation; a `hypothesis_ready` event fires.

---

## A deploy swap or latency injection has no effect

**Detection:** `/api/deploys/activate` returned 200, or a `latency` injection is active, but
`/healthz` still reports the old `model_version` or latency p95 has not moved.

**Diagnosis:** serving reflects database state through a 5-second poller. Repeated `poller_error`
entries in the serving log mean it is failing; the absence of `weights_reloaded` after an activation
means it never saw the change.

**Remediation:** restart serving (`make serving`). On startup it loads the active deploy directly.

**Verify:** `curl http://localhost:8001/healthz` reports the expected `model_version`; for a latency
injection, the next window's `latency_p95` rises by roughly the injected `added_latency_ms`.

---

## The dashboard shows sample data

**Detection:** a **sample data** badge in the dashboard header, and no network calls to `/api`.

**Diagnosis:** `VITE_USE_STUBS` is set to something other than `0` in the frontend environment.

**Remediation:** unset it (or set `VITE_USE_STUBS=0`) and restart the dev server — Vite reads
environment variables at start.

**Verify:** the badge disappears and the Dashboard renders live windows.

---

## The dashboard cannot reach the control plane

**Detection:** pages error, the event feed is silent, browser console shows failed `/api` requests.

**Diagnosis:**
1. Is the control plane up? `curl http://localhost:8000/health`.
2. Is the browser origin allowed? `CORS_ORIGINS` must contain the origin serving the dashboard.
3. Is the Vite proxy pointing at the right port? The dev server proxies `/api` to
   `http://localhost:8000`.

**Remediation:** start the control plane; or add the origin to `CORS_ORIGINS` and restart the control
plane; or correct the proxy target in `frontend/vite.config.ts` and restart the dev server.

**Verify:** the Dashboard loads windows and the event feed receives events.

---

## An eval run never finishes

**Detection:** an eval run row keeps showing `—` for its scores long past expectations.

**Diagnosis:** the runner replays through the live pipeline and only drives injections — it depends
on serving, traffic, the aggregator, and the agent graph all running. If any is down, every case
waits out its timeouts: 600 s for detection plus 300 s for a hypothesis, per case, across 13 cases.

**Remediation:** confirm the full stack is healthy ([10](10-ops-monitoring.md)) and let the run
finish; then start a new run. Do not run two suites at once — the runner clears active injections
and resets the active deploy when it starts, so concurrent runs corrupt each other's cases.

**Verify:** the run's scores populate, and the per-case scorecard is complete.

---

## Escalation

There is no on-call rotation for this system. When the runbook runs out:

1. Capture the failing process's log output and the `correlation_id` from the failing request, if
   there is one.
2. Note the incident number and window timestamps involved.
3. Record what you changed while diagnosing, so the next person is not debugging your fix.
4. Raise it with the repository owner.
