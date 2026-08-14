"""Canonical ARP 3.0 contracts and explicit adapters for older payloads."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Literal, Mapping

from agent_reliability_protocol.contracts import (
    CapturePolicy,
    EvidenceReference as LegacyEvidenceReference,
    EvidenceStage,
    GateDecision as LegacyGateDecision,
    GateRequest as LegacyGateRequest,
    RunManifest as LegacyRunManifest,
)
from agent_reliability_protocol.events import LifecycleEvent as LegacyLifecycleEvent

SCHEMA_VERSION = "3.0.0"
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
Decision = Literal["approve", "warn", "request_clarification", "block"]
ScalarValue = str | int | float | bool | None
CHECKPOINTS = frozenset(
    {
        "episode.started",
        "input.received",
        "interpretation.completed",
        "plan.completed",
        "execution.started",
        "tool.completed",
        "retrieval.completed",
        "artifact.completed",
        "evaluation.completed",
        "gate.requested",
        "gate.decided",
        "episode.completed",
    }
)


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _v3(name: str, value: str) -> None:
    _nonempty(name, value)
    match = _SEMVER.fullmatch(value)
    if not match or int(match.group(1)) != 3:
        raise ValueError(f"{name} must be an ARP 3.x SemVer")


def _scalar(name: str, value: ScalarValue) -> None:
    if value is not None and not isinstance(value, (str, int, float, bool)):
        raise ValueError(f"{name} must be scalar")


def _policy(value: CapturePolicy | str) -> None:
    try:
        CapturePolicy(value)
    except ValueError as exc:
        raise ValueError("capture_policy must be one of: none, metadata, redacted, full") from exc


def _extensions(value: Mapping[str, Any]) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("extensions must be an object")
    if any(not isinstance(namespace, str) or not namespace.strip() for namespace in value):
        raise ValueError("extensions namespace must be a non-empty string")


def _strict(value: Mapping[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(value).difference(allowed))
    if unknown:
        raise ValueError("unknown v3 fields: " + ", ".join(str(item) for item in unknown))


@dataclass(frozen=True)
class SourceIdentity:
    revision: str | None = None
    input_ref: str | None = None
    input_hash: str | None = None

    def __post_init__(self) -> None:
        for name in ("revision", "input_ref", "input_hash"):
            value = getattr(self, name)
            if value is not None:
                _nonempty(name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"revision": self.revision, "input_ref": self.input_ref, "input_hash": self.input_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SourceIdentity":
        _strict(value, {"revision", "input_ref", "input_hash"})
        return cls(revision=value["revision"], input_ref=value["input_ref"], input_hash=value["input_hash"])


@dataclass(frozen=True)
class ExecutorIdentity:
    name: str
    version: str

    def __post_init__(self) -> None:
        _nonempty("executor.name", self.name)
        _nonempty("executor.version", self.version)

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExecutorIdentity":
        _strict(value, {"name", "version"})
        return cls(name=str(value["name"]), version=str(value["version"]))


@dataclass(frozen=True)
class EpisodeIdentity:
    run_id: str
    episode_id: str
    ordinal: int | None = None
    variant_ref: str | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _v3("schema_version", self.schema_version)
        _nonempty("run_id", self.run_id)
        _nonempty("episode_id", self.episode_id)
        if self.ordinal is not None and (not isinstance(self.ordinal, int) or self.ordinal < 0):
            raise ValueError("ordinal must be a non-negative integer")
        if self.variant_ref is not None:
            _nonempty("variant_ref", self.variant_ref)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "run_id": self.run_id, "episode_id": self.episode_id, "ordinal": self.ordinal, "variant_ref": self.variant_ref}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EpisodeIdentity":
        _strict(value, {"schema_version", "run_id", "episode_id", "ordinal", "variant_ref"})
        return cls(run_id=str(value["run_id"]), episode_id=str(value["episode_id"]), ordinal=value["ordinal"], variant_ref=value["variant_ref"], schema_version=str(value["schema_version"]))


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    created_at: str
    source: SourceIdentity
    executor: ExecutorIdentity
    configuration_hash: str
    environment: Mapping[str, Any]
    profile: str | None = None
    capture_policy: CapturePolicy | str = CapturePolicy.METADATA
    extensions: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _v3("schema_version", self.schema_version)
        for name in ("run_id", "created_at", "configuration_hash"):
            _nonempty(name, getattr(self, name))
        if not isinstance(self.source, SourceIdentity):
            raise ValueError("source must be a SourceIdentity")
        if not isinstance(self.executor, ExecutorIdentity):
            raise ValueError("executor must be an ExecutorIdentity")
        if not isinstance(self.environment, Mapping):
            raise ValueError("environment must be an object")
        if self.profile is not None:
            _nonempty("profile", self.profile)
        _policy(self.capture_policy)
        _extensions(self.extensions)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "run_id": self.run_id, "created_at": self.created_at, "source": self.source.to_dict(), "executor": self.executor.to_dict(), "configuration_hash": self.configuration_hash, "environment": dict(self.environment), "profile": self.profile, "capture_policy": CapturePolicy(self.capture_policy).value, "extensions": dict(self.extensions)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RunManifest":
        _strict(value, {"schema_version", "run_id", "created_at", "source", "executor", "configuration_hash", "environment", "profile", "capture_policy", "extensions"})
        return cls(run_id=str(value["run_id"]), created_at=str(value["created_at"]), source=SourceIdentity.from_dict(value["source"]), executor=ExecutorIdentity.from_dict(value["executor"]), configuration_hash=str(value["configuration_hash"]), environment=value["environment"], profile=value["profile"], capture_policy=value["capture_policy"], extensions=value["extensions"], schema_version=str(value["schema_version"]))


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    run_id: str
    claim: str
    observed: ScalarValue = None
    expected: ScalarValue = None
    comparator: str | None = None
    stage: EvidenceStage = EvidenceStage.PRE_FINAL
    source_event_id: str | None = None
    artifact_uri: str | None = None
    artifact_hash: str | None = None
    capture_policy: CapturePolicy | str = CapturePolicy.METADATA
    extensions: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _v3("schema_version", self.schema_version)
        for name in ("evidence_id", "run_id", "claim"):
            _nonempty(name, getattr(self, name))
        for name, value in (("observed", self.observed), ("expected", self.expected)):
            _scalar(name, value)
        for name in ("comparator", "source_event_id", "artifact_uri", "artifact_hash"):
            value = getattr(self, name)
            if value is not None:
                _nonempty(name, value)
        if not isinstance(self.stage, EvidenceStage):
            try:
                object.__setattr__(self, "stage", EvidenceStage(self.stage))
            except ValueError as exc:
                raise ValueError("stage is not a valid evidence stage") from exc
        _policy(self.capture_policy)
        _extensions(self.extensions)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "evidence_id": self.evidence_id, "run_id": self.run_id, "claim": self.claim, "observed": self.observed, "expected": self.expected, "comparator": self.comparator, "stage": self.stage.value, "source_event_id": self.source_event_id, "artifact_uri": self.artifact_uri, "artifact_hash": self.artifact_hash, "capture_policy": CapturePolicy(self.capture_policy).value, "extensions": dict(self.extensions)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvidenceRecord":
        _strict(value, {"schema_version", "evidence_id", "run_id", "claim", "observed", "expected", "comparator", "stage", "source_event_id", "artifact_uri", "artifact_hash", "capture_policy", "extensions"})
        return cls(**{**dict(value), "stage": EvidenceStage(value["stage"]), "schema_version": str(value["schema_version"])})


@dataclass(frozen=True)
class GateReason:
    code: str
    message: str

    def __post_init__(self) -> None:
        _nonempty("reason.code", self.code)
        _nonempty("reason.message", self.message)

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GateReason":
        return cls(code=str(value["code"]), message=str(value["message"]))


@dataclass(frozen=True)
class GateRequest:
    gate_id: str
    run_id: str
    checkpoint: str
    requested_at: str
    policy_version: str
    required_evidence: tuple[str, ...]
    decision_authority: str
    capture_policy: CapturePolicy | str = CapturePolicy.METADATA
    extensions: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _v3("schema_version", self.schema_version)
        for name in ("gate_id", "run_id", "checkpoint", "requested_at", "policy_version", "decision_authority"):
            _nonempty(name, getattr(self, name))
        if any(not isinstance(item, str) or not item.strip() for item in self.required_evidence):
            raise ValueError("required_evidence must contain non-empty strings")
        _policy(self.capture_policy)
        _extensions(self.extensions)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "gate_id": self.gate_id, "run_id": self.run_id, "checkpoint": self.checkpoint, "requested_at": self.requested_at, "policy_version": self.policy_version, "required_evidence": list(self.required_evidence), "decision_authority": self.decision_authority, "capture_policy": CapturePolicy(self.capture_policy).value, "extensions": dict(self.extensions)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GateRequest":
        _strict(value, {"schema_version", "gate_id", "run_id", "checkpoint", "requested_at", "policy_version", "required_evidence", "decision_authority", "capture_policy", "extensions"})
        return cls(**{**dict(value), "required_evidence": tuple(value["required_evidence"]), "schema_version": str(value["schema_version"])})


@dataclass(frozen=True)
class GateDecision:
    gate_id: str
    run_id: str
    checkpoint: str
    decision: Decision
    decided_at: str
    policy_version: str
    decision_authority: str
    reasons: tuple[GateReason, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    capture_policy: CapturePolicy | str = CapturePolicy.METADATA
    extensions: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _v3("schema_version", self.schema_version)
        for name in ("gate_id", "run_id", "checkpoint", "decided_at", "policy_version", "decision_authority"):
            _nonempty(name, getattr(self, name))
        if self.decision not in ("approve", "warn", "request_clarification", "block"):
            raise ValueError("invalid gate decision")
        if self.decision != "approve" and not self.reasons:
            raise ValueError("non-approval decisions require reasons")
        if any(not isinstance(item, str) or not item.strip() for item in self.evidence_ids):
            raise ValueError("evidence_ids must contain non-empty strings")
        if any(not isinstance(reason, GateReason) for reason in self.reasons):
            raise ValueError("reasons must contain GateReason values")
        _policy(self.capture_policy)
        _extensions(self.extensions)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "gate_id": self.gate_id, "run_id": self.run_id, "checkpoint": self.checkpoint, "decision": self.decision, "decided_at": self.decided_at, "policy_version": self.policy_version, "decision_authority": self.decision_authority, "reasons": [reason.to_dict() for reason in self.reasons], "evidence_ids": list(self.evidence_ids), "capture_policy": CapturePolicy(self.capture_policy).value, "extensions": dict(self.extensions)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GateDecision":
        _strict(value, {"schema_version", "gate_id", "run_id", "checkpoint", "decision", "decided_at", "policy_version", "decision_authority", "reasons", "evidence_ids", "capture_policy", "extensions"})
        return cls(**{**dict(value), "reasons": tuple(GateReason.from_dict(item) for item in value["reasons"]), "evidence_ids": tuple(value["evidence_ids"]), "schema_version": str(value["schema_version"])})


@dataclass(frozen=True)
class LifecycleEvent:
    event_id: str
    run_id: str
    episode_id: str
    sequence_number: int
    checkpoint: str
    started_at: str
    ended_at: str
    attributes: Mapping[str, Any] = field(default_factory=dict)
    content_reference: str | None = None
    parent_event_id: str | None = None
    extensions: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _v3("schema_version", self.schema_version)
        for name in ("event_id", "run_id", "episode_id", "checkpoint", "started_at", "ended_at"):
            _nonempty(name, getattr(self, name))
        if not isinstance(self.sequence_number, int) or self.sequence_number < 0:
            raise ValueError("sequence_number must be non-negative")
        if self.checkpoint not in CHECKPOINTS:
            raise ValueError("unsupported lifecycle checkpoint")
        if not isinstance(self.attributes, Mapping):
            raise ValueError("attributes must be an object")
        for name in ("content_reference", "parent_event_id"):
            value = getattr(self, name)
            if value is not None:
                _nonempty(name, value)
        _extensions(self.extensions)

    @property
    def event_type(self) -> str:
        return self.checkpoint

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "event_id": self.event_id, "run_id": self.run_id, "episode_id": self.episode_id, "sequence_number": self.sequence_number, "checkpoint": self.checkpoint, "event_type": self.checkpoint, "started_at": self.started_at, "ended_at": self.ended_at, "attributes": dict(self.attributes), "content_reference": self.content_reference, "parent_event_id": self.parent_event_id, "extensions": dict(self.extensions)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LifecycleEvent":
        _strict(value, {"schema_version", "event_id", "run_id", "episode_id", "sequence_number", "checkpoint", "event_type", "started_at", "ended_at", "attributes", "content_reference", "parent_event_id", "extensions"})
        if value["event_type"] != value["checkpoint"]:
            raise ValueError("checkpoint and event_type must match")
        return cls(**{key: value[key] for key in ("event_id", "run_id", "episode_id", "sequence_number", "checkpoint", "started_at", "ended_at", "attributes", "content_reference", "parent_event_id", "extensions", "schema_version")})


def validate_lifecycle_sequence(events: list[LifecycleEvent]) -> None:
    if not events:
        raise ValueError("lifecycle sequence must contain at least one event")
    first = events[0]
    identity = (first.run_id, first.episode_id)
    previous = first.sequence_number - 1
    seen: set[str] = set()
    requested = False
    for event in events:
        if (event.run_id, event.episode_id) != identity:
            raise ValueError("lifecycle event identity does not match sequence")
        if event.event_id in seen:
            raise ValueError("duplicate event_id in lifecycle sequence")
        seen.add(event.event_id)
        if event.sequence_number != previous + 1:
            raise ValueError("sequence numbers must be contiguous")
        previous = event.sequence_number
        if event.checkpoint == "gate.requested":
            requested = True
        if event.checkpoint == "gate.decided":
            if not requested:
                raise ValueError("gate.decided requires a preceding gate.requested")


def adapt_manifest_v2(value: Mapping[str, Any]) -> RunManifest:
    legacy = LegacyRunManifest.from_dict(value)
    return RunManifest(
        run_id=legacy.run_id,
        created_at=legacy.created_at,
        source=SourceIdentity(revision=legacy.git_sha, input_ref=legacy.dataset_id, input_hash=legacy.dataset_hash),
        executor=ExecutorIdentity(name=legacy.harness_name, version=legacy.harness_version),
        configuration_hash=legacy.configuration_hash,
        environment=legacy.environment,
        capture_policy=CapturePolicy.METADATA,
        extensions={"arp-compat/v2": {"experiment_id": legacy.experiment_id, "dataset_id": legacy.dataset_id, "model_provider": legacy.model_provider, "model_name": legacy.model_name, "model_version": legacy.model_version, "random_seed": legacy.random_seed, "replication_count": legacy.replication_count}},
    )


def adapt_event_v2(value: Mapping[str, Any]) -> LifecycleEvent:
    legacy = LegacyLifecycleEvent.from_dict(value)
    return LifecycleEvent(
        event_id=legacy.event_id,
        run_id=legacy.run_id,
        episode_id=legacy.episode_id,
        sequence_number=legacy.sequence_number,
        checkpoint=legacy.checkpoint,
        started_at=legacy.started_at,
        ended_at=legacy.ended_at,
        attributes={},
        content_reference=legacy.content_reference,
        parent_event_id=legacy.parent_event_id,
        extensions={"arp-compat/v2": {"experiment_id": legacy.experiment_id, "replication_id": legacy.replication_id, "attributes": dict(legacy.attributes)}},
    )


def adapt_evidence_v2(value: Mapping[str, Any], *, run_id: str) -> EvidenceRecord:
    legacy = LegacyEvidenceReference.from_dict(value)
    claim = legacy.claim or legacy.metric_name or "legacy_evidence"
    return EvidenceRecord(
        evidence_id=legacy.evidence_id,
        run_id=run_id,
        claim=claim,
        observed=legacy.observed if legacy.observed is not None else legacy.observed_value,
        expected=legacy.expected if legacy.expected is not None else legacy.threshold,
        comparator=legacy.comparator,
        stage=legacy.stage,
        source_event_id=legacy.event_id,
        artifact_uri=legacy.artifact_uri,
        artifact_hash=legacy.artifact_hash,
        capture_policy=legacy.capture_policy or CapturePolicy.METADATA,
        extensions={"arp-compat/v2": {"metric_name": legacy.metric_name, "threshold": legacy.threshold}},
    )


def adapt_gate_request_v2(value: Mapping[str, Any], *, decision_authority: str) -> GateRequest:
    legacy = LegacyGateRequest.from_dict(value)
    return GateRequest(
        gate_id=legacy.gate_id,
        run_id=legacy.run_id,
        checkpoint=legacy.checkpoint,
        requested_at=legacy.requested_at,
        policy_version=legacy.policy_version,
        required_evidence=legacy.required_evidence,
        decision_authority=decision_authority,
        capture_policy=legacy.capture_policy or CapturePolicy.METADATA,
        extensions={"arp-compat/v2": dict(legacy.extensions)},
    )


def adapt_decision_v2(value: Mapping[str, Any], *, run_id: str, gate_id: str, decided_at: str, policy_version: str, decision_authority: str) -> GateDecision:
    legacy = LegacyGateDecision.from_dict(value)
    reasons = tuple(GateReason(reason.code, reason.message) for reason in legacy.reasons)
    return GateDecision(gate_id=gate_id, run_id=run_id, checkpoint=legacy.checkpoint, decision=legacy.decision, decided_at=decided_at, policy_version=policy_version, decision_authority=decision_authority, reasons=reasons, evidence_ids=tuple(item.evidence_id for item in legacy.evidence))
