"""Lossless adapters to common telemetry record shapes."""
from __future__ import annotations
from typing import Any
from agent_reliability_protocol.events import LifecycleEvent

class OpenTelemetryExporter:
    def export(self, event: LifecycleEvent) -> dict[str, Any]:
        canonical = event.to_dict()
        return {"name": f"arp.{event.event_type}", "timestamp": event.ended_at, "arp.event": canonical, "attributes": {"arp.run_id": event.run_id, "arp.event_type": event.event_type, "arp.event": canonical}}

class OpenInferenceExporter:
    def export(self, event: LifecycleEvent) -> dict[str, Any]:
        record = OpenTelemetryExporter().export(event); record["attributes"]["openinference.span.kind"] = "CHAIN"; return record
