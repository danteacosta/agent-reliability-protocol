# ARP Profile: `software-delivery/v1`

Status: Final profile for ARP 3.0

This profile maps merge-gated software delivery onto the neutral ARP 3.0
contract. It does not add delivery semantics to ARP core records. Delivery
facts live in this namespaced extension and in referenced verification
artifacts.

## Mapping

| Delivery concept | ARP 3.0 representation |
| --- | --- |
| One `WorkAttempt` | One `RunManifestV3`, with `run_id = attempt_id` |
| Repository base revision | `source.revision` |
| Tracker/graph snapshot | `source.input_ref` and `source.input_hash` |
| Scheduler/policy configuration | `configuration_hash` |
| Agent runtime identity | `executor.name`/`executor.version`; provider-specific details remain in this profile extension |
| Agent episode | `EpisodeIdentityV3` and lifecycle events |
| Delivery observation | `EvidenceRecord` plus a verification artifact |
| Pending human or automated gate | `GateRequestV3` |
| Resolved gate | `GateDecisionV3` and `gate.decided` lifecycle event |

The adapter MUST use `source.revision` for the exact base revision used to
create the workspace. The graph snapshot is an input to scheduling and MUST
have a deterministic reference and hash. A delivery adapter MUST NOT encode a
commit SHA as a numeric observation.

## Extension namespace

The only delivery-specific namespace defined by this profile is
`software-delivery/v1`:

```json
{
  "extensions": {
    "software-delivery/v1": {
      "work_item_id": "PAY-104",
      "attempt_id": "attempt-1",
      "wave_id": "wave-2",
      "workspace_id": "workspace-1",
      "pull_request_ref": "github:pr/123",
      "head_revision": "def456",
      "merge_revision": "fedcba"
    }
  }
}
```

Fields inside this namespace are opaque to ARP consumers that do not implement
the profile. The control plane owns their meaning and independently verifies
them against Git, the tracker, CI, and review systems.

## Verification artifact

The adapter SHOULD emit one immutable artifact per delivery verification:

```json
{
  "work_item_id": "PAY-104",
  "attempt_id": "attempt-1",
  "base_revision": "abc123",
  "head_revision": "def456",
  "ci_checked_revision": "def456",
  "ci_status": "passing",
  "reviews_resolved": true,
  "scope_check": "pass",
  "merged": true,
  "merge_revision": "fedcba",
  "observed_at": "2026-08-14T00:01:00+00:00"
}
```

The corresponding `EvidenceRecord` uses generic claims such as
`artifact_matches_expected_revision` and `required_checks_satisfied`, points
to the artifact, and records its hash. The artifact is the source of truth for
the delivery-specific fields; the ARP record is the portable claim and
provenance envelope.

## Gate semantics

- Emit `GateRequestV3` when required evidence is available and a decision is
  pending.
- Do not emit a `GateDecisionV3` for a merely pending human merge.
- Emit `approve` only after the configured authority has resolved the gate and
  the core has independently verified the evidence.
- Emit `block`, `warn`, or `request_clarification` only for an actual resolved
  outcome, according to the delivery policy.
- A merge is profile evidence, not an ARP lifecycle checkpoint.
- Downstream dispatch requires an approved gate and a newly observed base
  revision after merge.

## Capture policy

The adapter MUST record the effective policy on every v3 record. `metadata` or
`redacted` is the default for delivery. `full` requires explicit operator
authorization because diffs, prompts, tool arguments, review content, and
tracker data can contain secrets or personal data. `none` records no captured
content while preserving the contract identity and decision metadata.

## Compatibility

ARP 2.x delivery records can be read and adapted to v3. Legacy delivery keys
are preserved only under `arp-compat/v2`; new delivery producers MUST emit v3
records and this profile.
