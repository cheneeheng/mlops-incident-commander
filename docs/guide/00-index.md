# MLOps Incident Commander — Guide

The Incident Commander watches a live image-classification service. A traffic generator sends a
steady stream of CIFAR-10 images to the model; a metrics aggregator rolls those predictions into
30-second windows; a set of agents triages each window, opens an incident when something looks
wrong, diagnoses the root cause, and proposes a remediation that either auto-executes or waits for
your approval.

Read the files in numeric order. Files `01`–`06` are the **user guide** (using the dashboard).
Files `07`–`12` are the **operator guide** (installing, running, and recovering the system). The two
are kept separate on purpose — nothing in `01`–`06` requires shell access.

## User guide

| # | Page | Read it when |
|---|------|--------------|
| 01 | [What the system does and the dashboard tour](01-user-overview.md) | You are new to the dashboard |
| 02 | [Run a fault drill](02-user-run-a-fault-drill.md) | You want to see the full loop end to end |
| 03 | [Approve or reject a remediation](03-user-approve-a-remediation.md) | An incident is awaiting approval |
| 04 | [Review incidents and postmortems](04-user-review-incidents.md) | You are investigating what happened |
| 05 | [Run the eval suite and read costs](05-user-evals-and-costs.md) | You are measuring agent quality or spend |
| 06 | [Troubleshooting (dashboard)](06-user-troubleshooting.md) | The UI is empty, stale, or erroring |

## Operator guide

| # | Page | Read it when |
|---|------|--------------|
| 07 | [Install and first run](07-ops-install.md) | Standing the system up from a clean checkout |
| 08 | [Configuration reference](08-ops-configuration.md) | Changing models, database, CORS, or costs |
| 09 | [Routine operations](09-ops-routine-operations.md) | Starting, stopping, and reseeding day to day |
| 10 | [Monitoring and health](10-ops-monitoring.md) | Checking the system is alive and healthy |
| 11 | [Incident runbook](11-ops-runbook.md) | Something is broken and you are on call |
| 12 | [Rollback and recovery](12-ops-rollback-recovery.md) | You need to revert a model or reset state |

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
