# 03 — Approve or reject a remediation

**When:** an incident reaches `awaiting_approval`, or a `remediation_queued` event appears in the
feed.
**Prerequisites:** dashboard access. No shell access needed.
**Time / impact:** seconds to decide. **Approving executes the action immediately** — a `rollback`
really does swap the served model back to the known-good version.

## What you are deciding

The action and its risk level are not chosen by the agent — they come from a fixed policy table.
The agent supplies only a rationale, which is recorded.

| Diagnosed fault | Action | Risk |
|-----------------|--------|------|
| `bad_deploy` | `rollback` | low |
| `feature_drift` | `retrain_trigger` | medium |
| `label_skew` | `pipeline_fix` | medium |
| `latency` | `pipeline_fix` | medium |
| `unknown` | `pipeline_fix` | high |

A remediation runs automatically only when its risk is **low** *and* the diagnosis confidence is at
least **0.85**. A low-risk action diagnosed with confidence below 0.5 is bumped to medium risk, so
a shaky diagnosis can never auto-execute. Everything that does not clear that bar lands on
**Approvals** and waits for you.

## Steps

1. Open **Approvals** in the sidebar. Each card shows the action type, a risk badge (`low risk`,
   `medium risk`, `high risk`), a link to the incident, and the diagnosis line —
   for example `Diagnosis: feature_drift (72% confidence)`.
2. Click the **incident** link on the card to read the full evidence before deciding. The incident
   detail page lists every hypothesis and the tool findings cited for it. Use the browser back
   button to return.
3. Decide:
   - Click **Approve** to execute the action now.
   - Click **Reject** to decline it. Nothing is executed.

   Both buttons disable while the request is in flight.

**Verify:** the card disappears from **Approvals**. On approval, the incident's **Status** on the
**Incidents** page becomes `resolved` with a **Closed** timestamp, and a postmortem appears under
**Postmortems** shortly after. On rejection, the remediation is marked rejected and the incident is
not resolved.

**If it fails:**
- *The card reappears or an error is shown* — the remediation may already have been acted on in
  another browser tab. Reload the page; an already-executed or already-rejected remediation cannot
  be approved again.
- *Approval seems to hang for a few seconds* — expected. The postmortem is generated as part of
  execution, so the request waits for it.

## What each action actually does

- **`rollback`** — a real deploy swap back to the known-good model version. The serving process
  notices within about 5 seconds and reloads the weights.
- **`retrain_trigger`** and **`pipeline_fix`** — recorded state transitions that complete
  immediately. They are simulated: no retraining job or pipeline change is launched.

In all three cases the incident is resolved and a postmortem is generated.
