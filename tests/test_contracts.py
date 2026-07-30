from __future__ import annotations

import json

import pytest

from agent_reliability_protocol import DecisionReason, Evidence, GateDecision, LifecycleEvent, RunManifest


def test_manifest_decision_and_event_round_trip() -> None:
    decision = GateDecision.failed(
        DecisionReason("threshold_not_met", "Quality is below threshold", (Evidence("measurement", "quality", 0.7, 0.9, ">="),))
    )
    manifest = RunManifest(
        run_id="run-123",
        started_at="2026-07-30T00:00:00+00:00",
        decision=decision,
        identifiers={"build": "build-123"},
        hashes={"input": "abc"},
    )
    event = LifecycleEvent("gate.decided", "run-123", "2026-07-30T00:00:01+00:00", {"outcome": "fail"})

    assert GateDecision.from_dict(json.loads(json.dumps(decision.to_dict()))) == decision
    assert RunManifest.from_dict(json.loads(json.dumps(manifest.to_dict()))).to_dict() == manifest.to_dict()
    assert LifecycleEvent.from_dict(json.loads(json.dumps(event.to_dict()))) == event


@pytest.mark.parametrize(
    ("outcome", "reasons"),
    [("fail", ()), ("pass", (DecisionReason("code", "message"),)), ("unknown", ())],
)
def test_decision_rejects_invalid_states(outcome: str, reasons: tuple[DecisionReason, ...]) -> None:
    with pytest.raises(ValueError):
        GateDecision(outcome=outcome, reasons=reasons)  # type: ignore[arg-type]
