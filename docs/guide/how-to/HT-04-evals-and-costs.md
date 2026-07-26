# HT-04 — Run the eval suite and read costs

## Run the eval suite

**When:** you want a scored, repeatable measure of how well the agents detect and diagnose faults —
for example after a prompt change.
**Prerequisites:** the whole system running (serving, traffic, aggregator, agent graph). The suite
replays through the **live** pipeline, not a simulation.
**Time / impact:** long. The suite is 13 cases, each allowed up to 10 minutes to be detected and a
further 5 minutes for a diagnosis, and each case drives a real injection against the live model.
Do not start a run while you need the system quiet.

1. Open **Evals**. You see a **Run eval suite** button and a table of past runs.
2. Click **Run eval suite**. The run is accepted immediately and executes in the background; the
   button re-enables and a new row appears in the table.
3. Wait. Refresh expectations accordingly — the run row shows `—` for its scores until it finishes.
4. Click the run's row to open **Run detail**, a per-case scorecard.

**Verify:** the run row shows non-empty **Recall**, **Diagnosis acc**, **Mean MTTD**, and
**Mean cost** values.

### What the suite contains

Suite `v1` is 13 labeled scenarios: three severities each of `feature_drift`, `latency`,
`label_skew`, and `bad_deploy`, plus one `no_fault_control` case that checks the system does *not*
open an incident when nothing is wrong.

### Reading the scorecard

| Column | Meaning |
|--------|---------|
| **Suite** | Suite version. Only compare runs within the same version. |
| **Recall** | Share of faulty scenarios where an incident was opened |
| **Diagnosis acc** | Share where the accepted hypothesis matched the injected fault |
| **Mean MTTD** | Mean seconds from injection to incident opening |
| **Mean cost** | Mean agent spend per case, in dollars |

Tune against the scorecard, not against a single anecdote. A prompt change that helps one incident
and hurts recall is a regression.

## Read agent costs

**When:** you want to know what the agents are spending.

1. Open **Costs**. The page shows the total spend and three breakdown tables — **by agent**,
   **by incident**, and **by day** — each with **Key**, **Runs**, and **Cost** columns.

Every model call is metered: input and output tokens, dollar cost, and latency. Costs are priced per
model, so the cheap monitor agent and the strong diagnosis agent are billed at different rates.

**How to read it:** the monitor runs on every window and so dominates the run count; the diagnosis
agent runs only on incidents but costs far more per run. A sudden jump in the by-day column usually
means either many incidents were opened or an eval suite was run.

Per-incident cost for a single incident is also visible on its **Incident detail** page under agent
runs.
