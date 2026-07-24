# 02 — Run a fault drill

Inject a labeled fault and watch the system detect, diagnose, and remediate it. This is the fastest
way to see the whole product work.

**When:** you want to demonstrate or exercise the loop end to end.
**Prerequisites:** the dashboard is open and the Dashboard page is drawing charts (if it is empty,
see [06 — Troubleshooting](06-user-troubleshooting.md)).
**Time / impact:** 2–10 minutes. The injection degrades the live model's behaviour on purpose; a
`bad_deploy` injection swaps the served model to the deliberately broken `v1.1-bad` checkpoint until
you stop it.

## Choose a fault

Four faults can be injected. Each has a different signature on the Dashboard charts.

| Fault | What it does | Expect to see |
|-------|--------------|---------------|
| `feature_drift` | Shifts image brightness and adds noise before sending | PSI rises, mean confidence falls |
| `latency` | Serving sleeps a fixed extra delay on every request | Latency p95 steps up |
| `bad_deploy` | Activates the `v1.1-bad` model version | Mean confidence falls sharply, entropy shifts |
| `label_skew` | Over-samples one class in the traffic mix | PSI rises, prediction entropy falls |

## Steps

1. Open **Inject** in the sidebar. You see a fault dropdown, an **Inject fault** button, an
   **Active injections** card, and a **Past injections** table.
2. Select the fault you want from the dropdown — for a first drill, choose `feature_drift`.
3. Click **Inject fault**. The fault appears under **Active injections** with its ground-truth label,
   and a **Stop** button beside it.
4. Switch to **Dashboard** and wait for the next window. Windows close every 30 seconds, so the first
   affected point appears within about a minute. The relevant chart moves in the direction listed in
   the table above.
5. Watch the event feed for `incident_opened`. Detection is a judgement call made by the monitor
   agent, not a fixed threshold, so a mild fault may take several windows — or may legitimately not
   open an incident at all.
6. Open **Incidents** and click the newest row. The **Incident detail** page fills in with the
   hypothesis once diagnosis completes (event `hypothesis_ready`), showing the diagnosed fault type,
   a confidence percentage, and the evidence the agent cited from its tools.
7. Check **Approvals**. If the remediation was low risk and the diagnosis was confident, it already
   auto-executed and nothing is listed — go to step 8. Otherwise a card is waiting; approve or
   reject it following [03 — Approve or reject a remediation](03-user-approve-a-remediation.md).
8. Return to **Inject** and click **Stop** on the active injection. The row moves to **Past
   injections** with an end time. Stopping a `bad_deploy` injection also restores the good model.
9. Open **Postmortems**. A write-up for the resolved incident appears (event `postmortem_ready`).

**Verify:** the injection shows an end time under **Past injections**, the incident's **Status** on
the **Incidents** page reads `resolved`, and a postmortem exists for it.

**If it fails:**
- *No incident after several windows* — the fault may be too mild to be worth an incident. Stop the
  injection and try a stronger fault such as `bad_deploy`, which produces an unmistakable signal.
- *Charts are not moving at all* — the traffic generator or aggregator is not running; hand over to
  [11 — Incident runbook](11-ops-runbook.md).

## Injection parameters

The **Inject fault** button sends an injection with default parameters. The magnitudes used by the
scored scenario suite — for example `brightness` and `noise` for drift, `added_latency_ms` for
latency, `class` and `fraction` for label skew — are exercised by the eval suite instead; see
[05 — Run the eval suite](05-user-evals-and-costs.md).
