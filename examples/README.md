# Runnable examples

Three scripts that drive the running system through its REST + SSE API to show what it does. They
add no dependencies — just `httpx` (already required) and the standard library.

## Bring the stack up first

```bash
make db && make migrate && make seed   # Postgres, schema, CNN weights + baseline rows
make serving                           # :8001 — classifier + synthetic traffic (own shell)
make control                           # :8000 — aggregator + agent graph (own shell, needs ANTHROPIC_API_KEY)
```

All three examples target `http://localhost:8000`; override with `ICC_BASE_URL`.

## The examples

| Script | What it demonstrates |
|--------|----------------------|
| `incident_lifecycle.py` | The full loop: inject a fault → monitor opens an incident → diagnosis cites evidence from MCP tools → risk-gated remediation → approve → postmortem. |
| `watch_events.py` | Tails the live SSE event stream (the dashboard's feed) — run it alongside the lifecycle demo. |
| `run_eval.py` | Runs the scored eval harness over the labeled scenario suite and prints the scorecard. |

```bash
uv run python examples/incident_lifecycle.py              # feature_drift (default)
uv run python examples/incident_lifecycle.py bad_deploy   # auto-remediated (low-risk rollback) path
uv run python examples/incident_lifecycle.py latency      # or: label_skew

uv run python examples/watch_events.py                    # in a separate shell

uv run python examples/run_eval.py                        # demo: one case, ~minutes
uv run python examples/run_eval.py --full                 # full 13-case suite (slow, costs tokens)
```

The agents call Anthropic, so runs take a couple of minutes (the aggregator windows every 30s and
diagnosis makes several tool calls) and cost a few cents. `feature_drift`, `latency`, and
`label_skew` are MEDIUM-risk and pause for approval; `bad_deploy` is a LOW-risk rollback that
auto-executes when confidence is high.
