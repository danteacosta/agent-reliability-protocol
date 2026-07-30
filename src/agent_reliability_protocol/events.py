"""Neutral JSONL lifecycle event contract."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


EVENT_TYPES = frozenset({"run.started", "input.changed", "work.completed", "gate.decided", "run.completed"})


@dataclass(frozen=True)
class LifecycleEvent:
    type: str
    run_id: str
    occurred_at: str
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in EVENT_TYPES:
            raise ValueError(f"unsupported lifecycle event: {self.type}")
        if not self.run_id.strip():
            raise ValueError("event run_id must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "run_id": self.run_id, "occurred_at": self.occurred_at, "data": dict(self.data)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LifecycleEvent":
        return cls(str(value["type"]), str(value["run_id"]), str(value["occurred_at"]), dict(value.get("data") or {}))


class JsonlExporter:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def export(self, event: LifecycleEvent) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = event.to_dict()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
        return payload


def new_event(event_type: str, run_id: str, data: Mapping[str, Any] | None = None) -> LifecycleEvent:
    return LifecycleEvent(event_type, run_id, datetime.now(timezone.utc).isoformat(), dict(data or {}))
