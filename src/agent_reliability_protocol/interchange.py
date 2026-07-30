"""Portable contract validation, compatibility, and safe JSON exports."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from agent_reliability_protocol.contracts import GateDecision, RunManifest
from agent_reliability_protocol.events import LifecycleEvent

ContractKind = Literal["decision", "event", "manifest"]
_SECRET_MARKERS = ("secret", "token", "password", "authorization", "cookie", "api_key")
_SUPPORTED_MANIFEST_VERSIONS = {"arp/v1", "protocol_next/v1"}


def redact_contract(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): "[REDACTED]" if _sensitive(str(key)) else redact_contract(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_contract(item) for item in value]
    return value


def export_contract(value: Any, path: Path | str, *, redact: bool = True) -> None:
    payload = value.to_dict() if hasattr(value, "to_dict") else value
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(redact_contract(payload) if redact else payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def check_contract(kind: ContractKind, payload: Mapping[str, Any]) -> list[str]:
    try:
        json.dumps(payload, ensure_ascii=True)
        if kind == "decision": GateDecision.from_dict(payload)
        elif kind == "event": LifecycleEvent.from_dict(payload)
        elif kind == "manifest":
            if payload.get("schema_version", "arp/v1") not in _SUPPORTED_MANIFEST_VERSIONS:
                raise ValueError("unsupported manifest schema_version")
            RunManifest.from_dict(payload)
        else: return [f"unknown contract kind: {kind}"]
    except (KeyError, TypeError, ValueError) as exc:
        return [str(exc)]
    return []


def upgrade_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    result = RunManifest.from_dict(value).to_dict()
    result["schema_version"] = "arp/v1"
    return result


def _sensitive(key: str) -> bool:
    return any(marker in key.lower().replace("-", "_") for marker in _SECRET_MARKERS)
