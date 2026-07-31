"""Acceptance tests for the ARP v2 neutral interchange contract."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class ArpV2ContractTests(unittest.TestCase):
    def test_episode_identity_is_complete_and_serializable(self) -> None:
        from agent_reliability_protocol import EpisodeIdentity

        identity = EpisodeIdentity(
            experiment_id="experiment-1",
            run_id="run-1",
            episode_id="episode-1",
            replication_id=0,
            workload_id="workload-1",
            variant_id="clean",
        )

        self.assertEqual(EpisodeIdentity.from_dict(identity.to_dict()), identity)

    def test_v2_manifest_round_trips_with_required_reproducibility_fields(self) -> None:
        from agent_reliability_protocol import RunManifest

        manifest = RunManifest(
            schema_version="2.0.0",
            experiment_id="experiment-1",
            run_id="run-1",
            created_at="2026-07-30T00:00:00+00:00",
            git_sha="abc123",
            harness_name="neutral-harness",
            harness_version="1.0.0",
            dataset_id="dataset-1",
            dataset_hash="sha256:dataset",
            configuration_hash="sha256:config",
            model_provider="example-provider",
            model_name="example-model",
            model_version="2026-07",
            random_seed=7,
            replication_count=3,
            environment={"runtime": "test"},
        )

        self.assertEqual(RunManifest.from_dict(json.loads(json.dumps(manifest.to_dict()))), manifest)

    def test_pre_final_evidence_cannot_reference_terminal_artifact_or_label(self) -> None:
        from agent_reliability_protocol import EvidenceReference, EvidenceStage

        with self.assertRaises(ValueError):
            EvidenceReference("e-1", artifact_uri="artifacts/final.json", stage=EvidenceStage.PRE_FINAL)
        with self.assertRaises(ValueError):
            EvidenceReference("e-2", artifact_uri="labels/final.json", stage=EvidenceStage.PRE_FINAL)

    def test_lifecycle_requires_complete_envelope_and_checkpoint(self) -> None:
        from agent_reliability_protocol import LifecycleEvent

        event = LifecycleEvent(
            event_id="event-1", schema_version="2.0.0", experiment_id="experiment-1", run_id="run-1",
            episode_id="episode-1", replication_id=0, sequence_number=1,
            checkpoint="interpretation.completed", event_type="interpretation.completed",
            started_at="2026-07-30T00:00:00+00:00", ended_at="2026-07-30T00:00:01+00:00",
            attributes={"intent": "summarize"}, content_reference="content://input", parent_event_id=None,
        )
        self.assertEqual(LifecycleEvent.from_dict(event.to_dict()), event)

    def test_lifecycle_sequence_enforces_identity_order_and_thesis_checkpoints(self) -> None:
        from agent_reliability_protocol import LifecycleEvent, validate_lifecycle_sequence

        events = [
            LifecycleEvent(
                event_id="event-1", schema_version="2.0.5", experiment_id="project-1", run_id="run-1",
                episode_id="episode-1", replication_id=0, sequence_number=1,
                checkpoint="input.received", event_type="input.received",
                started_at="2026-07-30T00:00:00+00:00", ended_at="2026-07-30T00:00:01+00:00",
            ),
            LifecycleEvent(
                event_id="event-2", schema_version="2.0.5", experiment_id="project-1", run_id="run-1",
                episode_id="episode-1", replication_id=0, sequence_number=2,
                checkpoint="interpretation.completed", event_type="interpretation.completed",
                started_at="2026-07-30T00:00:01+00:00", ended_at="2026-07-30T00:00:02+00:00",
            ),
            LifecycleEvent(
                event_id="event-3", schema_version="2.0.5", experiment_id="project-1", run_id="run-1",
                episode_id="episode-1", replication_id=0, sequence_number=3,
                checkpoint="plan.completed", event_type="plan.completed",
                started_at="2026-07-30T00:00:02+00:00", ended_at="2026-07-30T00:00:03+00:00",
            ),
            LifecycleEvent(
                event_id="event-4", schema_version="2.0.5", experiment_id="project-1", run_id="run-1",
                episode_id="episode-1", replication_id=0, sequence_number=4,
                checkpoint="execution.started", event_type="execution.started",
                started_at="2026-07-30T00:00:03+00:00", ended_at="2026-07-30T00:00:04+00:00",
            ),
        ]

        self.assertIsNone(validate_lifecycle_sequence(events))

        with self.assertRaisesRegex(ValueError, "sequence"):
            validate_lifecycle_sequence(events[:1] + [LifecycleEvent.from_dict({**events[1].to_dict(), "sequence_number": 3})])
        with self.assertRaisesRegex(ValueError, "identity"):
            validate_lifecycle_sequence(events[:1] + [LifecycleEvent.from_dict({**events[1].to_dict(), "episode_id": "other"})])

    def test_thesis_envelope_requires_manifest_identity_and_rejects_invalid_events(self) -> None:
        from agent_reliability_protocol import LifecycleEvent, RunManifest, validate_thesis_envelope

        manifest = RunManifest(
            schema_version="2.0.5", experiment_id="project-1", run_id="run-1", created_at="now",
            git_sha="sha", harness_name="harness", harness_version="1", dataset_id="dataset-1",
            dataset_hash="dataset-hash", configuration_hash="config-hash", model_provider="provider",
            model_name="model", model_version="version", random_seed=1, replication_count=1, environment={},
        )
        event = LifecycleEvent(
            event_id="event-1", schema_version="2.0.5", experiment_id="project-1", run_id="run-1",
            episode_id="episode-1", replication_id=0, sequence_number=1,
            checkpoint="input.received", event_type="input.received", started_at="now", ended_at="later",
            attributes={"dataset_id": "dataset-1"},
        )

        self.assertIsNone(validate_thesis_envelope(manifest, [event]))
        with self.assertRaisesRegex(ValueError, "experiment_id"):
            validate_thesis_envelope(manifest, [LifecycleEvent.from_dict({**event.to_dict(), "experiment_id": "other"})])


    def test_gate_decision_carries_a_structured_reason_evidence_and_threshold(self) -> None:
        from agent_reliability_protocol import DecisionReason, EvidenceReference, EvidenceStage, GateDecision

        decision = GateDecision(
            decision="warn", risk_score=0.7, confidence=0.9, checkpoint="gate.decided",
            reasons=(DecisionReason("quality.low", "quality fell below policy"),),
            evidence=(EvidenceReference("e-1", metric_name="quality", observed_value=0.7, threshold=0.9, stage=EvidenceStage.PRE_FINAL),),
            threshold_version="thresholds/1.0.0",
        )
        self.assertEqual(GateDecision.from_dict(decision.to_dict()), decision)

    def test_exporters_preserve_the_canonical_event_payload(self) -> None:
        from agent_reliability_protocol import LifecycleEvent, OpenInferenceExporter, OpenTelemetryExporter

        event = LifecycleEvent(
            event_id="event-1", schema_version="2.0.0", experiment_id="experiment-1", run_id="run-1",
            episode_id="episode-1", replication_id=0, sequence_number=1,
            checkpoint="input.received", event_type="input.received",
            started_at="2026-07-30T00:00:00+00:00", ended_at="2026-07-30T00:00:01+00:00",
        )
        self.assertEqual(OpenTelemetryExporter().export(event)["arp.event"], event.to_dict())
        self.assertEqual(OpenInferenceExporter().export(event)["arp.event"], event.to_dict())

    def test_capture_content_redacts_secret_values_without_changing_metadata(self) -> None:
        from agent_reliability_protocol import CaptureContent, redact_contract

        redacted = redact_contract({"prompt": "email jane@example.com", "model": "small", "api_key": "secret"}, CaptureContent.REDACTED)
        self.assertEqual(redacted["model"], "small")
        self.assertEqual(redacted["prompt"], "[REDACTED]")
        self.assertEqual(redacted["api_key"], "[REDACTED]")
        self.assertEqual(redact_contract({"prompt": "private", "model": "small"}, CaptureContent.METADATA), {"prompt": "[OMITTED]", "model": "small"})

    def test_run_directory_validator_checks_cross_file_invariants(self) -> None:
        from agent_reliability_protocol import LifecycleEvent, RunManifest, validate_run_directory

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            manifest = RunManifest("2.0.0", "experiment-1", "run-1", "2026-07-30T00:00:00+00:00", "abc123", "harness", "1.0.0", "dataset", "hash", "config", "provider", "model", "version", 1, 1, {})
            event = LifecycleEvent("event-1", "2.0.0", "experiment-1", "run-1", "episode-1", 0, 1, "episode.started", "episode.started", "2026-07-30T00:00:00+00:00", "2026-07-30T00:00:01+00:00")
            (directory / "manifest.json").write_text(json.dumps(manifest.to_dict()), encoding="utf-8")
            (directory / "events.jsonl").write_text(json.dumps(event.to_dict()) + "\n", encoding="utf-8")
            self.assertEqual(validate_run_directory(directory), [])

    def test_contract_cli_accepts_a_run_directory_as_its_direct_argument(self) -> None:
        from agent_reliability_protocol.__main__ import main
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            manifest = {"schema_version": "2.0.0", "experiment_id": "x", "run_id": "run", "created_at": "now", "git_sha": "sha", "harness_name": "h", "harness_version": "1", "dataset_id": "d", "dataset_hash": "d", "configuration_hash": "c", "model_provider": "p", "model_name": "m", "model_version": "v", "random_seed": 1, "replication_count": 1, "environment": {}}
            event = {"event_id": "e", "schema_version": "2.0.0", "experiment_id": "x", "run_id": "run", "episode_id": "ep", "replication_id": 0, "sequence_number": 1, "checkpoint": "episode.started", "event_type": "episode.started", "started_at": "now", "ended_at": "now", "attributes": {}, "content_reference": None, "parent_event_id": None}
            (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (directory / "events.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
            self.assertEqual(main([str(directory)]), 0)

    def test_valid_and_invalid_v2_fixtures_are_distinguished(self) -> None:
        from agent_reliability_protocol import check_contract

        root = Path(__file__).resolve().parents[1] / "src" / "agent_reliability_protocol" / "fixtures" / "v2"
        for kind, name in (("manifest", "run-manifest"), ("event", "lifecycle-event"), ("decision", "gate-decision")):
            self.assertEqual(check_contract(kind, json.loads((root / f"{name}.valid.json").read_text(encoding="utf-8"))), [])
            self.assertNotEqual(check_contract(kind, json.loads((root / f"{name}.invalid.json").read_text(encoding="utf-8"))), [])

        self.assertEqual(check_contract("envelope", json.loads((root / "lifecycle-envelope.valid.json").read_text(encoding="utf-8"))), [])
        self.assertNotEqual(check_contract("envelope", json.loads((root / "lifecycle-envelope.invalid.json").read_text(encoding="utf-8"))), [])


if __name__ == "__main__":
    unittest.main()
