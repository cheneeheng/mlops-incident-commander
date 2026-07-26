# TS — Troubleshooting (dashboard)

Symptoms you can see and act on from the browser. Anything that needs a shell is in
[OP-05 — Incident runbook](operations/OP-05-runbook.md); hand those items to your operator.

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| A **sample data** badge sits in the header | The dashboard is running against hardcoded sample data, not a live backend | Nothing on screen is real. Ask your operator to unset `VITE_USE_STUBS` — see [OP-02 — Configuration](operations/OP-02-configuration.md) |
| Dashboard charts are empty | No metric windows yet: the system was just started, or traffic is not flowing | Wait one minute for the first window. If still empty, escalate — the traffic generator or aggregator is likely down |
| Charts stop advancing and the event feed goes silent | The live event connection dropped, or the control plane stopped | Reload the page. If it stays silent, escalate |
| Pages show an error instead of data | The control plane is unreachable or returning errors | Reload. If it persists, escalate |
| **Inject fault** shows "Failed to inject." | The control plane rejected or did not receive the request | Reload and retry once. If it persists, escalate |
| An incident is stuck in `open` or `diagnosing` | Diagnosis failed or is still running | Give it a few minutes. If it never advances, escalate — the agent may be failing to reach the model API |
| A diagnosis came back as `unknown` with very low confidence | The agent failed to reach a conclusion and deliberately failed closed | Expected behaviour, not a bug. It produces a high-risk `pipeline_fix` that always requires your approval |
| **Approvals** is empty although an incident was opened | The remediation was low risk and confident, so it auto-executed | Check **Incidents**; the incident should be `resolved` |
| An approve or reject click errors | The remediation was already executed or rejected elsewhere | Reload the page. Terminal remediations cannot be changed |
| A resolved incident has no postmortem | Postmortem generation failed; it is deliberately non-fatal | The remediation still executed. Escalate so the failure can be found in the logs |
| An eval run shows `—` for every score | The run has not finished | Wait. A full suite is 13 cases with per-case timeouts of up to 15 minutes |

## Before escalating

Collect these — they make the operator's job much faster:

1. The incident number (from the **Incidents** table), if the problem concerns one.
2. The time you saw the problem.
3. What the event feed last showed on the **Dashboard**.
4. Whether the **sample data** badge is present in the header.
