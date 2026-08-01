"""Guardrails preventing application-specific contracts from leaking into ARP."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import Any


_DOMAIN_KEYS = {"retrieval_metrics", "rag_metrics", "embedding_model", "golden_dataset", "smell", "oracle_spec", "trace_link", "retrieval_hit", "mrr", "groundedness", "mutation_score"}
_HARNESS_IMPORT_MARKERS = ("rag_harness", "langchain", "openai", "anthropic", "agent_smell", "oracle_spec", "retrieval_hit", "mutation_score")


def assert_neutral_contract(value: Mapping[str, Any]) -> None:
    violations = _find_domain_keys(value)
    if violations:
        raise ValueError("domain-specific contract keys are not allowed: " + ", ".join(sorted(violations)))


def assert_neutral_source(package_root: Path | str) -> None:
    """Fail if a shared-contract source tree imports known harness/provider APIs."""
    offenders: list[str] = []
    for path in Path(package_root).rglob("*.py"):
        if path.name == "neutral.py":
            continue  # This module defines the banlist; it is not contract surface.
        text = path.read_text(encoding="utf-8").lower()
        if any(marker in text for marker in _HARNESS_IMPORT_MARKERS):
            offenders.append(str(path))
    if offenders:
        raise ValueError("harness-specific source markers are not allowed: " + ", ".join(offenders))


def assert_no_protocol_next_dependency(package_root: Path | str) -> None:
    """Guard producer code from importing the consumer-side protocol_next API.

    Import syntax is inspected with ``ast`` instead of searching text, so
    documentation and compatibility strings such as ``protocol_next/v1`` do
    not create false positives.  This is intentionally runtime-callable by
    CI or a producer startup check and has no dependency on protocol_next.
    """
    offenders: list[str] = []
    for path in Path(package_root).rglob("*.py"):
        if path.name == "neutral.py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            raise ValueError(f"cannot inspect producer source {path}: {exc}") from exc
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            if any(name == "protocol_next" or name.startswith("protocol_next.") for name in imported):
                offenders.append(str(path))
                break
    if offenders:
        raise ValueError("protocol_next must not be a producer dependency: " + ", ".join(offenders))


def assert_protocol_next_independent(package_root: Path | str) -> None:
    """Compatibility alias for :func:`assert_no_protocol_next_dependency`."""
    assert_no_protocol_next_dependency(package_root)


def _find_domain_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        found = {str(key) for key in value if str(key) in _DOMAIN_KEYS}
        for item in value.values(): found.update(_find_domain_keys(item))
        return found
    if isinstance(value, (list, tuple)):
        return set().union(*(_find_domain_keys(item) for item in value)) if value else set()
    return set()
