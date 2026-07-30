"""Neutral data contracts for agent reliability decisions and runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Mapping


DecisionOutcome = Literal["pass", "fail"]


@dataclass(frozen=True)
class Evidence:
    kind: str
    subject: str
    observed: Any = None
    expected: Any = None
    comparator: str | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class DecisionReason:
    code: str
    message: str
    evidence: tuple[Evidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "evidence": [item.to_dict() for item in self.evidence]}


@dataclass(frozen=True)
class GateDecision:
    outcome: DecisionOutcome
    reasons: tuple[DecisionReason, ...] = ()

    def __post_init__(self) -> None:
        if self.outcome not in ("pass", "fail"):
            raise ValueError("outcome must be 'pass' or 'fail'")
        if self.outcome == "pass" and self.reasons:
            raise ValueError("a passed decision cannot include reasons")
        if self.outcome == "fail" and not self.reasons:
            raise ValueError("a failed decision requires at least one reason")

    @classmethod
    def passed(cls) -> "GateDecision":
        return cls("pass")

    @classmethod
    def failed(cls, *reasons: DecisionReason) -> "GateDecision":
        return cls("fail", tuple(reasons))

    @property
    def exit_code(self) -> int:
        return 0 if self.outcome == "pass" else 1

    def to_dict(self) -> dict[str, Any]:
        return {"outcome": self.outcome, "reasons": [reason.to_dict() for reason in self.reasons]}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GateDecision":
        return cls(
            str(value["outcome"]),
            tuple(
                DecisionReason(
                    str(reason["code"]), str(reason["message"]),
                    tuple(Evidence(**dict(item)) for item in reason.get("evidence", [])),
                )
                for reason in value.get("reasons", [])
            ),
        )


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    started_at: str
    decision: GateDecision
    identifiers: Mapping[str, str]
    hashes: Mapping[str, str]
    schema_version: str = "arp/v1"
    completed_at: str | None = None
    artifacts: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    configuration: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise ValueError("run_id must be a non-empty string")
        _validate_named_values("identifiers", self.identifiers)
        _validate_named_values("hashes", self.hashes)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "decision": self.decision.to_dict(),
            "identifiers": dict(self.identifiers), "hashes": dict(self.hashes),
            "artifacts": dict(self.artifacts), "metadata": dict(self.metadata),
            "configuration": dict(self.configuration),
        }
        if self.completed_at is not None:
            payload["completed_at"] = self.completed_at
        return payload

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RunManifest":
        return cls(
            run_id=str(value["run_id"]), started_at=str(value["started_at"]),
            decision=GateDecision.from_dict(value["decision"]),
            identifiers=dict(value["identifiers"]), hashes=dict(value["hashes"]),
            schema_version=str(value.get("schema_version", "arp/v1")), completed_at=value.get("completed_at"),
            artifacts=dict(value.get("artifacts") or {}), metadata=dict(value.get("metadata") or {}),
            configuration=dict(value.get("configuration") or {}),
        )


def _validate_named_values(name: str, values: Mapping[str, str]) -> None:
    if not values:
        raise ValueError(f"{name} must contain at least one entry")
    if any(not isinstance(key, str) or not key.strip() for key in values):
        raise ValueError(f"{name} keys must be non-empty strings")
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise ValueError(f"{name} values must be non-empty strings")
