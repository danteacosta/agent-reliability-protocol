from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_reliability_protocol import CapturePolicy, EvidenceStage
from agent_reliability_protocol import check_contract, validate_run_directory
from agent_reliability_protocol.v3 import (
    EpisodeIdentity,
    EvidenceRecord,
    ExecutorIdentity,
    GateDecision,
    GateRequest,
    LifecycleEvent,
    RunManifest,
    SourceIdentity,
    adapt_decision_v2,
    adapt_event_v2,
    adapt_evidence_v2,
    adapt_gate_request_v2,
    adapt_manifest_v2,
    validate_lifecycle_sequence,
)


def test_v3_manifest_is_generic_and_round_trips() -> None:
    manifest = RunManifest(
        run_id="attempt-1",
        created_at="2026-08-14T00:00:00+00:00",
        source=SourceIdentity(revision="abc123", input_ref="graph", input_hash="sha256:graph"),
        executor=ExecutorIdentity(name="agent-runtime", version="1.0.0"),
        configuration_hash="sha256:config",
        environment={"runtime": "ci"},
        profile="software-delivery/v1",
        capture_policy=CapturePolicy.REDACTED,
        extensions={"software-delivery/v1": {"work_item_id": "PAY-104"}},
    )

    payload = manifest.to_dict()
    assert payload["schema_version"] == "3.0.0"
    assert "dataset_id" not in payload
    assert "model_name" not in payload
    assert RunManifest.from_dict(json.loads(json.dumps(payload))) == manifest


def test_v3_episode_identity_uses_only_generic_identity_fields() -> None:
    identity = EpisodeIdentity("run-1", "episode-1", ordinal=0, variant_ref="clean")

    assert EpisodeIdentity.from_dict(identity.to_dict()) == identity
    assert check_contract("episode", identity.to_dict()) == []


def test_v3_evidence_requires_a_claim_and_accepts_only_scalar_observations() -> None:
    evidence = EvidenceRecord(
        evidence_id="e-1",
        run_id="run-1",
        claim="artifact_matches_expected_revision",
        observed=True,
        expected=True,
        comparator="equals",
        stage=EvidenceStage.FINAL_ARTIFACT,
        artifact_uri="artifacts/verification.json",
        artifact_hash="sha256:artifact",
        capture_policy=CapturePolicy.METADATA,
    )

    assert EvidenceRecord.from_dict(evidence.to_dict()) == evidence
    with pytest.raises(ValueError, match="scalar"):
        EvidenceRecord("e-2", "run-1", "claim", observed={"sha": "abc"})


def test_v3_gate_request_and_decision_share_identity_and_policy() -> None:
    request = GateRequest(
        gate_id="gate-1",
        run_id="run-1",
        checkpoint="release.gate",
        requested_at="2026-08-14T00:00:00+00:00",
        policy_version="delivery/1.0.0",
        required_evidence=("e-1",),
        decision_authority="human",
        capture_policy=CapturePolicy.REDACTED,
    )
    decision = GateDecision(
        gate_id="gate-1",
        run_id="run-1",
        checkpoint="release.gate",
        decision="approve",
        decided_at="2026-08-14T00:01:00+00:00",
        policy_version="delivery/1.0.0",
        decision_authority="human",
        evidence_ids=("e-1",),
        capture_policy=CapturePolicy.REDACTED,
    )

    assert GateRequest.from_dict(request.to_dict()) == request
    assert GateDecision.from_dict(decision.to_dict()) == decision

    with pytest.raises(ValueError, match="reasons"):
        GateDecision(
            gate_id="gate-1", run_id="run-1", checkpoint="release.gate",
            decision="block", decided_at="now", policy_version="delivery/1.0.0",
            decision_authority="human",
        )


def test_v3_lifecycle_sequence_is_contiguous_and_generic() -> None:
    events = [
        LifecycleEvent("event-1", "run-1", "episode-1", 0, "episode.started", "now", "now"),
        LifecycleEvent("event-2", "run-1", "episode-1", 1, "gate.requested", "now", "later"),
        LifecycleEvent("event-3", "run-1", "episode-1", 2, "gate.decided", "later", "later"),
    ]

    validate_lifecycle_sequence(events)
    with pytest.raises(ValueError, match="contiguous"):
        validate_lifecycle_sequence(events[:1] + [LifecycleEvent("event-3", "run-1", "episode-1", 2, "gate.decided", "later", "later")])


