# OP-03 — Routine operations

Day-to-day procedures. Install is in [07](OP-01-install.md); failures are in [11](OP-05-runbook.md).

## Start the system

**Prerequisites:** dependencies installed, `.env` present, migrations applied.

1. Start the database and confirm it is healthy.

   ```bash
   make db
   docker compose ps
   ```

2. Start serving in its own shell.

   ```bash
   make serving
   ```

3. Start the control plane in a second shell.

   ```bash
   make control
   ```

4. Start the dashboard in a third shell.

   ```bash
   make frontend
   ```

**Verify:** `curl http://localhost:8000/health` returns `{"status":"ok"}` and the control plane logs
a `metric_window_written` line within a minute of serving starting.

## Stop the system

1. Press `Ctrl+C` in each application shell. Both processes cancel their background tasks on
   shutdown — the control plane logs `control_plane_stopping`, serving logs `serving_stopping`.
2. Stop the database only if you also want traffic to stop being recorded:

   ```bash
   docker compose stop db
   ```

Use `docker compose stop`, not `down -v`: `-v` destroys the `pgdata` volume and every incident,
postmortem, and eval run in it.

## Restart one process

Both application processes run under `--reload`, so editing source restarts them automatically. For
a configuration change, restart by hand — settings are cached for the life of the process and `.env`
edits are not picked up by a reload alone.

`make serving` and `make control` are independent; restarting one does not require restarting the
other. A serving restart briefly pauses traffic, so expect one thin or empty metric window.

## Apply a database migration

**Time / impact:** brief. Stop the writers first so a schema change does not race live inserts.

1. Stop the control plane and serving processes (`Ctrl+C` in both shells).
2. Apply pending migrations.

   ```bash
   make migrate
   ```

3. Restart both processes.

**Verify:** `uv run alembic current` reports the expected head revision.

## Reseed deploys and the reference profile

**When:** after wiping the database, or if the deploy rows or reference profile are missing.
**Impact:** none on existing data — both seed steps are idempotent and skip rows that already exist.

```bash
make seed          # weights + DB rows
make seed-weights  # weights only
make seed-db       # DB rows only
```

**Verify:** the output lists `v1.0-good`, `v1.1-bad`, and `reference_profile v1.0-good`, each with
either `+` (created) or `=` (already present).

## Switch the active model version

The active deploy determines which checkpoint serving loads. The serving poller picks up a change
within about 5 seconds and logs `weights_reloaded`.

```bash
curl -X POST http://localhost:8000/api/deploys/activate \
  -H 'Content-Type: application/json' \
  -d '{"model_version":"v1.0-good"}'
```

A 404 with `{"detail":"model_version not found"}` means that version has not been seeded.

**Verify:** `curl http://localhost:8001/healthz` reports the new `model_version`.

## Run the eval suite from the shell

The dashboard button is the normal path ([05](../how-to/HT-04-evals-and-costs.md)); this is the scriptable
equivalent. The run happens in the background and returns immediately.

```bash
curl -X POST 'http://localhost:8000/api/eval/runs'          # full 13-case suite
curl -X POST 'http://localhost:8000/api/eval/runs?demo=1'   # single drift scenario
curl http://localhost:8000/api/eval/runs                    # list runs and scores
```

> **Warning:** a suite run drives real injections against the live model, including `bad_deploy`.
> Do not start one while the system is being demonstrated or measured for anything else. It also
> ends any injections currently active and resets the active deploy to `v1.0-good` before starting.

## Code quality checks

```bash
make lint                          # ruff check .
make typecheck                     # mypy backend serving mcp_servers (strict)
cd frontend && npm run typecheck   # tsc -b --noEmit
```
