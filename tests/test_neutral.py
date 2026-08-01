from __future__ import annotations

import pytest

from agent_reliability_protocol import assert_neutral_contract, assert_neutral_source, assert_no_protocol_next_dependency


def test_neutral_guard_allows_generic_contracts_and_rejects_harness_shape() -> None:
    assert_neutral_contract({"run_id": "run-123", "metadata": {"team": "platform"}})
    with pytest.raises(ValueError, match="domain-specific"):
        assert_neutral_contract({"retrieval_metrics": {"recall@5": 1.0}})
    with pytest.raises(ValueError, match="domain-specific"):
        assert_neutral_contract({"oracle_spec": "consumer-only"})


def test_neutral_source_guard_rejects_harness_import_markers(tmp_path) -> None:
    source = tmp_path / "adapter.py"
    source.write_text("import langchain\n", encoding="utf-8")
    with pytest.raises(ValueError, match="harness-specific"):
        assert_neutral_source(tmp_path)


def test_protocol_source_remains_domain_neutral() -> None:
    package_root = __import__("agent_reliability_protocol").__path__[0]
    assert_neutral_source(package_root)


def test_protocol_next_is_not_a_producer_dependency(tmp_path) -> None:
    producer = tmp_path / "producer.py"
    producer.write_text("from protocol_next import emit\n", encoding="utf-8")
    with pytest.raises(ValueError, match="protocol_next"):
        assert_no_protocol_next_dependency(tmp_path)
