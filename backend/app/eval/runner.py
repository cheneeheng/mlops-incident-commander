"""Eval runner: replays the labeled scenario suite through the live pipeline and scores each case
against ground truth. Runs as a background task spawned by POST /api/eval/runs.

Assumes the full system is running (serving + traffic + aggregator + agent graph): the runner only
drives injections and reads the resulting incidents/hypotheses/agent_runs to score.
"""

import asyncio
import time
from datetime import UTC, datetime

from backend.app.db.models import EvalCase, Hypothesis, Incident
from backend.app.db.queries import (
    get_active_injections,
    get_agent_runs_for_incident,
    get_eval_cases_for_run,
    get_eval_run,
    get_first_incident_after,
    get_hypotheses_for_incident,
    insert_eval_case,
    set_active_deploy,
)
from backend.app.db.session import SessionLocal
from backend.app.domain.enums import HypothesisKind
from backend.app.eval.scenarios import Scenario, build_suite, demo_suite
from backend.app.observability import log
from backend.app.schemas import InjectionCreate
from backend.app.services import injection_service

_GOOD_VERSION = "v1.0-good"
_CASE_TIMEOUT_S = 600.0  # await detection up to 10 min
_HYPOTHESIS_TIMEOUT_S = 300.0  # await the accepted hypothesis up to 5 min
_POLL_INTERVAL_S = 10.0


async def _reset_transient_state() -> None:
    async with SessionLocal() as db:
        for injection in await get_active_injections(db):
            injection.ended_at = datetime.now(UTC)
        await set_active_deploy(db, _GOOD_VERSION)
        await db.commit()


async def _await_incident(after: datetime) -> Incident | None:
    deadline = time.monotonic() + _CASE_TIMEOUT_S
    while time.monotonic() < deadline:
        async with SessionLocal() as db:
            incident = await get_first_incident_after(db, after)
        if incident is not None:
            return incident
        await asyncio.sleep(_POLL_INTERVAL_S)
    return None


def _accepted(hypotheses: list[Hypothesis]) -> Hypothesis | None:
    adjudication = next((h for h in hypotheses if h.kind == HypothesisKind.ADJUDICATION), None)
    if adjudication is not None:
        return adjudication
    return next((h for h in hypotheses if h.kind == HypothesisKind.PRIMARY), None)


async def _await_accepted_hypothesis(incident_id: str) -> Hypothesis | None:
    deadline = time.monotonic() + _HYPOTHESIS_TIMEOUT_S
    while time.monotonic() < deadline:
        async with SessionLocal() as db:
            hypotheses = await get_hypotheses_for_incident(db, incident_id)
        accepted = _accepted(hypotheses)
        if accepted is not None:
            return accepted
        await asyncio.sleep(_POLL_INTERVAL_S)
    return None


async def _incident_cost(incident_id: str) -> float:
    async with SessionLocal() as db:
        runs = await get_agent_runs_for_incident(db, incident_id)
    return sum(run.cost_usd for run in runs)


async def _run_case(eval_run_id: str, scenario: Scenario) -> None:
    t0 = datetime.now(UTC)
    injection_id: str | None = None
    if scenario.fault_type is not None:
        async with SessionLocal() as db:
            injection = await injection_service.create_injection(
                db, InjectionCreate(fault_type=scenario.fault_type, params=scenario.params)
            )
            injection_id = injection.id

    incident = await _await_incident(t0)
    detected = incident is not None
    diagnosis_correct: bool | None = None
    ttd_seconds: float | None = None
    cost_usd: float | None = None

    if incident is not None:
        ttd_seconds = (incident.opened_at - t0).total_seconds()
        cost_usd = await _incident_cost(incident.id)
        accepted = await _await_accepted_hypothesis(incident.id)
        if scenario.fault_type is None:
            diagnosis_correct = False  # any incident on the control case is a false positive
        elif accepted is not None:
            diagnosis_correct = accepted.fault_type == scenario.fault_type

    if injection_id is not None:
        async with SessionLocal() as db:
            await injection_service.stop_injection(db, injection_id)

    async with SessionLocal() as db:
        await insert_eval_case(
            db,
            EvalCase(
                eval_run_id=eval_run_id,
                scenario_name=scenario.name,
                injected_fault=scenario.ground_truth,
                detected=detected,
                diagnosis_correct=diagnosis_correct,
                ttd_seconds=ttd_seconds,
                cost_usd=cost_usd,
            ),
        )
        await db.commit()
    log.info(
        "eval_case_scored",
        scenario=scenario.name,
        detected=detected,
        diagnosis_correct=diagnosis_correct,
        ttd_seconds=ttd_seconds,
        cost_usd=cost_usd,
    )


async def _finalize(eval_run_id: str) -> None:
    async with SessionLocal() as db:
        cases = await get_eval_cases_for_run(db, eval_run_id)
        run = await get_eval_run(db, eval_run_id)
        if run is None:
            return
        fault_cases = [c for c in cases if c.injected_fault != "none"]
        detected = [c for c in fault_cases if c.detected]
        correct = [c for c in detected if c.diagnosis_correct]
        ttds = [c.ttd_seconds for c in detected if c.ttd_seconds is not None]
        costs = [c.cost_usd for c in detected if c.cost_usd is not None]

        run.finished_at = datetime.now(UTC)
        run.detection_recall = len(detected) / len(fault_cases) if fault_cases else None
        run.diagnosis_accuracy = len(correct) / len(detected) if detected else None
        run.mean_ttd_s = sum(ttds) / len(ttds) if ttds else None
        run.mean_cost_usd = sum(costs) / len(costs) if costs else None
        await db.commit()
    log.info("eval_run_finalized", eval_run_id=eval_run_id)


async def run_suite(eval_run_id: str, demo: bool = False) -> None:
    scenarios = demo_suite() if demo else build_suite()
    log.info("eval_run_started", eval_run_id=eval_run_id, cases=len(scenarios), demo=demo)
    try:
        await _reset_transient_state()
        for scenario in scenarios:
            await _run_case(eval_run_id, scenario)
    except Exception as exc:  # always finalize, even on a mid-suite failure
        log.error("eval_run_error", eval_run_id=eval_run_id, error=repr(exc))
    finally:
        await _finalize(eval_run_id)
