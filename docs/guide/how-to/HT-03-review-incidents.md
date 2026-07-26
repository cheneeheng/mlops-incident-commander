# HT-03 — Review incidents and postmortems

**When:** you are investigating what the system saw, decided, and did.
**Prerequisites:** dashboard access.

## Find an incident

1. Open **Incidents**. The table lists every incident with **#**, **Status**, **Severity**,
   **Opened**, and **Closed**.
2. Click a row to open **Incident detail**.

**Verify:** the detail page header reads `Incident #<number>` with its status and severity.

## Read an incident

The detail page assembles everything recorded against the incident:

- **Trigger metrics** — the exact window that caused the monitor to open the incident. This is the
  evidence for *why* it opened at all.
- **Hypotheses** — one or more diagnoses, each with a fault type, a confidence, the evidence cited
  from the read-only tool servers, and a kind:
  - `primary` — the first diagnosis.
  - `second_opinion` — an independent re-diagnosis, run only when the primary confidence was below
    0.6.
  - `adjudication` — the reconciliation of the two. When present, this is the diagnosis that drove
    the remediation.
- **Remediations** — the proposed action, its risk, its status, and when it executed.
- **Agent runs** — every model call made for this incident, with tokens, cost, and latency.

Read them in that order: trigger → hypothesis → remediation. If a `second_opinion` and an
`adjudication` exist, the adjudicated fault type is the one the system acted on, not the primary.

## Read a postmortem

1. Open **Postmortems**. Each resolved incident has one entry.
2. Select the postmortem for your incident to read the generated write-up.

Postmortems are not only for humans: each one is embedded and stored, and the diagnosis agent
retrieves the three most similar past postmortems as advisory context when investigating future
incidents. Retrieval is best-effort — a diagnosis is never blocked by it.

**If a resolved incident has no postmortem:** generation is non-fatal by design, so an execution can
succeed while its postmortem fails. The remediation and resolution still stand. Report it to your
operator ([OP-05 — Incident runbook](../operations/OP-05-runbook.md) covers finding the failure in the logs).

## A note on ground truth

The **Inject** page shows each injection's ground-truth fault, because you are running the drill.
The diagnosis agent never sees it — it cannot read whether a deploy is flagged faulty and must infer
the fault from metrics alone. That is what makes a matching diagnosis meaningful.
