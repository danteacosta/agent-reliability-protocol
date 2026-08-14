# ARP Profile: `software-delivery/v1`

Status: Draft 1.0

This profile maps a merge-gated software delivery system onto the neutral
Agent Reliability Protocol (ARP). It does not add delivery semantics to ARP's
core records. Delivery-specific facts live in namespaced extensions and
referenced artifacts.

## Mapping

| Delivery concept | ARP representation |
| --- | --- |
| One `WorkAttempt` | One `RunManifest` with `run_id = attempt_id` |
| Work item identity | `workload_id` and `extensions[software-delivery/v1].work_item_id` |
| Agent session/episode | `EpisodeIdentity.episode_id` |
| Repository revision used as base | `git_sha` |
| Tracker/graph snapshot | `dataset_id` and `dataset_hash` |
| Scheduler and policy configuration | `configuration_hash` |
| Agent runtime identity | `model_provider`, `model_name`, `model_version` |
| Delivery observations | `EvidenceReference` plus a verification artifact |
| Pending human or automated gate | `GateRequest` |
| Resolved gate | `GateDecision` and lifecycle event `gate.decided` |

For the current ARP manifest shape, `dataset_id` means the canonical input
snapshot used to schedule the attempt, not a training dataset. The adapter
MUST document that mapping and provide a deterministic `dataset_hash`.

## Extension namespace

Delivery adapters MAY use the `software-delivery/v1` namespace:

```json
{
  "extensions": {
    "software-delivery/v1": {
      "work_item_id": "PAY-104",
      "attempt_id": "attempt-1",
      "wave_id": "wave-2",
      "base_sha": "abc123",
      "head_sha": "def456",
      "pull_request_ref": "github:pr/123",
      "merge_commit_sha": "fedcba"
    }
  }
}
```

These fields are not part of the neutral ARP core and are ignored by
consumers that do not understand this profile.

## Verification artifact

The adapter SHOULD emit a structured artifact for delivery verification:

```json
{
  "work_item_id": "PAY-104",
  "base_sha": "abc123",
  "head_sha": "def456",
  "ci_checked_head_sha": "def456",
  "ci_status": "passing",
  "reviews_resolved": true,
  "scope_check": "pass",
  "merged": true,
  "merge_commit_sha": "fedcba"
}
```

The ARP evidence reference points to this artifact and records generic claims
such as `artifact_matches_expected_revision` or `required_checks_satisfied`.
The adapter MUST NOT encode SHA values as numeric metrics.

## Gate policy

- A `GateRequest` is emitted when required evidence is complete and a decision
  is needed.
- No ARP `GateDecision` is emitted for a merely pending gate.
- A verified approval emits `GateDecision(decision="approve")`.
- Missing, stale, contradictory, or failed evidence emits `block`, `warn`, or
  `request_clarification` according to the delivery policy.
- A human merge is represented by the delivery artifact and the resulting
  generic gate decision; ARP does not gain a `merge` checkpoint.

## Capture policy

The adapter MUST record the effective capture policy. `metadata` or `redacted`
is the default for delivery runs. `full` requires explicit operator policy
because source diffs, prompts, tool arguments, and review material may contain
secrets or personal data.
