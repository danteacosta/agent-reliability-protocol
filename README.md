# Agent Reliability Protocol

`agent-reliability-protocol` (ARP) is a dependency-free, neutral contract for
recording reproducible runs, episode lifecycle events, evidence, and gate
decisions across agent systems. Version `2.0.6` is the current package release
on the stable ARP 2.0.5 wire schema:
new records carry a SemVer `schema_version`; v0.1 manifests/events remain
readable through compatibility adapters.

SemVer policy: patches correct behavior without structural change; minors add
optional fields; majors remove, rename, or alter the meaning of a field. The
v2 schemas cover episode identities, manifests, provenance events, decisions,
and evidence references. `adapt_manifest_v2` turns a readable v0.1 manifest
into the canonical representation; `upgrade_manifest` preserves the v0.1
normal form for old consumers.

```python
from agent_reliability_protocol import EpisodeIdentity, RunManifest

identity = EpisodeIdentity("experiment-1", "run-123", "episode-1", 0, "workload-1")
manifest = RunManifest("2.0.5", "experiment-1", "run-123", "2026-07-30T00:00:00+00:00", "abc123", "harness", "1.0.0", "dataset", "sha256:...", "sha256:...", "provider", "model", "version", 7, 1, {"runtime": "ci"})
```

Validate a JSON document without network access:

```console
arp-contract-test check --kind manifest --input manifest.json
arp-contract-test check --run-directory ./runs/example
```

The package intentionally contains no application, model, provider, or harness
imports. Core fields may not contain domain terms such as `smell`, `oracle_spec`,
`retrieval_hit`, `mrr`, or `mutation_score`. Capture policy is explicit:
`none`, `metadata`, `redacted`, or `full`; `redacted` removes prompts,
artifacts, tool arguments, retrieved content, PII, and secrets.
