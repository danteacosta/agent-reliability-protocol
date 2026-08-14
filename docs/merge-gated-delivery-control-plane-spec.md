# Merge-Gated, Dependency-Aware Agentic Delivery Control Plane

Status: Final v2.0 — ARP 3.0 integration

License intent: Apache-2.0

## 1. Summary

A model-agnostic control plane that turns an explicit work-item dependency
graph into isolated agent executions and releases downstream work only after
independently verified quality gates and an updated base revision.

The control plane coordinates work. It does not write application code, host a
chat UI, or trust an agent's completion message as authority.

> Agents propose work and produce claims. The control plane verifies external
> state and records portable evidence before releasing dependent work.

## 2. Scope and non-goals

Version 1 supports one repository, one tracker project, isolated Git
workspaces, pull requests, CI/review observation, explicit dependencies, and a
human merge gate. It supports two scheduling policies:

- `continuous_frontier`: dispatch every item whose direct blockers are
  independently verified as done;
- `wave_barrier`: dispatch a closed batch from one base revision, then wait for
  the entire batch to pass its release gate.

It does not provide a chat UI or IDE, automatic merge, automatic conflict
resolution, replacement CI, inferred dependencies, multi-repository
coordination, provider-specific scheduler logic, or a mandatory dashboard.

## 3. Work-item contract

A tracker item is an executable prompt, not a title fragment. It contains:

- an imperative, specific title;
- problem and expected behavior;
- in-scope and explicitly out-of-scope sections;
- affected modules, functions, and paths;
- acceptance criteria and test scenarios;
- explicit `blocked_by`, including `[]` when unblocked;
- risk, rollout, kill-switch, events, and metrics when applicable;
- i18n, privacy, factory, migration, and schema requirements when applicable.

Tests and migrations belong to the behavior-changing item. A standalone test,
migration, schema, or speculative foundation item is rejected by the authoring
validator. Items above five points are split, and non-trivial pull requests
target approximately 400 changed lines or less.

## 4. Domain model

### Dependency graph

The graph contains explicit nodes and `blocked_by` edges. Compilation rejects
missing blockers, cycles with the exact cycle path, malformed work-item
contracts, and duplicate identities. Dependencies are never inferred from
titles or prose.

### Work attempt

```text
WorkAttempt {
  attempt_id
  work_item_id
  base_revision
  workspace_id
  runtime_ref
  started_at
  state
}
```

Retries create a new attempt and retain a reference to the previous attempt in
the local event log and ARP extension.

### Delivery verification

`DeliveryVerification` is an internal delivery record containing PR, revision,
CI, review, scope, merge, and acceptance-signal observations. It is not an
ARP core type. The reliability adapter projects it to an ARP 3.0
`EvidenceRecord` and an immutable `software-delivery/v1` artifact.

### Human gate

```text
pending → approved
        ↘ rejected
        ↘ needs_attention
```

`pending` is represented by ARP `GateRequestV3`; only a resolved state produces
`GateDecisionV3`. A pending merge is never encoded as `block`.

## 5. Authority boundary

The core accepts a release transition only after independently verifying:

1. the PR exists and is linked to the work item;
2. the workspace was created from the expected base revision;
3. CI checks refer to the PR's current head revision;
4. required reviews are resolved;
5. the diff is inside declared scope, with best-effort warnings in v1;
6. acceptance signals and agent claims are recorded but are not authority;
7. the merge exists in the target base branch;
8. a fresh base revision has been observed before dependent dispatch.

An agent cannot mark a ticket done, satisfy a gate, or unblock a dependency by
self-report alone. Contradictory or stale observations stop downstream
dispatch.

## 6. Waves and base revisions

### Continuous frontier

Each attempt captures its own `base_revision` at dispatch. An item is eligible
only when every direct blocker has a verified release decision and current
tracker/Git state.

### Wave barrier

```text
ExecutionWave {
  wave_id
  base_revision
  work_item_ids
  state: open | closed
}
```

Every item in a wave is created from the same base revision. No item in wave
N+1 is dispatched until every item in wave N passes its gate. The scheduler
then fetches `origin/main`, records the new revision, and creates all next-wave
workspaces from that revision.

## 7. System boundaries and ports

