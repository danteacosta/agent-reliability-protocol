"""Versioned, domain-neutral contracts for agent reliability runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Literal, Mapping

SCHEMA_VERSION = "2.0.2"
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
DecisionOutcome = Literal["pass", "fail"]
Decision = Literal["approve", "warn", "request_clarification", "block"]


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip(): raise ValueError(f"{name} must be a non-empty string")

def _schema_version(value: str) -> None:
    if value not in {"arp/v1", "protocol_next/v1"} and not _SEMVER.fullmatch(value): raise ValueError("schema_version must be SemVer")


@dataclass(frozen=True)
class EpisodeIdentity:
    experiment_id: str; run_id: str; episode_id: str; replication_id: int; workload_id: str; variant_id: str | None = None
    def __post_init__(self) -> None:
        for name in ("experiment_id", "run_id", "episode_id", "workload_id"): _nonempty(name, getattr(self, name))
        if not isinstance(self.replication_id, int) or self.replication_id < 0: raise ValueError("replication_id must be a non-negative integer")
    def to_dict(self) -> dict[str, Any]: return {"experiment_id": self.experiment_id, "run_id": self.run_id, "episode_id": self.episode_id, "replication_id": self.replication_id, "workload_id": self.workload_id, "variant_id": self.variant_id}
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EpisodeIdentity": return cls(**{key: value.get(key) for key in ("experiment_id", "run_id", "episode_id", "replication_id", "workload_id", "variant_id")})


class EvidenceStage(str, Enum):
    PRE_FINAL = "pre_final"; FINAL_ARTIFACT = "final_artifact"; TERMINAL_LABEL = "terminal_label"


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str; event_id: str | None = None; artifact_uri: str | None = None; metric_name: str | None = None; observed_value: float | None = None; threshold: float | None = None; stage: EvidenceStage = EvidenceStage.PRE_FINAL
    def __post_init__(self) -> None:
        _nonempty("evidence_id", self.evidence_id)
        if self.stage is EvidenceStage.PRE_FINAL and self.artifact_uri and any(token in self.artifact_uri.lower() for token in ("final", "label")):
            raise ValueError("pre_final evidence cannot reference a final artifact or terminal label")
        if self.observed_value is not None and not isinstance(self.observed_value, (int, float)): raise ValueError("observed_value must be numeric")
        if self.threshold is not None and not isinstance(self.threshold, (int, float)): raise ValueError("threshold must be numeric")
    def to_dict(self) -> dict[str, Any]: return {"evidence_id": self.evidence_id, "event_id": self.event_id, "artifact_uri": self.artifact_uri, "metric_name": self.metric_name, "observed_value": self.observed_value, "threshold": self.threshold, "stage": self.stage.value}
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvidenceReference": return cls(**{**dict(value), "stage": EvidenceStage(value.get("stage", EvidenceStage.PRE_FINAL))})


@dataclass(frozen=True)
class Evidence:
    """v0.1 compatibility evidence adapter."""
    kind: str; subject: str; observed: Any = None; expected: Any = None; comparator: str | None = None; source: str | None = None
    def to_dict(self) -> dict[str, Any]: return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass(frozen=True)
class DecisionReason:
    code: str; message: str; evidence: tuple[Evidence | EvidenceReference, ...] = ()
    def __post_init__(self) -> None: _nonempty("reason code", self.code); _nonempty("reason message", self.message)
    def to_dict(self) -> dict[str, Any]: return {"code": self.code, "message": self.message, "evidence": [item.to_dict() for item in self.evidence]}


@dataclass(frozen=True, init=False)
class GateDecision:
    decision: Decision; risk_score: float | None; confidence: float | None; checkpoint: str; reasons: tuple[DecisionReason, ...]; evidence: tuple[EvidenceReference, ...]; threshold_version: str; _legacy: bool = field(compare=False, repr=False)
    def __init__(self, decision: Decision | None = None, risk_score: float | None = None, confidence: float | None = None, checkpoint: str = "gate.decided", reasons: tuple[DecisionReason, ...] = (), evidence: tuple[EvidenceReference, ...] = (), threshold_version: str = "legacy", *, outcome: DecisionOutcome | None = None) -> None:
        # Preserve the compact v0.1 positional form GateDecision("fail", reasons)
        # while exposing the explicit v2 fields to new callers.
        if decision in ("pass", "fail") and isinstance(risk_score, (tuple, list)) and not reasons:
            reasons = tuple(risk_score)
            risk_score = None
        legacy = outcome is not None or decision in ("pass", "fail")
        if outcome is None and decision in ("pass", "fail"): outcome, decision = decision, None  # type: ignore[assignment]
        if outcome is not None:
            if outcome not in ("pass", "fail"): raise ValueError("outcome must be 'pass' or 'fail'")
            if outcome == "pass" and reasons: raise ValueError("a passed decision cannot include reasons")
            if outcome == "fail" and not reasons: raise ValueError("a failed decision requires at least one reason")
            decision = "approve" if outcome == "pass" else "block"
        if decision not in ("approve", "warn", "request_clarification", "block"): raise ValueError("invalid gate decision")
        if decision != "approve" and not reasons: raise ValueError("non-approval decisions require at least one reason")
        for name, score in (("risk_score", risk_score), ("confidence", confidence)):
            if score is not None and (not isinstance(score, (int, float)) or not 0 <= score <= 1): raise ValueError(f"{name} must be between 0 and 1")
        _nonempty("checkpoint", checkpoint); _nonempty("threshold_version", threshold_version)
        object.__setattr__(self, "decision", decision); object.__setattr__(self, "risk_score", risk_score); object.__setattr__(self, "confidence", confidence); object.__setattr__(self, "checkpoint", checkpoint); object.__setattr__(self, "reasons", tuple(reasons)); object.__setattr__(self, "evidence", tuple(evidence)); object.__setattr__(self, "threshold_version", threshold_version); object.__setattr__(self, "_legacy", legacy)
    @classmethod
    def passed(cls) -> "GateDecision": return cls(outcome="pass")
    @classmethod
    def failed(cls, *reasons: DecisionReason) -> "GateDecision": return cls(outcome="fail", reasons=tuple(reasons))
    @property
    def outcome(self) -> DecisionOutcome: return "pass" if self.decision == "approve" else "fail"
    @property
    def exit_code(self) -> int: return 0 if self.decision == "approve" else 1
    def to_dict(self) -> dict[str, Any]:
        if self._legacy: return {"outcome": self.outcome, "reasons": [r.to_dict() for r in self.reasons]}
        return {"decision": self.decision, "risk_score": self.risk_score, "confidence": self.confidence, "checkpoint": self.checkpoint, "reasons": [r.to_dict() for r in self.reasons], "evidence": [e.to_dict() for e in self.evidence], "threshold_version": self.threshold_version}
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GateDecision":
        reasons = tuple(DecisionReason(str(r["code"]), str(r["message"]), tuple(EvidenceReference.from_dict(x) if "evidence_id" in x else Evidence(**x) for x in r.get("evidence", ()))) for r in value.get("reasons", ()))
        if "outcome" in value: return cls(outcome=str(value["outcome"]), reasons=reasons)
        return cls(decision=str(value["decision"]), risk_score=value.get("risk_score"), confidence=value.get("confidence"), checkpoint=str(value["checkpoint"]), reasons=reasons, evidence=tuple(EvidenceReference.from_dict(x) for x in value.get("evidence", ())), threshold_version=str(value["threshold_version"]))


@dataclass(frozen=True, init=False)
class RunManifest:
    schema_version: str; experiment_id: str; run_id: str; created_at: str; git_sha: str; harness_name: str; harness_version: str; dataset_id: str; dataset_hash: str; configuration_hash: str; model_provider: str; model_name: str; model_version: str; random_seed: int; replication_count: int; environment: Mapping[str, Any]; _legacy: bool = field(compare=False, repr=False); completed_at: str | None = None; artifacts: Mapping[str, str] = field(default_factory=dict); metadata: Mapping[str, Any] = field(default_factory=dict); configuration: Mapping[str, Any] = field(default_factory=dict); labels: Mapping[str, str] = field(default_factory=dict); decision: GateDecision | None = None; identifiers: Mapping[str, str] = field(default_factory=dict); hashes: Mapping[str, str] = field(default_factory=dict)
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        v2_names = ("schema_version", "experiment_id", "run_id", "created_at", "git_sha", "harness_name", "harness_version", "dataset_id", "dataset_hash", "configuration_hash", "model_provider", "model_name", "model_version", "random_seed", "replication_count", "environment")
        legacy = "started_at" in kwargs or (args and not (isinstance(args[0], str) and args[0].count(".") == 2))
        if legacy:
            data = dict(kwargs); data.update(dict(zip(("run_id", "started_at", "decision", "identifiers", "hashes"), args)))
            if isinstance(data.get("decision"), Mapping): data["decision"] = GateDecision.from_dict(data["decision"])
            identifiers, hashes = dict(data.get("identifiers") or {}), dict(data.get("hashes") or {})
            raw_artifacts = data.get("artifacts") or {}
            artifacts = {} if isinstance(raw_artifacts, str) else dict(raw_artifacts)
            values = {"schema_version": str(data.get("schema_version", "arp/v1")), "experiment_id": identifiers.get("experiment_id", "legacy"), "run_id": data["run_id"], "created_at": data["started_at"], "git_sha": hashes.get("git_sha", "unknown"), "harness_name": identifiers.get("harness_name", "legacy"), "harness_version": identifiers.get("harness_version", "unknown"), "dataset_id": identifiers.get("dataset_id", "unknown"), "dataset_hash": hashes.get("dataset", next(iter(hashes.values()), "unknown")), "configuration_hash": hashes.get("configuration", "unknown"), "model_provider": "unknown", "model_name": "unknown", "model_version": "unknown", "random_seed": 0, "replication_count": 1, "environment": {}, "decision": data["decision"], "identifiers": identifiers, "hashes": hashes, "completed_at": data.get("completed_at"), "artifacts": artifacts, "metadata": dict(data.get("metadata") or {}), "configuration": dict(data.get("configuration") or {}), "labels": dict(data.get("labels") or {})}
        else:
            values = dict(zip(v2_names, args)); values.update(kwargs); values.setdefault("completed_at", None); values.setdefault("artifacts", {}); values.setdefault("metadata", {}); values.setdefault("configuration", {}); values.setdefault("labels", {}); values.setdefault("decision", None); values.setdefault("identifiers", {}); values.setdefault("hashes", {})
        for name in v2_names[:13]: _nonempty(name, str(values[name]))
        if legacy and not values["identifiers"]:
            raise ValueError("identifiers are required for legacy manifests")
        _schema_version(values["schema_version"])
        if not isinstance(values["random_seed"], int): raise ValueError("random_seed must be an integer")
        if not isinstance(values["replication_count"], int) or values["replication_count"] < 1: raise ValueError("replication_count must be positive")
        for name, value in values.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "_legacy", legacy)
    def to_dict(self) -> dict[str, Any]:
        if self._legacy:
            value = {"schema_version": self.schema_version, "run_id": self.run_id, "started_at": self.created_at, "decision": self.decision.to_dict() if self.decision else {}, "identifiers": dict(self.identifiers), "hashes": dict(self.hashes), "artifacts": dict(self.artifacts), "metadata": dict(self.metadata), "configuration": dict(self.configuration)}
            if self.completed_at: value["completed_at"] = self.completed_at
            if self.labels: value["labels"] = dict(self.labels)
            return value
        payload = {k: (dict(v) if isinstance(v, Mapping) else v) for k, v in self.__dict__.items() if k != "_legacy" and v is not None}
        if isinstance(self.decision, GateDecision):
            payload["decision"] = self.decision.to_dict()
        return payload
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RunManifest": return cls(**dict(value))
