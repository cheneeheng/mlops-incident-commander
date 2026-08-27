# OP-06 — Rollback and recovery

[← Guide index](../index.md)

Procedures for getting back to a known-good state. Read the blast radius on each before running it.

## Roll the model back to the known-good version

**When:** the served model is misbehaving, a `bad_deploy` injection was left running, or a
remediation went wrong.
**Impact:** serving reloads weights within about 5 seconds. In-flight requests are unaffected.

1. Activate the good version.

   ```bash
   curl -X POST http://localhost:8000/api/deploys/activate \
     -H 'Content-Type: application/json' \
     -d '{"model_version":"v1.0-good"}'
   ```

2. Wait 5 seconds for the serving poller.

**Verify:**

```bash
curl http://localhost:8001/healthz
```

Expected output:

```
{"status":"ok","model_version":"v1.0-good"}
```

**If it fails:** the poller may be stuck — restart serving, which loads the active deploy directly at
startup. See [OP-05 — Incident runbook](OP-05-runbook.md).

## Stop all active injections

**When:** faults were left running, or the system needs to return to baseline.
**Impact:** stopping a `bad_deploy` injection also reactivates `v1.0-good`.

1. List injections and identify the ones with `"ended_at": null`.

   ```bash
   curl http://localhost:8000/api/injections
   ```

2. Stop each one by id.

   ```bash
   curl -X POST http://localhost:8000/api/injections/inj_<id>/stop
   ```

   The dashboard equivalent is the **Stop** button on the **Inject** page.

**Verify:** every injection in the list has a non-null `ended_at`, and within a minute or two the
Dashboard charts return to baseline (PSI near 0, latency p95 back down).

## Recover from a corrupt or unwanted database state

> **Warning:** this destroys every incident, hypothesis, remediation, postmortem, eval run, and
> prediction record. There is no backup configured for the `pgdata` volume — once dropped, the
> history is gone. Export anything you need first.

**When:** the schema or data is beyond repair and history is expendable.
**Impact:** total data loss; roughly five minutes of downtime.

1. Stop the control plane and serving (`Ctrl+C` in both shells).
2. Export anything worth keeping, for example the postmortems:

   ```bash
   curl http://localhost:8000/api/postmortems > postmortems-backup.json
   ```

   This must happen **before** step 3, so run it while the control plane is still up if you skipped
   ahead.
3. Destroy the database and its volume.

   ```bash
   docker compose down -v
   ```

4. Recreate it, migrate, and reseed.

   ```bash
   make db
   make migrate
   make seed
   ```

5. Restart serving, the control plane, and the dashboard ([OP-03 — Routine
   operations](OP-03-routine-operations.md)).

**Verify:** `curl http://localhost:8001/healthz` reports `v1.0-good`, and a new
`metric_window_written` line appears within a minute.

## Back up the database

No backup runs on a schedule. To take one manually:

```bash
docker compose exec db pg_dump -U icc icc > icc-backup.sql
```

Restore into a freshly migrated, empty database:

```bash
docker compose exec -T db psql -U icc icc < icc-backup.sql
```

Take a dump before any destructive operation you might regret.

## Recover a stuck remediation

Remediations are deliberately one-way: once `executed` or `auto_executed` they cannot be re-approved,
and a `rejected` remediation stays rejected. There is no undo endpoint.

- **A rollback executed that you did not want** — activate the version you meant to run, using the
  first procedure on this page.
- **A remediation is stuck `pending` and no longer relevant** — reject it from the **Approvals**
  page. Rejecting the same remediation twice is idempotent and safe. It clears the approval queue
  but leaves the incident in `awaiting_approval` forever: nothing re-diagnoses it, and the rejected
  remediation can never be approved. There is no supported way to resolve such an incident through
  the API.
- **An incident is resolved but the underlying fault is still active** — remediating does not stop an
  injection. Stop the injection separately, using the second procedure on this page.

---

[← OP-05 Incident runbook](OP-05-runbook.md) · [Guide index](../index.md)
