from __future__ import annotations

import json
from pathlib import Path

from agent_reliability_protocol import JsonlExporter, LifecycleEvent, OpenInferenceExporter, OpenTelemetryExporter


def test_exporters_produce_portable_jsonl_otel_and_openinference_records(tmp_path: Path) -> None:
    event = LifecycleEvent("gate.decided", "run-123", "2026-07-30T00:00:00+00:00", {"outcome": "pass"})
    path = tmp_path / "events.jsonl"
    JsonlExporter(path).export(event)

    otel = OpenTelemetryExporter().export(event)
    openinference = OpenInferenceExporter().export(event)

    assert json.loads(path.read_text(encoding="utf-8"))["type"] == "gate.decided"
    assert otel["name"] == "arp.gate.decided"
    assert otel["attributes"]["arp.run_id"] == "run-123"
    assert openinference["attributes"]["openinference.span.kind"] == "CHAIN"
