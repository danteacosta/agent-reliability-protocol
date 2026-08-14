# Agent Reliability Protocol

MIT-licensed. See [LICENSE](LICENSE), [CONTRIBUTING](CONTRIBUTING.md), and
[SECURITY](SECURITY.md). The published v2.0.6 package and tag are immutable;
consumer harnesses pin this release while the ARP 2.0.5 wire contract remains
stable.

`agent-reliability-protocol` (ARP) is a dependency-free, neutral contract for
recording reproducible runs, episode lifecycle events, evidence, and gate
decisions across agent systems. The current development line is ARP `2.1.0`:
it adds generic scalar claims, pending gate requests, capture policy, profiles,
and namespaced extensions while preserving the ARP 2.0.5 wire contract:
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

The test environment is pinned in [constraints.txt](constraints.txt). The
published v2.0.6 package remains MIT-licensed and is not retagged.

The package intentionally contains no application, model, provider, or harness
imports. Core fields may not contain domain terms such as `smell`, `oracle_spec`,
`retrieval_hit`, `mrr`, or `mutation_score`; those may appear only inside an
opaque, namespaced `extensions` payload. Capture policy is explicit:
`none`, `metadata`, `redacted`, or `full`; `redacted` removes prompts,
artifacts, tool arguments, retrieved content, PII, and secrets.

The merge-gated delivery integration is documented in
[docs/profiles/software-delivery-v1.md](docs/profiles/software-delivery-v1.md).
The final control-plane specification is documented in
[docs/merge-gated-delivery-control-plane-spec.md](docs/merge-gated-delivery-control-plane-spec.md).
