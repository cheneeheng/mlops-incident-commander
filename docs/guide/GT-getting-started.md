# GT — What the system does, and a tour of the dashboard

**Audience:** anyone using the dashboard. No shell access or knowledge of the internals is assumed.

## What it does

A small CNN classifies CIFAR-10 images under continuous synthetic traffic. Every 30 seconds the
system summarises that traffic into a **window** and hands it to a monitor agent. If the window
looks unhealthy, the monitor opens an **incident**; a diagnosis agent then investigates through
read-only tool servers and writes a **hypothesis** (fault type + confidence + evidence). A policy
table maps that diagnosis to a **remediation** and a risk level. Low-risk, high-confidence actions
execute automatically; everything else waits for a human to approve it on the **Approvals** page.
When a remediation executes, the incident resolves and a **postmortem** is written.

The one-line flow:

> inject fault → incident opened → hypothesis produced → remediation queued → you approve →
> postmortem appears

## Before you begin

- A running control plane and dashboard. Your operator sets these up (see
  [OP-01 — Install and first run](operations/OP-01-install.md)); the dashboard is normally at
  <http://localhost:5173>.
- A modern browser. The dashboard holds one live server-sent-events connection open, so pages update
  themselves — you should not need to refresh.

## The seven pages

The left sidebar, top to bottom.

| Page | What it shows | Use it to |
|------|---------------|-----------|
| **Dashboard** | Four live charts — **Latency p95 (ms)**, **PSI score**, **Prediction entropy**, **Mean confidence** — plus a live event feed | See current health at a glance |
| **Incidents** | Table of all incidents: **#**, **Status**, **Severity**, **Opened**, **Closed** | Find an incident to investigate |
| **Inject** | A fault picker with an **Inject fault** button, plus active and past injections | Run a drill |
| **Approvals** | One card per remediation awaiting a decision, with **Approve** and **Reject** | Act on a queued remediation |
| **Postmortems** | The generated write-up for each resolved incident | Read what happened after the fact |
| **Costs** | Total agent spend, broken down by agent, by incident, and by day | Track token spend |
| **Evals** | Scorecards from replays of the labeled scenario suite | Measure detection and diagnosis quality |

## Reading the Dashboard charts

Each point is one 30-second window, labelled by the time the window ended.

- **Latency p95 (ms)** — the slow tail of request latency. A step change upward is the signature of
  a latency fault.
- **PSI score** — drift of the predicted-class mix against the reference profile. Rises under
  feature drift and label skew. `0` means the distribution matches the baseline.
- **Prediction entropy** — how spread out the predicted classes are. Drops sharply when traffic
  collapses onto one class (label skew).
- **Mean confidence** — average model confidence. A sustained drop is a common sign of a bad deploy
  or heavy drift.

Below the charts, the **event feed** lists the most recent 50 system events (incidents opened,
hypotheses ready, remediations queued and executed, postmortems ready) as they happen.

## Statuses you will see

An incident moves through: `open` → `diagnosing` → `awaiting_approval` → `remediating` →
`resolved`. Not every incident visits every state — a low-risk, high-confidence remediation
auto-executes and the incident goes straight to `resolved` without ever appearing on **Approvals**.

A remediation is one of: `pending` (waiting for you), `approved`, `rejected`, `executed`,
`auto_executed`, or `failed`.

**Next:** [HT-01 — Run a fault drill](how-to/HT-01-run-a-fault-drill.md).
