"""Lifecycle envelope and semantic-preserving local JSONL exporter."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import re

LIFECYCLE_CHECKPOINTS = frozenset({"episode.started", "input.received", "interpretation.completed", "plan.completed", "execution.started", "tool.completed", "retrieval.completed", "artifact.completed", "evaluation.completed", "gate.decided", "episode.completed"})
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
EVENT_TYPES = LIFECYCLE_CHECKPOINTS  # v2 public alias

@dataclass(frozen=True, init=False)
class LifecycleEvent:
    event_id: str; schema_version: str; experiment_id: str; run_id: str; episode_id: str; replication_id: int; sequence_number: int; checkpoint: str; event_type: str; started_at: str; ended_at: str; attributes: Mapping[str, Any] = field(default_factory=dict); content_reference: str | None = None; parent_event_id: str | None = None; _legacy: bool = field(compare=False, repr=False)
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        legacy = "type" in kwargs or (len(args) == 4 and "event_id" not in kwargs)
        if legacy:
            data = dict(kwargs); data.update(dict(zip(("type", "run_id", "occurred_at", "data"), args)))
            event_type = str(data["type"])
            # known v0.1 events are admitted as opaque legacy values.
            values = dict(event_id=f"legacy:{data['run_id']}:{event_type}:{data['occurred_at']}", schema_version="arp/v1", experiment_id="legacy", run_id=str(data["run_id"]), episode_id="legacy", replication_id=0, sequence_number=0, checkpoint=event_type, event_type=event_type, started_at=str(data["occurred_at"]), ended_at=str(data["occurred_at"]), attributes=dict(data.get("data") or {}), content_reference=None, parent_event_id=None)
        else:
            names = ("event_id", "schema_version", "experiment_id", "run_id", "episode_id", "replication_id", "sequence_number", "checkpoint", "event_type", "started_at", "ended_at", "attributes", "content_reference", "parent_event_id")
            values = dict(zip(names, args)); values.update(kwargs); values.setdefault("attributes", {}); values.setdefault("content_reference", None); values.setdefault("parent_event_id", None)
        for name in ("event_id", "schema_version", "experiment_id", "run_id", "episode_id", "checkpoint", "event_type", "started_at", "ended_at"):
            if not isinstance(values[name], str) or not values[name].strip(): raise ValueError(f"{name} must be a non-empty string")
        if not legacy and not _SEMVER.fullmatch(values["schema_version"]): raise ValueError("schema_version must be SemVer")
        if not isinstance(values["replication_id"], int) or values["replication_id"] < 0: raise ValueError("replication_id must be non-negative")
        if not isinstance(values["sequence_number"], int) or values["sequence_number"] < 0: raise ValueError("sequence_number must be non-negative")
        if not legacy and (values["checkpoint"] not in LIFECYCLE_CHECKPOINTS or values["event_type"] not in LIFECYCLE_CHECKPOINTS): raise ValueError("unsupported lifecycle checkpoint or event_type")
        for name, value in values.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "_legacy", legacy)
    @property
    def type(self) -> str: return self.event_type
    @property
    def occurred_at(self) -> str: return self.ended_at
    @property
    def data(self) -> Mapping[str, Any]: return self.attributes
    def to_dict(self) -> dict[str, Any]:
        if self._legacy: return {"type": self.event_type, "run_id": self.run_id, "occurred_at": self.ended_at, "data": dict(self.attributes)}
        return {"event_id": self.event_id, "schema_version": self.schema_version, "experiment_id": self.experiment_id, "run_id": self.run_id, "episode_id": self.episode_id, "replication_id": self.replication_id, "sequence_number": self.sequence_number, "checkpoint": self.checkpoint, "event_type": self.event_type, "started_at": self.started_at, "ended_at": self.ended_at, "attributes": dict(self.attributes), "content_reference": self.content_reference, "parent_event_id": self.parent_event_id}
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LifecycleEvent": return cls(**dict(value))

class JsonlExporter:
    def __init__(self, path: Path | str) -> None: self.path = Path(path)
    def export(self, event: LifecycleEvent) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True); payload = event.to_dict()
        with self.path.open("a", encoding="utf-8") as handle: handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
        return payload

def new_event(event_type: str, run_id: str, data: Mapping[str, Any] | None = None) -> LifecycleEvent:
    now = datetime.now(timezone.utc).isoformat()
    return LifecycleEvent(type=event_type, run_id=run_id, occurred_at=now, data=dict(data or {}))
