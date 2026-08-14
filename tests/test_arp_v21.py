from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_reliability_protocol import (
    CapturePolicy,
    EvidenceReference,
    EvidenceStage,
    GateDecision,
    GateRequest,
    LifecycleEvent,
    RunManifest,
    assert_neutral_contract,
    check_contract,
)


def test_evidence_reference_round_trips_neutral_scalar_claims_and_artifact_provenance() -> None:
    evidence = EvidenceReference(
        "e-1",
        event_id="event-1",
        artifact_uri="artifacts/verification.json",
        artifact_hash="sha256:artifact",
        subject_ref="attempt-1",
        claim="artifact_matches_expected_revision",
        observed=True,
        expected=True,
        comparator="equals",
        stage=EvidenceStage.FINAL_ARTIFACT,
        capture_policy=CapturePolicy.METADATA,
    )

    assert EvidenceReference.from_dict(evidence.to_dict()) == evidence
    assert check_contract("evidence", evidence.to_dict()) == []


def test_evidence_reference_rejects_non_scalar_generic_observations() -> None:
    with pytest.raises(ValueError, match="scalar"):
        EvidenceReference("e-1", observed={"sha": "abc123"})


def test_gate_request_round_trips_pending_gate_identity_and_required_evidence() -> None:
    request = GateRequest(
        gate_id="gate-1",
        run_id="run-1",
        checkpoint="release.gate",
        policy_version="policy/1.0.0",
        requested_at="2026-08-14T00:00:00+00:00",
        required_evidence=("e-1", "e-2"),
    )

    assert GateRequest.from_dict(request.to_dict()) == request
    assert check_contract("gate-request", request.to_dict()) == []


def test_gate_decision_round_trips_authority_and_decision_provenance() -> None:
    decision = GateDecision(
        decision="approve",
        checkpoint="gate.decided",
        reasons=(),
        evidence=(),
        threshold_version="legacy",
        gate_id="gate-1",
        decided_at="2026-08-14T00:01:00+00:00",
        decision_authority="human",
        policy_version="policy/1.0.0",
        capture_policy=CapturePolicy.REDACTED,
        extensions={"consumer/v1": {"review_ref": "opaque"}},
    )

    assert GateDecision.from_dict(decision.to_dict()) == decision


def test_run_manifest_and_lifecycle_event_carry_profile_policy_and_extensions() -> None:
    manifest = RunManifest(
        schema_version="2.1.0",
        experiment_id="project-1",
        run_id="run-1",
        created_at="2026-08-14T00:00:00+00:00",
        git_sha="abc123",
        harness_name="runner",
        harness_version="1.0.0",
        dataset_id="input-1",
        dataset_hash="sha256:input",
        configuration_hash="sha256:config",
        model_provider="provider",
        model_name="model",
        model_version="version",
        random_seed=0,
        replication_count=1,
        environment={},
        profile="software-delivery/v1",
        capture_policy=CapturePolicy.NONE,
        extensions={"software-delivery/v1": {"work_item_id": "PAY-104"}},
    )
    event = LifecycleEvent(
        event_id="event-1",
        schema_version="2.1.0",
        experiment_id="project-1",
        run_id="run-1",
        episode_id="episode-1",
        replication_id=0,
        sequence_number=1,
        checkpoint="gate.decided",
        event_type="gate.decided",
        started_at="2026-08-14T00:00:00+00:00",
        ended_at="2026-08-14T00:00:01+00:00",
        extensions={"software-delivery/v1": {"base_sha": "abc123"}},
    )

    assert RunManifest.from_dict(manifest.to_dict()) == manifest
    assert LifecycleEvent.from_dict(event.to_dict()) == event


def test_neutral_guard_allows_domain_payloads_only_inside_namespaced_extensions() -> None:
    assert_neutral_contract({"extensions": {"rag-reliability/v1": {"mrr": 0.9}}})

    with pytest.raises(ValueError, match="domain-specific"):
        assert_neutral_contract({"mrr": 0.9})

    with pytest.raises(ValueError, match="namespace"):
        assert_neutral_contract({"extensions": {"": {"mrr": 0.9}}})


def test_evidence_and_gate_request_schemas_match_the_new_contract_requirements() -> None:
    schema_root = Path(__file__).resolve().parents[1] / "src" / "agent_reliability_protocol" / "schemas"
    evidence_schema = json.loads((schema_root / "evidence-reference.schema.json").read_text(encoding="utf-8"))
    gate_request_schema = json.loads((schema_root / "gate-request.schema.json").read_text(encoding="utf-8"))

    assert evidence_schema["required"] == ["evidence_id", "stage"]
    assert gate_request_schema["required"] == [
        "gate_id",
        "run_id",
        "checkpoint",
        "policy_version",
        "requested_at",
        "required_evidence",
    ]
