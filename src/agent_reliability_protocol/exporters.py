"""Dependency-free adapters to common telemetry record shapes."""

from __future__ import annotations

from typing import Any

from agent_reliability_protocol.events import LifecycleEvent


class OpenTelemetryExporter:
    """Return OTel-compatible log/span input; callers own SDK emission."""
    def export(self, event: LifecycleEvent) -> dict[str, Any]:
        return {"name": f"arp.{event.type}", "timestamp": event.occurred_at, "attributes": {"arp.run_id": event.run_id, "arp.event_type": event.type, **{f"arp.data.{key}": value for key, value in event.data.items()}}}


class OpenInferenceExporter:
    """Return OpenInference-compatible span input without requiring its SDK."""
    def export(self, event: LifecycleEvent) -> dict[str, Any]:
        record = OpenTelemetryExporter().export(event)
        record["attributes"]["openinference.span.kind"] = "CHAIN"
        return record
