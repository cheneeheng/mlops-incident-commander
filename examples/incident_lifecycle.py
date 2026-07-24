#!/usr/bin/env python
"""End-to-end incident demo: inject a fault, then watch the agents detect, diagnose, remediate,
and write a postmortem — the full loop the README promises, driven entirely through the REST API.

Prerequisites: the full stack must be running and seeded (see examples/README.md):
    make db && make migrate && make seed
    make serving   # :8001 + traffic generator
    make control   # :8000 + aggregator + agent graph  (needs ANTHROPIC_API_KEY)

Run:
    uv run python examples/incident_lifecycle.py                 # feature_drift (default)
    uv run python examples/incident_lifecycle.py bad_deploy      # auto-remediated path
    uv run python examples/incident_lifecycle.py latency|label_skew

The agents call Anthropic, so this costs a few cents and takes a couple of minutes: the aggregator
rolls a metric window every 30s, and diagnosis makes several tool calls.
"""

import os
import sys
import time

import httpx

BASE_URL = os.environ.get("ICC_BASE_URL", "http://localhost:8000")

# Fault magnitudes mirror backend/app/eval/scenarios.py (params that reliably trip the monitor).
FAULTS: dict[str, dict[str, float]] = {
    "feature_drift": {"brightness": 0.5, "noise": 0.15},
    "latency": {"added_latency_ms": 400},
    "label_skew": {"class": 3, "fraction": 0.8},
    "bad_deploy": {},
}

_DETECT_TIMEOUT_S = 240.0
_DIAGNOSE_TIMEOUT_S = 240.0
_RESOLVE_TIMEOUT_S = 180.0
_POLL_S = 5.0


def _max_incident_number(client: httpx.Client) -> int:
    incidents = client.get("/api/incidents").raise_for_status().json()
    return max((i["number"] for i in incidents), default=0)


def _wait_for_new_incident(client: httpx.Client, baseline: int) -> dict:
    """Poll until an incident with a higher (DB-sequence) number than the baseline appears."""
    deadline = time.monotonic() + _DETECT_TIMEOUT_S
    while time.monotonic() < deadline:
        incidents = client.get("/api/incidents").raise_for_status().json()
        new = sorted((i for i in incidents if i["number"] > baseline), key=lambda i: i["number"])
        if new:
            return new[0]
        print("  ...waiting for the monitor to open an incident", flush=True)
        time.sleep(_POLL_S)
    raise SystemExit(
        f"No incident opened within {_DETECT_TIMEOUT_S:.0f}s. Is the full stack running "
        "(serving + traffic + control) and ANTHROPIC_API_KEY set?"
    )


def _accepted_hypothesis(detail: dict) -> dict | None:
    """The adjudicated hypothesis if a second opinion ran, else the primary."""
    hypotheses = detail.get("hypotheses", [])
    by_kind = {h["kind"]: h for h in hypotheses}
    return by_kind.get("adjudication") or by_kind.get("primary")


def _wait_for(
    client: httpx.Client, incident_id: str, predicate, timeout_s: float, note: str
) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        detail = client.get(f"/api/incidents/{incident_id}").raise_for_status().json()
        if predicate(detail):
            return detail
        print(f"  ...{note}", flush=True)
        time.sleep(_POLL_S)
    raise SystemExit(f"Timed out after {timeout_s:.0f}s waiting for: {note}")


def main() -> None:
    fault = sys.argv[1] if len(sys.argv) > 1 else "feature_drift"
    if fault not in FAULTS:
        raise SystemExit(f"Unknown fault {fault!r}. Choose one of: {', '.join(FAULTS)}")

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        active = next(
            (d["model_version"] for d in client.get("/api/deploys").raise_for_status().json()
             if d["is_active"]),
            "unknown",
        )
        print(f"== MLOps Incident Commander demo — {fault} ==")
        print(f"Control plane: {BASE_URL}   Active model: {active}\n")

        baseline = _max_incident_number(client)
        injection = client.post(
            "/api/injections", json={"fault_type": fault, "params": FAULTS[fault]}
        ).raise_for_status().json()
        print(f"[1] Injected {fault} (injection {injection['id']}, params {FAULTS[fault]}).")
        print("    Ground truth is hidden from the agents — they must infer it from metrics.\n")

        incident = _wait_for_new_incident(client, baseline)
        incident_id = incident["id"]
        trig = incident["trigger_metrics"]
        print(f"[2] Incident #{incident['number']} OPEN — severity {incident['severity']}.")
        print(
            f"    Trigger window: p95={trig.get('latency_p95'):.0f}ms  "
            f"PSI={trig.get('psi_score'):.3f}  mean_conf={trig.get('mean_confidence'):.3f}\n"
        )

        # Stop the injection now so the drift doesn't keep opening fresh incidents behind us.
        client.post(f"/api/injections/{injection['id']}/stop").raise_for_status()

        detail = _wait_for(
            client, incident_id, lambda d: _accepted_hypothesis(d) is not None,
            _DIAGNOSE_TIMEOUT_S, "diagnosis investigating via MCP tools",
        )
        hyp = _accepted_hypothesis(detail)
        assert hyp is not None
        kinds = {h["kind"] for h in detail["hypotheses"]}
        adjudicated = "adjudication" in kinds
        verdict = "CORRECT" if hyp["fault_type"] == fault else "MISDIAGNOSED"
        print(
            f"[3] Diagnosis: {hyp['fault_type']} (confidence {hyp['confidence']:.2f}) "
            f"vs ground truth {fault} -> {verdict}."
        )
        if adjudicated:
            print("    Low-confidence primary triggered a second opinion + adjudicator.")
        for e in hyp["evidence"]:
            cite = e.get("finding") or e.get("reasoning") or ""
            print(f"    - [{e.get('tool', 'reasoning')}] {cite}")
        print()

        detail = _wait_for(
            client, incident_id, lambda d: d.get("remediations"),
            _DIAGNOSE_TIMEOUT_S, "remediation agent proposing an action",
        )
        rem = detail["remediations"][-1]
        print(
            f"[4] Remediation proposed: {rem['action_type']} "
            f"(risk {rem['risk']}, {rem['status']})."
        )
        if rem["status"] == "pending":
            print("    Risk-gated: awaiting human approval. Approving now...")
            client.post(f"/api/remediations/{rem['id']}/approve").raise_for_status()
        else:
            print("    Low risk + high confidence -> auto-executed, no human in the loop.\n")

        _wait_for(
            client, incident_id, lambda d: d["status"] == "resolved",
            _RESOLVE_TIMEOUT_S, "remediation executing",
        )
        print("[5] Incident RESOLVED.\n")

        posts = client.get("/api/postmortems").raise_for_status().json()
        post = next((p for p in posts if p["incident_id"] == incident_id), None)
        if post is None:
            print("    (Postmortem not found — generation may still be in flight.)")
            return
        print("[6] Postmortem written (embedded into pgvector memory for future diagnoses):")
        print("-" * 72)
        print(post["body_md"].strip())
        print("-" * 72)


if __name__ == "__main__":
    main()
