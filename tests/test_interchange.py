from __future__ import annotations

import json
from pathlib import Path

from agent_reliability_protocol import check_contract, export_contract, redact_contract
from agent_reliability_protocol.__main__ import main


def test_fixtures_validate_and_schema_files_are_portable() -> None:
    package_root = Path(__file__).resolve().parents[1] / "src" / "agent_reliability_protocol"
    fixtures = package_root / "fixtures" / "v1"
    for kind, filename in (("decision", "decision-fail.json"), ("event", "lifecycle-event.json"), ("manifest", "run-manifest.json")):
        assert check_contract(kind, json.loads((fixtures / filename).read_text(encoding="utf-8"))) == []
    for schema in (package_root / "schemas").glob("*.schema.json"):
        assert json.loads(schema.read_text(encoding="utf-8"))["$schema"].endswith("schema")


def test_export_redacts_sensitive_fields(tmp_path: Path) -> None:
    original = {"token": "secret", "nested": {"authorization": "Bearer secret"}, "safe": "yes"}
    output = tmp_path / "export.json"
    export_contract(original, output)

    assert original["token"] == "secret"
    assert redact_contract(original)["nested"]["authorization"] == "[REDACTED]"
    assert json.loads(output.read_text(encoding="utf-8"))["token"] == "[REDACTED]"


def test_contract_cli_returns_success_for_portable_fixture(capsys) -> None:
    fixture = Path(__file__).resolve().parents[1] / "src" / "agent_reliability_protocol" / "fixtures" / "v1" / "run-manifest.json"
    assert main(["check", "--kind", "manifest", "--input", str(fixture)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True
