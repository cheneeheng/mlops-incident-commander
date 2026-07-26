# OP-04 — Monitoring and health

## Health endpoints

| Check | Command | Healthy response |
|-------|---------|------------------|
| Control plane | `curl http://localhost:8000/health` | `{"status":"ok"}` |
| Serving | `curl http://localhost:8001/healthz` | `{"status":"ok","model_version":"v1.0-good"}` |
| Database | `docker compose ps` | The `db` service reports healthy (`pg_isready`, 5s interval) |

Serving's `/healthz` doubles as the answer to "which model is live right now" — it reports the
version actually loaded into the classifier, not what the database says should be active. A mismatch
between it and the active deploy row means the poller is stuck.

## Logs

Both processes emit structured JSON to stdout via structlog at INFO, with ISO timestamps and a
`correlation_id` bound per HTTP request. There is no log file — capture the shell output if you need
history.

Key events, and what their absence means:

| Log event | Process | Emitted when | If missing |
|-----------|---------|--------------|------------|
| `traffic_generator_started` | serving | Traffic generator finished loading CIFAR-10 | No traffic is being generated |
| `model_loaded` | serving | Weights loaded at startup | No active deploy row — reseed |
| `weights_reloaded` | serving | Poller saw a new active version | Deploy swaps are not taking effect |
| `metric_window_written` | control | A window was aggregated and committed | No traffic, or the aggregator is failing |
| `incident_opened` | control | The monitor chose to open an incident | Normal when healthy |

Error events worth alerting on:

| Log event | Meaning |
|-----------|---------|
| `aggregator_error` | The aggregation loop caught an exception; it stays alive and retries in 30 s. Repeated occurrences mean a real DB or data problem |
| `traffic_error` | A prediction POST failed. Isolated entries are transient; sustained ones mean serving is down or overloaded |
| `poller_error` | The 5 s active-state poller failed. Deploy swaps and latency injections will not take effect while this repeats |
| `monitor_failed` | The monitor's model call failed or returned unparseable output. **No incident can be opened while this repeats** — usually a bad or missing API key |
| `postmortem_generation_failed` | A remediation executed but its postmortem was not written. Non-fatal by design |
| `no_active_deploy_at_startup` | Serving started with no active deploy; it will serve nothing useful until one is activated |

## What healthy looks like

- One `metric_window_written` roughly every 30 seconds, with `request_count` around 150 (about
  5 req/s over a 30-second window). A much lower count means traffic is being lost.
- `psi` near 0 and a stable `mean_confidence` when no injection is active.
- `latency_p95` at baseline inference latency, with no injected component.
- Steady monitor `agent_run` rows — one per window — visible on the **Costs** page.

## Watching cost

The monitor agent runs on every window, so cost accrues continuously whether or not anything is
wrong: roughly 120 monitor calls per hour of uptime. Diagnosis, second opinion, adjudication, and
remediation only run per incident, but each costs far more per call.

Check the **Costs** page by day, or:

```bash
curl http://localhost:8000/api/costs/summary
```

An unexpected daily jump almost always means either an incident storm (check **Incidents**) or an
eval suite run.

## Live event stream

The SSE stream is both the dashboard's data source and a useful operator tail:

```bash
curl -N http://localhost:8000/api/events
```

Event types: `metrics_window`, `incident_opened`, `hypothesis_ready`, `remediation_queued`,
`remediation_executed`, `remediation_rejected`, `postmortem_ready`. If `metrics_window` events stop
arriving, the aggregator has stalled — see [OP-05 — Incident runbook](OP-05-runbook.md).
