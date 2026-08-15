from __future__ import annotations

from arp_profiles import AGENT_SMELL_PROFILE, validate_agent_smell_run


def manifest(*, confirmatory: bool = True, provenance: str = "runtime_native") -> dict[str, object]:
    return {
        "schema_version": "3.0.0",
        "run_id": "run-1",
        "profile": AGENT_SMELL_PROFILE,
        "extensions": {
            AGENT_SMELL_PROFILE: {
                "experiment_id": "exp-1",
                "project_id": "project-1",
                "source_intent_id": "intent-1",
                "variant_ref": "sha256:opaque",
                "split": "test" if confirmatory else "pilot",
                "confirmatory": confirmatory,
                "checkpoint_provenance": provenance,
            }
        },
    }


def event(sequence: int, checkpoint: str, **profile: object) -> dict[str, object]:
    return {
        "event_id": f"event-{sequence}",
        "schema_version": "3.0.0",
        "run_id": "run-1",
        "episode_id": "episode-1",
        "sequence_number": sequence,
        "checkpoint": checkpoint,
        "event_type": checkpoint,
        "started_at": f"2026-08-15T00:00:{sequence:02d}+00:00",
        "ended_at": f"2026-08-15T00:00:{sequence:02d}+00:00",
        "attributes": {},
        "content_reference": None,
        "parent_event_id": None if sequence == 0 else f"event-{sequence - 1}",
        "extensions": {AGENT_SMELL_PROFILE: profile},
    }


def valid_events() -> list[dict[str, object]]:
    return [
        event(0, "input.received"),
        event(1, "interpretation.completed", checkpoint_source="runtime_native"),
        event(2, "plan.completed", checkpoint_source="runtime_native"),
        event(3, "execution.started", checkpoint_source="runtime_native"),
        event(4, "tool.completed", checkpoint_source="runtime_native"),
        event(5, "artifact.completed", plane="label"),
        event(6, "evaluation.completed", plane="label"),
    ]


def test_confirmatory_profile_accepts_native_temporally_separated_events() -> None:
    assert validate_agent_smell_run(manifest(), valid_events()) == []


def test_confirmatory_profile_fails_closed_on_derived_checkpoints() -> None:
    errors = validate_agent_smell_run(
        manifest(provenance="replay_derived"),
        valid_events(),
    )

    assert "confirmatory runs require runtime_native checkpoint provenance" in errors


def test_pre_final_events_reject_label_and_oracle_leakage() -> None:
    events = valid_events()
    events[2]["attributes"] = {"oracle_spec": {"expected": "failure"}, "condition": "smelly"}

    errors = validate_agent_smell_run(manifest(), events)

    assert any("leaks label-plane keys: condition, oracle_spec" in error for error in errors)


def test_runtime_checkpoints_must_be_native_and_precede_artifact() -> None:
    events = valid_events()
    events[2]["extensions"] = {AGENT_SMELL_PROFILE: {"checkpoint_source": "synthetic"}}
    events[2]["sequence_number"] = 7

    errors = validate_agent_smell_run(manifest(), events)

    assert any("must declare checkpoint_source=runtime_native" in error for error in errors)
    assert any("must precede artifact.completed" in error for error in errors)


def test_artifact_and_evaluation_are_label_plane_only_and_ordered() -> None:
    events = valid_events()
    events[-2]["extensions"] = {AGENT_SMELL_PROFILE: {"plane": "observable"}}
    events[-1]["sequence_number"] = 4

    errors = validate_agent_smell_run(manifest(), events)

    assert "evaluation.completed must occur after artifact.completed" in errors
    assert any("artifact.completed must declare plane=label" in error for error in errors)


def test_profile_requires_non_empty_grouping_identity_and_boolean_flag() -> None:
    broken = manifest()
    extension = broken["extensions"][AGENT_SMELL_PROFILE]
    extension["project_id"] = ""
    extension["confirmatory"] = "yes"

    errors = validate_agent_smell_run(broken, valid_events())

    assert "profile manifest extension project_id must be non-empty text" in errors
    assert "profile manifest extension confirmatory must be boolean" in errors


def test_profile_rejects_cross_run_and_non_contiguous_events() -> None:
    events = valid_events()
    events[1]["run_id"] = "other-run"
    events[2]["sequence_number"] = 9

    errors = validate_agent_smell_run(manifest(), events)

    assert "every event run_id must match the manifest run_id" in errors
    assert any(error.startswith("invalid ARP lifecycle sequence") for error in errors)
