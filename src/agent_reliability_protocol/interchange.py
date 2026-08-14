"""Validation, compatibility adapters, redaction, and run-directory checks."""
from __future__ import annotations
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Iterable, Literal
from agent_reliability_protocol.contracts import CapturePolicy, EvidenceReference, GateDecision, GateRequest, RunManifest
from agent_reliability_protocol.events import LifecycleEvent, LIFECYCLE_CHECKPOINTS, validate_lifecycle_sequence
from agent_reliability_protocol.v3 import (
    EpisodeIdentity as EpisodeIdentityV3,
    EvidenceRecord as EvidenceRecordV3,
    GateDecision as GateDecisionV3,
    GateRequest as GateRequestV3,
    LifecycleEvent as LifecycleEventV3,
    RunManifest as RunManifestV3,
    validate_lifecycle_sequence as validate_lifecycle_sequence_v3,
)
from agent_reliability_protocol.neutral import assert_neutral_contract

ContractKind = Literal["decision", "event", "manifest", "episode", "sequence", "envelope", "evidence", "gate-request"]
CaptureContent = CapturePolicy
_SECRET_MARKERS = ("secret", "token", "password", "authorization", "cookie", "api_key", "prompt", "artifact", "tool_arguments", "retrieved_content", "pii")

def redact_contract(value: Any, capture_content: CaptureContent | str = CaptureContent.REDACTED) -> Any:
    mode = CaptureContent(capture_content)
    if mode is CaptureContent.FULL: return value
    if mode is CaptureContent.NONE: return None
    if isinstance(value, Mapping):
        return {str(key): ("[REDACTED]" if mode is CaptureContent.REDACTED else "[OMITTED]") if _sensitive(str(key)) else redact_contract(item, mode) for key, item in value.items()}
    if isinstance(value, (list, tuple)): return [redact_contract(item, mode) for item in value]
    return value

def export_contract(value: Any, path: Path | str, *, redact: bool = True, capture_content: CaptureContent | str | None = None) -> None:
    payload = value.to_dict() if hasattr(value, "to_dict") else value
    mode = capture_content or (CaptureContent.REDACTED if redact else CaptureContent.FULL)
    output = Path(path); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(redact_contract(payload, mode), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

def check_contract(kind: ContractKind, payload: Mapping[str, Any]) -> list[str]:
    try:
        json.dumps(payload, ensure_ascii=True)
        is_v3 = str(payload.get("schema_version", "")).startswith("3.")
        if is_v3:
            assert_neutral_contract(payload)
        if kind == "decision": (GateDecisionV3 if is_v3 else GateDecision).from_dict(payload)
        elif kind == "event": (LifecycleEventV3 if is_v3 else LifecycleEvent).from_dict(payload)
        elif kind == "manifest": (RunManifestV3 if is_v3 else RunManifest).from_dict(payload)
        elif kind == "episode": EpisodeIdentityV3.from_dict(payload)
        elif kind == "evidence": (EvidenceRecordV3 if is_v3 else EvidenceReference).from_dict(payload)
        elif kind == "gate-request": (GateRequestV3 if is_v3 else GateRequest).from_dict(payload)
        elif kind == "sequence":
            events = payload.get("events", ())
            if events and str(events[0].get("schema_version", "")).startswith("3."):
                validate_lifecycle_sequence_v3([LifecycleEventV3.from_dict(event) for event in events])
            else:
                validate_lifecycle_sequence(events)
        elif kind == "envelope": validate_thesis_envelope(payload["manifest"], payload["events"])
        else: return [f"unknown contract kind: {kind}"]
    except (KeyError, TypeError, ValueError) as exc: return [str(exc)]
    return []


def validate_thesis_envelope(manifest: RunManifest | Mapping[str, Any], events: Iterable[LifecycleEvent | Mapping[str, Any]]) -> None:
    """Validate cross-record identity for a canonical ARP lifecycle envelope.

    The manifest supplies the project/experiment and dataset identity; every
    event must remain in that run and experiment.  Producers may repeat
    ``project_id`` and ``dataset_id`` in event attributes, but if present those
    values are checked against the manifest instead of being trusted.
    """
    parsed_manifest = manifest if isinstance(manifest, RunManifest) else RunManifest.from_dict(manifest)
    if getattr(parsed_manifest, "_legacy", False):
        raise ValueError("thesis envelopes require a canonical ARP manifest")
    for name in ("experiment_id", "run_id", "dataset_id", "dataset_hash"):
        value = getattr(parsed_manifest, name, None)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"manifest {name} identity is required")
    parsed_events = [event if isinstance(event, LifecycleEvent) else LifecycleEvent.from_dict(event) for event in events]
    validate_lifecycle_sequence(parsed_events)
    project_id = getattr(parsed_manifest, "project_id", None) or parsed_manifest.metadata.get("project_id") or parsed_manifest.experiment_id
    for event in parsed_events:
        if event.experiment_id != parsed_manifest.experiment_id:
            raise ValueError("event experiment_id does not match manifest project identity")
        if event.run_id != parsed_manifest.run_id:
            raise ValueError("event run_id does not match manifest")
        attributes = event.attributes
        event_project = attributes.get("project_id") or attributes.get("experiment_id")
        if event_project is not None and event_project != project_id:
            raise ValueError("event project identity does not match manifest")
        event_dataset = attributes.get("dataset_id")
        if event_dataset is not None and event_dataset != parsed_manifest.dataset_id:
            raise ValueError("event dataset identity does not match manifest")

