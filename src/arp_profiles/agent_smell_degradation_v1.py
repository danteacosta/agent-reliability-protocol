"""Normative validator for the ARP requirement-degradation profile."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from agent_reliability_protocol.v3 import LifecycleEvent, validate_lifecycle_sequence


AGENT_SMELL_PROFILE = "agent-smell-degradation/v1"
_PRE_FINAL_CHECKPOINTS = frozenset(
    {
        "input.received",
        "interpretation.completed",
        "plan.completed",
        "execution.started",
        "tool.completed",
        "retrieval.completed",
    }
)
_RUNTIME_CHECKPOINTS = _PRE_FINAL_CHECKPOINTS - {"input.received"}
_LABEL_PLANE_CHECKPOINTS = frozenset({"artifact.completed", "evaluation.completed"})
_PROHIBITED_PREFINAL_KEYS = frozenset(
    {"condition", "defect", "defect_class", "smell", "smell_type", "oracle", "oracle_spec", "label", "expected_outcome"}
)


def validate_agent_smell_run(
    manifest: Mapping[str, object],
    events: Sequence[Mapping[str, object]],
) -> list[str]:
    """Validate provenance, temporal separation, and label isolation for one run."""
    errors: list[str] = []
    if not isinstance(manifest, Mapping):
        return ["manifest must be a JSON object"]
    if manifest.get("schema_version") != "3.0.0":
        errors.append("manifest must use ARP 3.0.0")
    if manifest.get("profile") != AGENT_SMELL_PROFILE:
        errors.append(f"manifest.profile must be {AGENT_SMELL_PROFILE}")
    extension = _extension(manifest, errors, "manifest")
    required = {
        "experiment_id",
        "project_id",
        "source_intent_id",
        "variant_ref",
        "split",
        "confirmatory",
        "checkpoint_provenance",
    }
    if extension is not None:
        missing = sorted(required - set(extension))
        if missing:
            errors.append("profile manifest extension missing: " + ", ".join(missing))
        for field in required - {"confirmatory"}:
            if field in extension and (not isinstance(extension[field], str) or not str(extension[field]).strip()):
                errors.append(f"profile manifest extension {field} must be non-empty text")
        if "confirmatory" in extension and not isinstance(extension["confirmatory"], bool):
            errors.append("profile manifest extension confirmatory must be boolean")
        split = extension.get("split")
        if not isinstance(split, str) or split not in {"train", "calibration", "test", "pilot"}:
            errors.append("profile split must be train, calibration, test, or pilot")
        provenance = extension.get("checkpoint_provenance")
        if not isinstance(provenance, str) or provenance not in {"runtime_native", "replay_derived", "synthetic"}:
            errors.append("checkpoint_provenance must be runtime_native, replay_derived, or synthetic")
        if extension.get("confirmatory") is True and provenance != "runtime_native":
            errors.append("confirmatory runs require runtime_native checkpoint provenance")

    if not isinstance(events, Sequence) or isinstance(events, (str, bytes, bytearray)):
        return errors + ["events must be an array of event objects"]

    event_errors: list[str] = []
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            event_errors.append(f"event {index}: contract must be a JSON object")
            continue
        for field in ("episode_id", "checkpoint"):
            value = event.get(field)
            if not isinstance(value, str) or not value.strip():
                event_errors.append(f"event {index}: {field} must be non-empty text")
        sequence = event.get("sequence_number")
        if type(sequence) is not int or sequence < 0:
            event_errors.append(f"event {index}: sequence_number must be a non-negative integer")
    if event_errors:
        return errors + event_errors

    ordered = sorted(events, key=lambda event: event["sequence_number"])
    try:
        typed_events = [LifecycleEvent.from_dict(event) for event in events]
        validate_lifecycle_sequence(typed_events)
    except (KeyError, TypeError, ValueError) as error:
        errors.append(f"invalid ARP lifecycle sequence: {error}")
    manifest_run_id = manifest.get("run_id")
    if any(event.get("run_id") != manifest_run_id for event in events):
        errors.append("every event run_id must match the manifest run_id")
    episode_ids = {event.get("episode_id") for event in events}
    if len(episode_ids) != 1 or None in episode_ids:
        errors.append("all events must share one non-empty episode_id")
    artifact_sequences = [
        event["sequence_number"]
        for event in ordered
        if event.get("checkpoint") == "artifact.completed"
    ]
    evaluation_sequences = [
        event["sequence_number"]
        for event in ordered
        if event.get("checkpoint") == "evaluation.completed"
    ]
    if not artifact_sequences:
        errors.append("one artifact.completed event is required")
    elif len(artifact_sequences) > 1:
        errors.append("only one artifact.completed event is allowed")
    if evaluation_sequences and artifact_sequences and min(evaluation_sequences) <= artifact_sequences[0]:
        errors.append("evaluation.completed must occur after artifact.completed")

    for event in ordered:
        checkpoint = event.get("checkpoint")
        sequence = event["sequence_number"]
        if checkpoint in _PRE_FINAL_CHECKPOINTS:
            if artifact_sequences and sequence >= artifact_sequences[0]:
                errors.append(f"pre-final checkpoint {checkpoint} must precede artifact.completed")
            leaked = _find_prohibited_keys(event.get("attributes")) | _find_prohibited_keys(event.get("extensions"))
            if leaked:
                errors.append(f"pre-final checkpoint {checkpoint} leaks label-plane keys: {', '.join(sorted(leaked))}")
        if checkpoint in _RUNTIME_CHECKPOINTS:
            event_extension = _extension(event, errors, f"event {event.get('event_id', sequence)}")
            if event_extension is not None and event_extension.get("checkpoint_source") != "runtime_native":
                errors.append(f"checkpoint {checkpoint} must declare checkpoint_source=runtime_native")
        if checkpoint in _LABEL_PLANE_CHECKPOINTS:
            event_extension = _extension(event, errors, f"event {event.get('event_id', sequence)}")
            if event_extension is not None and event_extension.get("plane") != "label":
                errors.append(f"checkpoint {checkpoint} must declare plane=label")
    return errors


def _extension(
    document: Mapping[str, object],
    errors: list[str],
    subject: str,
) -> Mapping[str, object] | None:
    extensions = document.get("extensions")
    if not isinstance(extensions, Mapping):
        errors.append(f"{subject}.extensions must be an object")
        return None
    extension = extensions.get(AGENT_SMELL_PROFILE)
    if not isinstance(extension, Mapping):
        errors.append(f"{subject} must contain the {AGENT_SMELL_PROFILE} extension")
        return None
    return extension


def _find_prohibited_keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).casefold()
            if normalized in _PROHIBITED_PREFINAL_KEYS:
                found.add(normalized)
            found.update(_find_prohibited_keys(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            found.update(_find_prohibited_keys(child))
    return found


__all__ = ["AGENT_SMELL_PROFILE", "validate_agent_smell_run"]
