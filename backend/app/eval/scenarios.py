"""Labeled scenario suite for the eval harness: 3 cases per fault type at varied severities plus one
no-fault control (13 total). Bumping SUITE_VERSION marks scorecards as comparable within a version —
tune prompts against the scorecard, not single anecdotes."""

from dataclasses import dataclass, field

from backend.app.domain.enums import FaultType

SUITE_VERSION = "v1"

_NO_FAULT = "none"


@dataclass(frozen=True)
class Scenario:
    name: str
    fault_type: FaultType | None  # None = no-fault control (false-positive check)
    params: dict[str, float] = field(default_factory=dict)

    @property
    def ground_truth(self) -> str:
        return self.fault_type.value if self.fault_type is not None else _NO_FAULT


# 3 severities per fault type; bad_deploy has no magnitude, so its three cases are repeats.
_SEVERITY_PARAMS: dict[FaultType, list[dict[str, float]]] = {
    FaultType.FEATURE_DRIFT: [
        {"brightness": 0.2, "noise": 0.05},
        {"brightness": 0.4, "noise": 0.1},
        {"brightness": 0.6, "noise": 0.2},
    ],
    FaultType.LATENCY: [
        {"added_latency_ms": 150},
        {"added_latency_ms": 400},
        {"added_latency_ms": 800},
    ],
    FaultType.LABEL_SKEW: [
        {"class": 3, "fraction": 0.6},
        {"class": 3, "fraction": 0.8},
        {"class": 7, "fraction": 0.9},
    ],
    FaultType.BAD_DEPLOY: [{}, {}, {}],
}


def build_suite() -> list[Scenario]:
    scenarios: list[Scenario] = []
    for fault_type, param_sets in _SEVERITY_PARAMS.items():
        for level, params in enumerate(param_sets):
            scenarios.append(Scenario(f"{fault_type.value}_{level}", fault_type, params))
    scenarios.append(Scenario("no_fault_control", None, {}))
    return scenarios


def demo_suite() -> list[Scenario]:
    """?demo=1: a single drift narrative — inject drift, watch the full loop."""
    return [Scenario("demo_feature_drift", FaultType.FEATURE_DRIFT, {"brightness": 0.5, "noise": 0.15})]
