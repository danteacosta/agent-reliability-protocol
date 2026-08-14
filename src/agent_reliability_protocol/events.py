"""Lifecycle envelope and semantic-preserving local JSONL exporter."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
import re

LIFECYCLE_CHECKPOINTS = frozenset({"episode.started", "input.received", "interpretation.completed", "plan.completed", "execution.started", "tool.completed", "retrieval.completed", "artifact.completed", "evaluation.completed", "gate.decided", "episode.completed"})
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
EVENT_TYPES = LIFECYCLE_CHECKPOINTS  # v2 public alias

# Thesis checkpoints are a small, domain-neutral ordering contract.  Other
# lifecycle events remain valid and may occur between these milestones.
THESIS_CHECKPOINT_ORDER = (
    "input.received",              # T0
    "interpretation.completed",    # T1
    "plan.completed",              # T2
    "execution.started",           # T3
)
_THESIS_CHECKPOINT_RANK = {name: rank for rank, name in enumerate(THESIS_CHECKPOINT_ORDER)}

@dataclass(frozen=True, init=False)
class LifecycleEvent:
    event_id: str; schema_version: str; experiment_id: str; run_id: str; episode_id: str; replication_id: int; sequence_number: int; checkpoint: str; event_type: str; started_at: str; ended_at: str; attributes: Mapping[str, Any] = field(default_factory=dict); content_reference: str | None = None; parent_event_id: str | None = None; extensions: Mapping[str, Any] = field(default_factory=dict); _legacy: bool = field(compare=False, repr=False)
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        legacy = "type" in kwargs or (len(args) == 4 and "event_id" not in kwargs)
        if legacy:
            data = dict(kwargs); data.update(dict(zip(("type", "run_id", "occurred_at", "data"), args)))
            event_type = str(data["type"])
            # known v0.1 events are admitted as opaque legacy values.
            values = dict(event_id=f"legacy:{data['run_id']}:{event_type}:{data['occurred_at']}", schema_version="arp/v1", experiment_id="legacy", run_id=str(data["run_id"]), episode_id="legacy", replication_id=0, sequence_number=0, checkpoint=event_type, event_type=event_type, started_at=str(data["occurred_at"]), ended_at=str(data["occurred_at"]), attributes=dict(data.get("data") or {}), content_reference=None, parent_event_id=None, extensions={})
        else:
            names = ("event_id", "schema_version", "experiment_id", "run_id", "episode_id", "replication_id", "sequence_number", "checkpoint", "event_type", "started_at", "ended_at", "attributes", "content_reference", "parent_event_id", "extensions")
            values = dict(zip(names, args)); values.update(kwargs); values.setdefault("attributes", {}); values.setdefault("content_reference", None); values.setdefault("parent_event_id", None); values.setdefault("extensions", {})
        for name in ("event_id", "schema_version", "experiment_id", "run_id", "episode_id", "checkpoint", "event_type", "started_at", "ended_at"):
            if not isinstance(values[name], str) or not values[name].strip(): raise ValueError(f"{name} must be a non-empty string")
        if not legacy and not _SEMVER.fullmatch(values["schema_version"]): raise ValueError("schema_version must be SemVer")
        if not isinstance(values["replication_id"], int) or values["replication_id"] < 0: raise ValueError("replication_id must be non-negative")
        if not isinstance(values["sequence_number"], int) or values["sequence_number"] < 0: raise ValueError("sequence_number must be non-negative")
        if not isinstance(values["attributes"], Mapping): raise ValueError("attributes must be an object")
        if not isinstance(values["extensions"], Mapping): raise ValueError("extensions must be an object")
        for name in ("content_reference", "parent_event_id"):
            if values[name] is not None and (not isinstance(values[name], str) or not values[name].strip()):
                raise ValueError(f"{name} must be a non-empty string when provided")
        if not legacy and (values["checkpoint"] not in LIFECYCLE_CHECKPOINTS or values["event_type"] not in LIFECYCLE_CHECKPOINTS): raise ValueError("unsupported lifecycle checkpoint or event_type")
        if not legacy and values["checkpoint"] != values["event_type"]: raise ValueError("checkpoint and event_type must match")
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
        return {"event_id": self.event_id, "schema_version": self.schema_version, "experiment_id": self.experiment_id, "run_id": self.run_id, "episode_id": self.episode_id, "replication_id": self.replication_id, "sequence_number": self.sequence_number, "checkpoint": self.checkpoint, "event_type": self.event_type, "started_at": self.started_at, "ended_at": self.ended_at, "attributes": dict(self.attributes), "content_reference": self.content_reference, "parent_event_id": self.parent_event_id, "extensions": dict(self.extensions)}
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LifecycleEvent":
        payload = dict(value)
        if "type" not in payload:
            required = {"event_id", "schema_version", "experiment_id", "run_id", "episode_id", "replication_id", "sequence_number", "checkpoint", "event_type", "started_at", "ended_at", "attributes", "content_reference", "parent_event_id"}
            missing = sorted(required.difference(payload))
            if missing:
                raise ValueError("lifecycle envelope is missing required fields: " + ", ".join(missing))
        return cls(**payload)


def validate_lifecycle_sequence(events: Iterable[LifecycleEvent | Mapping[str, Any]]) -> None:
    """Validate the ordered identity envelope shared by ARP event producers.

    A sequence is scoped to one run, episode, and replication.  Sequence
    numbers may start at zero or one for compatibility, then must advance by
    exactly one.  The thesis T0--T3 checkpoints must appear in canonical order;
    the remaining ARP checkpoints are legal at any point and do not alter that
    ordering.  Legacy v1 events are intentionally accepted unchanged.

    ``ValueError`` is raised on the first invalid envelope so producers cannot
    silently emit a partial or ambiguous lifecycle record.
    """
    parsed = [event if isinstance(event, LifecycleEvent) else LifecycleEvent.from_dict(event) for event in events]
    if not parsed:
        raise ValueError("lifecycle sequence must contain at least one event")
    if all(event._legacy for event in parsed):
        return

    first = parsed[0]
    if first.sequence_number not in (0, 1):
        raise ValueError("sequence_number must start at 0 or 1")
    identity = (first.experiment_id, first.run_id, first.episode_id, first.replication_id)
    seen_ids: set[str] = set()
    previous_sequence = first.sequence_number - 1
    previous_rank: int | None = None
    for event in parsed:
        if event._legacy:
            raise ValueError("legacy and ARP v2 lifecycle events cannot share a sequence")
        if event.event_id in seen_ids:
            raise ValueError("duplicate event_id in lifecycle sequence")
        seen_ids.add(event.event_id)
        event_identity = (event.experiment_id, event.run_id, event.episode_id, event.replication_id)
        if event_identity != identity:
            raise ValueError("lifecycle event identity does not match sequence identity")
        if event.sequence_number != previous_sequence + 1:
            raise ValueError("sequence_number is not ordered")
        previous_sequence = event.sequence_number
        rank = _THESIS_CHECKPOINT_RANK.get(event.checkpoint)
        if rank is not None and previous_rank is not None and rank < previous_rank:
            raise ValueError("thesis checkpoints are not ordered (T0-T3)")
        if rank is not None:
            previous_rank = rank

class JsonlExporter:
    def __init__(self, path: Path | str) -> None: self.path = Path(path)
    def export(self, event: LifecycleEvent) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True); payload = event.to_dict()
        with self.path.open("a", encoding="utf-8") as handle: handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
        return payload

def new_event(event_type: str, run_id: str, data: Mapping[str, Any] | None = None) -> LifecycleEvent:
    now = datetime.now(timezone.utc).isoformat()
    return LifecycleEvent(type=event_type, run_id=run_id, occurred_at=now, data=dict(data or {}))
