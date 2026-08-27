# MLOps Incident Commander — Guide

The Incident Commander watches a live image-classification service. A traffic generator sends a
steady stream of CIFAR-10 images to the model; a metrics aggregator rolls those predictions into
30-second windows; a set of agents triages each window, opens an incident when something looks
wrong, diagnoses the root cause, and proposes a remediation that either auto-executes or waits for
your approval.

Start with **Getting started**, then use the **HT** how-to pages for individual tasks. The `HT-`
pages are the **user guide** (dashboard only, no shell access needed); the `OP-` pages are the
**operator guide** (installing, running, and recovering the system). The two are kept separate on
purpose. **Troubleshooting** covers what you can see and fix from the browser; operators in a live
incident want [OP-05 — Incident runbook](operations/OP-05-runbook.md) instead.

## Start here

- [Getting started](getting-started.md) — what the system does, and a tour of the dashboard.
- [Troubleshooting the dashboard](troubleshooting.md) — symptom-to-fix table for what you see in the
  browser.

## How-to (user guide)

| Page | Read it when |
|------|--------------|
| [HT-01 — Run a fault drill](how-to/HT-01-run-a-fault-drill.md) | You want to see the full loop end to end |
| [HT-02 — Approve or reject a remediation](how-to/HT-02-approve-a-remediation.md) | An incident is awaiting approval |
| [HT-03 — Review incidents and postmortems](how-to/HT-03-review-incidents.md) | You are investigating what happened |
| [HT-04 — Run the eval suite and read costs](how-to/HT-04-evals-and-costs.md) | You are measuring agent quality or spend |

## Operations (operator guide)

| Page | Read it when |
|------|--------------|
| [OP-01 — Install and first run](operations/OP-01-install.md) | Standing the system up from a clean checkout |
| [OP-02 — Configuration reference](operations/OP-02-configuration.md) | Changing models, database, CORS, or costs |
| [OP-03 — Routine operations](operations/OP-03-routine-operations.md) | Starting, stopping, and reseeding day to day |
| [OP-04 — Monitoring and health](operations/OP-04-monitoring.md) | Checking the system is alive and healthy |
| [OP-05 — Incident runbook](operations/OP-05-runbook.md) | Something is broken and you are on call |
| [OP-06 — Rollback and recovery](operations/OP-06-rollback-recovery.md) | You need to revert a model or reset state |

## Terminology

Used consistently across every page.

- **Window** — a 30-second rollup of prediction traffic (latency percentiles, mean confidence,
  prediction entropy, PSI, class distribution). The unit the agents reason about.
- **PSI** — Population Stability Index: how far the current predicted-class distribution has moved
  from the reference profile. Higher means more drift.
- **Injection** — a deliberately introduced fault (`feature_drift`, `latency`, `bad_deploy`,
  `label_skew`) used to exercise the system.
- **Incident** — an open investigation, created by the monitor agent from one window.
- **Hypothesis** — a diagnosis of an incident: a fault type, a confidence, and cited evidence.
- **Remediation** — the proposed action for an incident (`rollback`, `retrain_trigger`,
  `pipeline_fix`), with a risk level.
- **Postmortem** — the write-up generated when an incident resolves. Past postmortems are retrieved
  as advisory context for future diagnoses.
