# Agent Reliability Protocol

MIT-licensed. See [LICENSE](LICENSE), [CONTRIBUTING](CONTRIBUTING.md), and
[SECURITY](SECURITY.md). The published v2.0.6 package and tag are immutable;
consumer harnesses pin this release while the ARP 2.0.5 wire contract remains
stable.

`agent-reliability-protocol` (ARP) is a dependency-free, neutral contract for
recording reproducible runs, episode lifecycle events, evidence, and gate
decisions across agent systems. The current release line is ARP `3.0.0`:
new producers emit a generic v3 wire contract while explicit adapters keep
v0.1/2.x payloads readable. v3 removes domain-shaped manifest requirements;
delivery, retrieval, and requirement-quality facts live in profiles and
namespaced extensions.

SemVer policy: patches correct behavior without structural change; minors add
optional fields; majors remove, rename, or alter the meaning of a field. The
v2 schemas cover episode identities, manifests, provenance events, decisions,
and evidence references. `adapt_manifest_v2` turns a readable v0.1 manifest
into the canonical representation; `upgrade_manifest` preserves the v0.1
normal form for old consumers.

```python
from agent_reliability_protocol import EpisodeIdentityV3, ExecutorIdentity, RunManifestV3, SourceIdentity

identity = EpisodeIdentityV3("run-123", "episode-1")
manifest = RunManifestV3(
    run_id="run-123",
    created_at="2026-08-14T00:00:00+00:00",
    source=SourceIdentity(revision="abc123"),
    executor=ExecutorIdentity("agent-runtime", "1.0.0"),
    configuration_hash="sha256:...",
    environment={},
)
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

For migration, use the `*V3` exports for new producers and the explicit
`adapt_manifest_v2_to_v3`, `adapt_event_v2`, `adapt_evidence_v2`,
`adapt_gate_request_v2`, and `adapt_decision_v2` adapters when reading older
payloads. The legacy top-level classes remain available for compatibility but
are not the v3 emission surface.

The ARP 3.0 design is documented in
[docs/superpowers/specs/2026-08-14-arp-3-0-design.md](docs/superpowers/specs/2026-08-14-arp-3-0-design.md).
The merge-gated delivery profile is documented in
[docs/profiles/software-delivery-v1.md](docs/profiles/software-delivery-v1.md).
The final control-plane specification is documented in
[docs/merge-gated-delivery-control-plane-spec.md](docs/merge-gated-delivery-control-plane-spec.md).
