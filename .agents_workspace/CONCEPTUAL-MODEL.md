# Conceptual model

What this repository is actually claiming, which parts are production-shaped, which parts are
scaffolding built only to make the loop observable, and what was deliberately left out.

Read this before extending the system. The diagram version of the same idea — the three rings — lives
in [`ARCHITECTURE.md`](ARCHITECTURE.md#conceptual-model--three-rings), alongside the component
diagrams and the Key Decisions log. For using or operating the system, see
[`docs/guide/`](../docs/guide/index.md).

## The idea

An ML model in production degrades in ways that are visible in its output statistics long before
anyone files a ticket. This repo builds the on-call engineer for that: a closed loop that watches a
live model's prediction stream, decides on its own when something is wrong, investigates with
read-only tools until it can cite evidence, and proposes a fix that a policy table — not the model —
is allowed to execute.

## Three rings

The system is shaped as three concentric rings, and knowing which ring a piece sits in tells you how
seriously to take it.

| Ring | What it is | How to read it |
|---|---|---|
| **3 — Simulated world** | Synthetic traffic, the fault-injection harness, the CIFAR-10 CNN, `deploy` rows | Scaffolding. Exists only so the loop has something to watch and something to break |
| **2 — Sensing** | The 30s metrics aggregator, the four read-only MCP tool servers | The honest boundary. The agents see only what a real operator's telemetry would show |
| **1 — Reasoning under guardrails** | monitor → diagnosis → second opinion → adjudicator → policy → postmortem memory | The actual contribution. Written as if it were production |

Ring 1 would survive being pointed at real telemetry. Ring 3 would be thrown away.

## What is real, what is mocked

| Piece | Status | Notes |
|---|---|---|
| Agent graph, validation, fail-closed paths | Real | Production-shaped; would survive real telemetry |
| Policy table + risk gating + approval flow | Real | Deterministic, auditable, LLM cannot bypass it |
| Metrics aggregation (PSI, percentiles, entropy) | Real | Standard drift math over an actual prediction stream |
| MCP tool servers | Real | Read-only stdio servers over real DB rows |
| Postmortem memory (embed + pgvector recall) | Real, wired | Advisory context on every diagnosis; best-effort, silent on failure |
| Cost/latency/token metering | Real | Every model call becomes an `agent_run` row |
| Eval harness | Real | Replays labeled scenarios through the *live* pipeline, scores vs hidden ground truth — see below |
| The served model | Mock | A small CIFAR-10 CNN, not a real production model |
| Production traffic | Mock | Synthetic generator loop; drift and label skew applied client-side |
| The faults | Mock | Injected on demand; latency via serving middleware, the rest via transformed inputs |
| "Deployments" | Mock | Rows in a `deploy` table; "rollback" swaps the active row and serving polls it |
| `retrain_trigger`, `pipeline_fix` executors | Mock | Recorded state transitions with synthetic immediate completion — no pipeline is touched |

Only `rollback` has a real (if small) effect on the running system. The other two actions demonstrate
the approval and audit path without pretending to own infrastructure the repo does not have.

## The eval harness

The one component that is easy to miss, because nothing in the normal runtime path calls it. It is
the system's own report card.

**What it is not:** it is *not* the thing that decides whether an incident exists. That is the monitor
agent, on every window, always. The eval harness is an offline-style grader that runs on demand.

**How it works** (`backend/app/eval/`, triggered by `POST /api/eval/runs`, surfaced on the **Evals**
page):

1. `scenarios.py` defines a labeled suite of 13 cases — 3 severities × 4 fault types, plus one
   **no-fault control** that scores a false positive if any incident opens.
2. `runner.py::run_suite` resets transient state (ends live injections, restores `v1.0-good`), then
   for each scenario injects the real fault into the **live running system** and waits.
3. It polls for the first incident opened after injection time (up to 10 min), then for the accepted
   hypothesis — the adjudication if one exists, else the primary (up to 5 min).
4. It scores the case against the label the agents never see: `detected`, `diagnosis_correct`,
   `ttd_seconds`, `cost_usd` → one `eval_case` row.
5. `_finalize` aggregates the run into four headline numbers: **detection recall**, **diagnosis
   accuracy**, **mean time-to-detect**, **mean cost per incident**.

**Why it matters architecturally:** detection is a model judgment, not a threshold (see the Key
Decisions log), so there is no config value to tune and no unit test that can pin it down. The
scorecard is the only feedback signal for prompt changes — you tune `MONITOR_SYSTEM` against
detection recall and the false-positive control, not against a single anecdote. `SUITE_VERSION` marks
which scorecards are comparable to each other.

It replays through the **live** pipeline, so it requires serving + traffic + aggregator + agent graph
all running, it costs real tokens, and a full suite takes a while — each case waits out real
30-second aggregation windows. `?demo=1` runs a single drift scenario instead.

## Deliberately not built

Not oversights — scope choices, each with a known upgrade path:

- **No authentication or authorization.** Every endpoint is open; there is no user, tenant, or role.
  A real deployment needs an auth layer at the router boundary before anything else.
- **No rate limiting** on mutation endpoints (approve, inject, eval runs).
- **Single-process SSE.** The event broker is in-memory (`services/event_service.py`), so the control
  plane cannot run multiple workers or replicas without losing events. Redis pub/sub is the exit.
- **No automated test suite.** `pytest` is configured (`asyncio_mode = "auto"`) but there is no suite;
  the eval harness is the de-facto quality gate, and it grades the agents, not the code.
- **No numeric pre-filter on detection.** Every 30s window costs one cheap-model call.
- **Memory never decays or gets curated.** Postmortems accumulate; nothing prunes bad ones. Recall is
  advisory precisely because of this.
- **Rejection is a dead end.** A rejected remediation leaves its incident in `awaiting_approval` with
  no path out and no re-diagnosis.
- **Single model, single deploy lineage.** No multi-model, multi-environment, or canary concepts.

## The trade-offs that define the design

Four choices shape everything else. Each is written up in full in the Key Decisions log in
[`ARCHITECTURE.md`](ARCHITECTURE.md#key-decisions).

1. **Two processes, one database** — the DB is the integration contract, so there is no control API to
   version. Cost: the packages are not independently deployable (serving imports `backend.app.db`).
2. **Policy table beats the LLM** — actions are reproducible and auditable regardless of model
   behavior. Cost: a new fault type needs a code change, not a prompt change.
3. **Detection is model judgment, not thresholds** — handles four signals that move differently per
   fault type, without a cutoff ladder. Cost: non-deterministic, untestable by unit test, and one
   model call per window.
4. **Ground truth is withheld from the agents** — makes the eval scores mean something. Cost: every
   new MCP tool must be audited for leakage, or the numbers silently become fiction.

## If you extend this

The load-bearing invariants are in `CLAUDE.md`; break them and the demo stops being a demonstration
of anything. Highest-value next moves, roughly in order: an auth boundary; a numeric pre-filter before
the monitor call; a real test suite around the deterministic layers (policy, aggregator, state
transitions); Redis-backed events; then a rejection → re-diagnosis loop.
