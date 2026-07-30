# Agent Reliability Protocol

`agent-reliability-protocol` (ARP) is a dependency-free, neutral contract for
recording a run manifest, lifecycle events, and gate decisions across agent
systems. Version `0.1.0` provides JSON-round-trippable dataclasses, Draft
2020-12 schemas, safe export/redaction, JSONL/OTel/OpenInference-shaped
exporters, compatibility helpers, and a contract CLI.

```python
from agent_reliability_protocol import GateDecision, RunManifest

manifest = RunManifest(
    run_id="run-123",
    started_at="2026-07-30T00:00:00+00:00",
    decision=GateDecision.passed(),
    identifiers={"build": "build-123"},
    hashes={"input": "sha256:..."},
)
```

Validate a JSON document without network access:

```console
arp-contract check --kind manifest --input manifest.json
```

The package intentionally contains no application, model, provider, or harness
imports. Domain-specific data belongs in `metadata`, `configuration`, or event
`data`.