```text
Tracker Adapter
  → normalized WorkItems
  → Graph Compiler
  → Scheduler
  → Workspace Factory
  → AgentRuntime
  → PR/CI/Review Observers
  → DeliveryVerification
  → Gate Evaluator
  → ReliabilityRecorder
  → Reconciliation Loop
```

The core owns these ports and has no ARP, model-provider, tracker SDK, or Git
provider dependency:

```typescript
interface AgentRuntime {
  start(input: RunSpec): Promise<RunHandle>
  stream(run: RunHandle): AsyncIterable<AgentEvent>
  continue(run: RunHandle, input: string): Promise<void>
  cancel(run: RunHandle): Promise<void>
  capabilities(): RuntimeCapabilities
}

interface TrackerAdapter {
  fetchCandidates(): Promise<RawWorkItem[]>
  fetchDependencies(itemId: string): Promise<string[]>
  transitionState(itemId: string, state: WorkItemState): Promise<void>
  linkPullRequest(itemId: string, url: string): Promise<void>
  postComment(itemId: string, body: string): Promise<void>
}

interface ReliabilityRecorder {
  recordRun(run: RunRecord): Promise<void>
  recordEpisode(event: EpisodeRecord): Promise<void>
  recordEvidence(evidence: EvidenceRecord): Promise<void>
  requestGate(request: GateRequest): Promise<void>
  decideGate(decision: GateDecision): Promise<void>
}
```

The ARP adapter is the only component that knows the ARP package. It maps:

```text
WorkAttempt          → RunManifestV3 + EpisodeIdentityV3
DeliveryVerification → EvidenceRecord + delivery artifact
HumanGate pending    → GateRequestV3
HumanGate result     → GateDecisionV3
```

Required v1 adapters are Linear, GitHub pull request/CI/review observation,
Git worktree creation, an ACP runtime, a generic CLI runtime fallback, and an
ARP 3.0 reliability recorder.

## 8. ARP 3.0 recording contract

The control plane emits `profile = software-delivery/v1` and uses:

- `source.revision` for the exact workspace base revision;
- `source.input_ref` and `source.input_hash` for the normalized graph/tracker
  snapshot;
- `executor.name` and `executor.version` for the runtime abstraction;
- `configuration_hash` for scheduler and policy configuration;
- namespaced extensions for work item, attempt, wave, workspace, PR, head,
  merge, CI, and review references;
- immutable artifacts for detailed delivery verification;
- generic evidence claims and evidence IDs for gate records.

The core does not put `blocked_by`, `wave`, PR URLs, CI provider names, merge
states, or domain metrics into ARP core fields. `merge` is evidence in the
delivery profile, not a new ARP lifecycle checkpoint.

## 9. State, persistence, and recovery

The orchestrator owns scheduling state. Local transitions are appended to a
SQLite event log and reconstructed by folding events. Git refs, tracker state,
PRs, CI, reviews, and merge state remain authoritative in their external
systems.

Polling is the v1 default. Webhooks optimize latency but are never the only
source of truth. On restart, reconciliation joins local attempts to current
tracker and Git state before dispatching; idempotency keys prevent duplicate
workspaces and duplicate gate records.

## 10. Safety and privacy

- agent processes run only inside their assigned workspace;
- workspace paths remain under the configured root;
- credentials are not copied into untrusted child environments;
- capture policy is explicit on every ARP 3.0 record;
- metadata or redacted capture is the default;
- full capture requires operator authorization;
- high-risk work requires rollout and kill-switch metadata;
- evidence conflicts and stale CI halt downstream release;
- prompts, diffs, tool arguments, review text, and personal data are never
  captured by default.

## 11. Acceptance demo

The simulator must reproduce this flow without Git, a tracker, or a real agent:

1. three independent tickets enter wave 1;
2. all three roots receive workspaces from the same base revision;
3. a fourth ticket blocked by all three is not dispatched;
4. an agent completion message cannot satisfy any gate;
5. stale CI is classified as unknown, not passing;
6. only independently verified merges produce approved gate decisions;
7. the scheduler fetches and records the new `origin/main` revision;
8. the fourth ticket receives a fresh workspace from that revision;
9. each run, evidence record, gate request, and decision validates as ARP 3.0.
