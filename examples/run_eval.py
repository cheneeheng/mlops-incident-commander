#!/usr/bin/env python
"""Run the scored eval harness and print the scorecard.

The runner replays labeled fault scenarios through the *live* pipeline and scores each against
hidden ground truth (detection recall, diagnosis accuracy, mean time-to-detect, mean cost). It
drives the injections itself, so the full stack must be running (serving + traffic + control).

    uv run python examples/run_eval.py           # demo: single feature_drift case (~minutes)
    uv run python examples/run_eval.py --full     # full 13-case suite (slow, costs real tokens)

Each case waits up to 10 min for detection, so the full suite is a long, deliberate run.
"""

import os
import sys
import time

import httpx

BASE_URL = os.environ.get("ICC_BASE_URL", "http://localhost:8000")
_POLL_S = 10.0


def _fmt(value: float | None, suffix: str = "") -> str:
    return "n/a" if value is None else f"{value}{suffix}"


def main() -> None:
    demo = "--full" not in sys.argv[1:]
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        run = client.post("/api/eval/runs", params={"demo": demo}).raise_for_status().json()
        run_id = run["id"]
        suite = "demo (1 case)" if demo else "full suite (13 cases)"
        print(f"Started eval run {run_id} — {suite}. Polling until it finishes...\n")

        # No hard client-side deadline: the server bounds each case; we just wait it out.
        while True:
            run = client.get(f"/api/eval/runs/{run_id}").raise_for_status().json()
            done = len(run.get("cases", []))
            if run["finished_at"] is not None:
                break
            print(f"  ...running ({done} case(s) scored so far)", flush=True)
            time.sleep(_POLL_S)

        print("\n== Scorecard ==")
        print(f"  detection recall   : {_fmt(run['detection_recall'])}")
        print(f"  diagnosis accuracy : {_fmt(run['diagnosis_accuracy'])}")
        print(f"  mean time-to-detect: {_fmt(run['mean_ttd_s'], 's')}")
        print(f"  mean cost / case   : ${_fmt(run['mean_cost_usd'])}")

        print("\n  per case:")
        for case in run.get("cases", []):
            ttd = _fmt(case["ttd_seconds"], "s")
            print(
                f"    {case['scenario_name']:<22} fault={case['injected_fault']:<14} "
                f"detected={str(case['detected']):<5} correct={str(case['diagnosis_correct']):<5} "
                f"ttd={ttd}"
            )


if __name__ == "__main__":
    main()
