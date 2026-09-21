"""Malformed research artifacts remain machine-readable validation failures."""
import json
from pathlib import Path

import pytest

from agent_reliability_protocol import check_contract, validate_run_directory
from agent_reliability_protocol.__main__ import main


@pytest.mark.parametrize("payload", [None, [], [1], "text", 3, True])
def test_contract_requires_an_object(payload):
    assert check_contract("manifest", payload) == ["contract must be a JSON object"]


@pytest.mark.parametrize("payload", [None, [], "text", 3, True])
def test_run_manifest_requires_an_object(tmp_path, payload):
    (tmp_path / "manifest.json").write_text(json.dumps(payload))
    errors = validate_run_directory(tmp_path)
    assert errors == ["manifest: contract must be a JSON object"]


@pytest.mark.parametrize("content", [b"{not json", b"\xff", b"null", b"[]"])
def test_cli_reports_invalid_input_as_json(tmp_path, capsys, content):
    path = tmp_path / "input.json"
    path.write_bytes(content)
    assert main(["check", "--kind", "manifest", "--input", str(path)]) == 1
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["valid"] is False
    assert result["errors"]
    assert captured.err == ""
    assert "not json" not in captured.out


def test_cli_reports_missing_input_as_json(tmp_path, capsys):
    assert main(["check", "--kind", "manifest", "--input", str(tmp_path / "absent")]) == 1
    assert json.loads(capsys.readouterr().out)["valid"] is False


@pytest.mark.parametrize("version", ["v1", "v3"])
@pytest.mark.parametrize("payload", [None, [], "text", 3, True])
def test_run_event_requires_object_with_line_context(tmp_path, version, payload):
    root = Path(__file__).resolve().parents[1] / "src/agent_reliability_protocol/fixtures"
    fixture = "run-manifest.json" if version == "v1" else "run-manifest.valid.json"
    (tmp_path / "manifest.json").write_bytes((root / version / fixture).read_bytes())
    (tmp_path / "events.jsonl").write_text(json.dumps(payload) + "\n")
    errors = validate_run_directory(tmp_path)
    assert "events.jsonl:1: contract must be a JSON object" in errors


@pytest.mark.parametrize("file_name", ["manifest.json", "events.jsonl"])
def test_directory_reports_non_utf8_input(tmp_path, file_name):
    root = Path(__file__).resolve().parents[1] / "src/agent_reliability_protocol/fixtures/v3"
    (tmp_path / "manifest.json").write_bytes((root / "run-manifest.valid.json").read_bytes())
    (tmp_path / file_name).write_bytes(b"\xff")
    errors = validate_run_directory(tmp_path)
    assert errors and file_name in errors[0]