def upgrade_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    """Preserve the legacy v0.1 normal form for existing consumers."""
    legacy = RunManifest.from_dict(value)
    payload = legacy.to_dict(); payload["schema_version"] = "arp/v1"; return payload

def adapt_manifest_v2(value: Mapping[str, Any]) -> dict[str, Any]:
    """Convert a legacy manifest into the v2 canonical representation."""
    legacy = RunManifest.from_dict(value)
    return RunManifest(schema_version="2.0.0", experiment_id=legacy.experiment_id, run_id=legacy.run_id, created_at=legacy.created_at, git_sha=legacy.git_sha, harness_name=legacy.harness_name, harness_version=legacy.harness_version, dataset_id=legacy.dataset_id, dataset_hash=legacy.dataset_hash, configuration_hash=legacy.configuration_hash, model_provider=legacy.model_provider, model_name=legacy.model_name, model_version=legacy.model_version, random_seed=legacy.random_seed, replication_count=legacy.replication_count, environment=legacy.environment, artifacts=legacy.artifacts, metadata=legacy.metadata, configuration=legacy.configuration, labels=legacy.labels).to_dict()

def validate_run_directory(path: Path | str) -> list[str]:
    directory = Path(path); errors: list[str] = []; manifest_path = directory / "manifest.json"; events_path = directory / "events.jsonl"
    if not manifest_path.is_file(): return ["missing manifest.json"]
    try: manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc: return [f"invalid manifest.json: {exc.msg}"]
    if str(manifest.get("schema_version", "")).startswith("3."):
        return validate_run_directory_v3(directory, manifest, events_path)
    errors.extend(f"manifest: {e}" for e in check_contract("manifest", manifest))
    for name, reference in (manifest.get("artifacts") or {}).items():
        if isinstance(reference, str) and "://" not in reference and not (directory / reference).exists(): errors.append(f"manifest artifact {name!r} does not exist: {reference}")
    if not events_path.is_file(): return errors + ["missing events.jsonl"]
    seen: set[str] = set(); sequence_by_episode: dict[tuple[str, int], int] = {}; parsed_events: list[LifecycleEvent] = []
    for line_number, line in enumerate(events_path.read_text(encoding="utf-8").splitlines(), 1):
        try: event = json.loads(line); parsed = LifecycleEvent.from_dict(event)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc: errors.append(f"events.jsonl:{line_number}: {exc}"); continue
        parsed_events.append(parsed)
        if parsed.run_id != manifest.get("run_id"): errors.append(f"events.jsonl:{line_number}: run_id does not match manifest")
        if parsed.experiment_id != manifest.get("experiment_id", parsed.experiment_id) and not parsed._legacy:
            errors.append(f"events.jsonl:{line_number}: experiment_id does not match manifest")
        if parsed.event_id in seen: errors.append(f"events.jsonl:{line_number}: duplicate event_id")
        seen.add(parsed.event_id)
        key = (parsed.episode_id, parsed.replication_id); previous = sequence_by_episode.get(key, -1)
        if parsed.sequence_number <= previous: errors.append(f"events.jsonl:{line_number}: sequence_number is not ordered")
        sequence_by_episode[key] = parsed.sequence_number
        if parsed.parent_event_id and parsed.parent_event_id not in seen: errors.append(f"events.jsonl:{line_number}: parent_event_id must reference a preceding event")
        if parsed.checkpoint not in LIFECYCLE_CHECKPOINTS: errors.append(f"events.jsonl:{line_number}: invalid checkpoint")
    if parsed_events:
        try:
            validate_lifecycle_sequence(parsed_events)
        except ValueError as exc:
            errors.append(f"events.jsonl: lifecycle envelope invalid: {exc}")
    return errors


def validate_run_directory_v3(directory: Path, manifest: Mapping[str, Any] | None = None, events_path: Path | None = None) -> list[str]:
    """Validate a v3 manifest and its JSONL lifecycle envelope."""
    errors: list[str] = []
    manifest = manifest or json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    events_path = events_path or directory / "events.jsonl"
    try:
        assert_neutral_contract(manifest)
        parsed_manifest = RunManifestV3.from_dict(manifest)
    except (KeyError, TypeError, ValueError) as exc:
        return [f"manifest: {exc}"]
    if not events_path.is_file():
        return ["missing events.jsonl"]
    parsed_events: list[LifecycleEventV3] = []
    seen: set[str] = set()
    for line_number, line in enumerate(events_path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            event_payload = json.loads(line)
            assert_neutral_contract(event_payload)
            parsed = LifecycleEventV3.from_dict(event_payload)
            if parsed.run_id != parsed_manifest.run_id:
                raise ValueError("run_id does not match manifest")
            if parsed.event_id in seen:
                raise ValueError("duplicate event_id")
            seen.add(parsed.event_id)
            parsed_events.append(parsed)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"events.jsonl:{line_number}: {exc}")
    if parsed_events:
        try:
            validate_lifecycle_sequence_v3(parsed_events)
        except ValueError as exc:
            errors.append(f"events.jsonl: lifecycle envelope invalid: {exc}")
    return errors

def _sensitive(key: str) -> bool: return any(marker in key.lower().replace("-", "_") for marker in _SECRET_MARKERS)