def test_v2_adapters_emit_v3_and_preserve_legacy_identity_as_opaque_extension() -> None:
    legacy_manifest = {
        "schema_version": "2.0.5",
        "experiment_id": "project-1",
        "run_id": "run-1",
        "created_at": "now",
        "git_sha": "abc123",
        "harness_name": "runner",
        "harness_version": "1.0.0",
        "dataset_id": "graph",
        "dataset_hash": "sha256:graph",
        "configuration_hash": "sha256:config",
        "model_provider": "provider",
        "model_name": "model",
        "model_version": "version",
        "random_seed": 0,
        "replication_count": 1,
        "environment": {},
    }
    adapted = adapt_manifest_v2(legacy_manifest)
    assert adapted.schema_version == "3.0.0"
    assert adapted.source.revision == "abc123"
    assert "arp-compat/v2" in adapted.extensions
    assert "model_name" not in adapted.to_dict()

    legacy_event = {
        "event_id": "event-1", "schema_version": "2.0.5", "experiment_id": "project-1",
        "run_id": "run-1", "episode_id": "episode-1", "replication_id": 0,
        "sequence_number": 1, "checkpoint": "episode.started", "event_type": "episode.started",
        "started_at": "now", "ended_at": "now", "attributes": {},
        "content_reference": None, "parent_event_id": None,
    }
    adapted_event = adapt_event_v2(legacy_event)
    assert adapted_event.schema_version == "3.0.0"
    assert adapted_event.extensions["arp-compat/v2"]["experiment_id"] == "project-1"


def test_v2_decision_adapter_never_invents_evidence() -> None:
    legacy = {"decision": "approve", "checkpoint": "gate.decided", "reasons": [], "evidence": [], "threshold_version": "1"}

    adapted = adapt_decision_v2(legacy, run_id="run-1", gate_id="gate-1", decided_at="now", policy_version="delivery/1.0.0", decision_authority="human")

    assert adapted.decision == "approve"
    assert adapted.evidence_ids == ()
    assert adapted.run_id == "run-1"


def test_v2_evidence_and_gate_request_adapters_require_external_run_authority() -> None:
    evidence = adapt_evidence_v2(
        {"evidence_id": "e-1", "stage": "final_artifact", "metric_name": "legacy_claim", "observed_value": 1.0},
        run_id="run-1",
    )
    request = adapt_gate_request_v2(
        {"gate_id": "gate-1", "run_id": "run-1", "checkpoint": "release.gate", "policy_version": "1", "requested_at": "now", "required_evidence": []},
        decision_authority="human",
    )

    assert evidence.claim == "legacy_claim"
    assert evidence.run_id == "run-1"
    assert request.decision_authority == "human"


def test_v3_interchange_and_run_directory_validator_accept_canonical_records(tmp_path: Path) -> None:
    manifest = RunManifest(
        run_id="run-1", created_at="now", source=SourceIdentity(revision="sha"),
        executor=ExecutorIdentity("runner", "1.0.0"), configuration_hash="config", environment={},
    )
    event = LifecycleEvent("event-1", "run-1", "episode-1", 0, "episode.started", "now", "now")
    assert check_contract("manifest", manifest.to_dict()) == []
    assert check_contract("event", event.to_dict()) == []

    (tmp_path / "manifest.json").write_text(json.dumps(manifest.to_dict()), encoding="utf-8")
    (tmp_path / "events.jsonl").write_text(json.dumps(event.to_dict()) + "\n", encoding="utf-8")
    assert validate_run_directory(tmp_path) == []


def test_v3_interchange_rejects_legacy_top_level_fields() -> None:
    manifest = RunManifest(
        run_id="run-1", created_at="now", source=SourceIdentity(),
        executor=ExecutorIdentity("runner", "1.0.0"), configuration_hash="config", environment={},
    )
    payload = {**manifest.to_dict(), "model_name": "must-not-be-core"}

    assert check_contract("manifest", payload)


def test_v3_interchange_allows_domain_data_only_inside_profile_extensions() -> None:
    manifest = RunManifest(
        run_id="run-1", created_at="now", source=SourceIdentity(),
        executor=ExecutorIdentity("runner", "1.0.0"), configuration_hash="config", environment={},
        extensions={"software-delivery/v1": {"wave_id": "wave-1"}},
    )
    assert check_contract("manifest", manifest.to_dict()) == []
    assert check_contract("manifest", {**manifest.to_dict(), "environment": {"mrr": 0.9}})


def test_v3_fixtures_are_portable_contracts() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "agent_reliability_protocol" / "fixtures" / "v3"
    for kind, filename in (
        ("manifest", "run-manifest.valid.json"),
        ("event", "lifecycle-event.valid.json"),
        ("evidence", "evidence-record.valid.json"),
        ("gate-request", "gate-request.valid.json"),
        ("decision", "gate-decision.valid.json"),
    ):
        assert check_contract(kind, json.loads((root / filename).read_text(encoding="utf-8"))) == []
