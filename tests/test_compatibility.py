from __future__ import annotations

from agent_reliability_protocol import check_contract, upgrade_manifest


def test_protocol_next_manifest_remains_compatible_without_importing_a_harness() -> None:
    legacy = {
        "schema_version": "protocol_next/v1",
        "run_id": "legacy-run",
        "started_at": "2026-07-30T00:00:00+00:00",
        "decision": {"outcome": "pass"},
        "identifiers": {"build": "legacy-build"},
        "hashes": {"input": "legacy-hash"},
    }

    upgraded = upgrade_manifest(legacy)

    assert upgraded["schema_version"] == "arp/v1"
    assert check_contract("manifest", legacy) == []
