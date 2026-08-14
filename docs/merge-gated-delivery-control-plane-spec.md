# Merge-Gated, Dependency-Aware Agentic Delivery Control Plane

Status: Draft v1.0

License intent: Apache-2.0

Positioning: model-agnostic, evidence-based software delivery orchestration.
This project is inspired by Symphony, Gas Town, Agent Orchestrator, and
wave-based schedulers, but makes no compatibility claim with any of them.

## 1. One-line description

A control plane that turns an explicit work-item dependency graph into isolated
agent executions and releases downstream work only after independently verified
quality gates and an updated base branch.

## 2. Problem

Coding agents can implement tickets in parallel, but an agent's completion
message is not proof that a PR is correctly scoped, that CI ran against the
current commit, that reviews are resolved, or that a dependency was actually
merged into the branch used for downstream work.

The control plane separates production from authority:

> Agents produce work and evidence. The core verifies delivery state from the
> tracker, Git, CI, reviews, and gate records.

## 3. Scope

The first release supports one repository, one tracker project, isolated local
Git worktrees, pull requests, CI/review observation, and human-gated merge.
The scheduler supports two project-wide execution policies:

- `continuous_frontier`: dispatch every item whose explicit blockers are done;
- `wave_barrier`: dispatch a closed batch from one `base_sha`, then wait for the
  whole batch to pass its release gate before opening the next batch.

## 4. Non-goals

- chat UI or IDE;
- automatic merge;
- automatic conflict resolution;
- replacing CI or code review;
- inferring dependencies from ticket titles;
- multi-repository coordination in v1;
- provider-specific agent logic in the scheduler;
- a mandatory dashboard in the first public release.

## 5. Domain model

### WorkItem

Each work item is an executable contract containing:

- imperative title;
- problem and expected behavior;
- explicit in-scope and out-of-scope sections;
- affected paths;
- acceptance criteria;
- test scenarios;
- explicit `blocked_by`, including an empty list when there are no blockers;
- risk level and rollout/kill-switch information when required;
- relevant events and metrics.

Tickets that only add tests, migrations, schema changes, or future foundation
code are rejected by the authoring validator. Tests and migrations belong to
the behavior-changing ticket.

### DependencyGraph

The graph contains explicit nodes and `blocked_by` edges. The compiler rejects:

- missing blocker references;
- cycles, including the exact cycle path;
- malformed work-item contracts.

The graph is never inferred from title or description text.

### WorkAttempt

An attempt records one execution of one work item:

```text
WorkAttempt {
  id
  work_item_id
  base_sha
  workspace_id
  agent_runtime
  started_at
  state
}
```

Retries create a new attempt and preserve a reference to the prior attempt in
the event log.

### DeliveryVerification

This is an internal, delivery-specific record. It may contain PR URLs, commit
SHAs, CI conclusions, review state, affected paths, and scope analysis. It is
not an ARP type.

The ARP integration adapter projects it into generic evidence references and a
delivery profile artifact.

### HumanGate

The internal gate lifecycle is:

```text
pending → approved
        ↘ rejected
        ↘ needs_attention
```

Only an independently observed merge can produce `approved` for the merge
gate.

## 6. Authority boundary

The core may accept a transition only after independently verifying:

1. the PR exists and is linked to the work item;
2. the branch was created from the expected base or is current with it;
3. CI checks refer to the PR's current head SHA;
4. required reviews are resolved;
5. the diff is within declared scope, with v1 best-effort warnings;
6. acceptance criteria signals are recorded but are not trusted alone;
7. the merge actually occurred in the base branch;
8. the new base SHA was captured before dependent dispatch.

An agent cannot mark a ticket done, satisfy a gate, or unblock a dependency by
self-report alone.

## 7. Wave semantics

### Continuous frontier

Every attempt captures its own `base_sha` at dispatch. An item becomes eligible
when every direct blocker reaches verified `Done`.

### Wave barrier

An `ExecutionWave` has a closed item list and one shared `base_sha`:

```text
ExecutionWave {
  wave_id
  base_sha
  work_item_ids
  state: open | closed
}
```

No item in wave N+1 is dispatched until every item in wave N has passed its
gate. The scheduler then fetches the updated base branch and creates all new
workspaces from the resulting SHA.

## 8. System boundaries

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
  → Reconciliation Loop
```

The core interfaces are:

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
  recordLifecycle(event: LifecycleRecord): Promise<void>
  recordEvidence(evidence: EvidenceRecord): Promise<void>
  recordGate(decision: GateRecord): Promise<void>
}
```

`ReliabilityRecorder` is a port. The ARP implementation lives in an adapter
package and emits the `software-delivery/v1` profile. The control-plane core
does not import ARP.

Required v1 adapters:

- Linear tracker;
- GitHub pull request/CI/review observer;
- Git worktree workspace factory;
- ACP agent runtime;
- generic CLI runtime fallback;
- ARP reliability recorder.

## 9. State and recovery

The orchestrator owns scheduling state. State transitions are appended to a
SQLite-backed event log and reconstructed by folding events. External systems
remain authoritative for tracker state, Git refs, PRs, CI, reviews, and merges.

Polling is the v1 default. Webhooks are an optimization, never the only source
of truth. On restart, the reconciler must avoid duplicate dispatches by joining
local attempts with current tracker and Git state.

## 10. Safety and privacy

- agents run only inside their assigned workspace;
- workspace paths must remain under the configured root;
- provider credentials are not copied into untrusted child environments;
- capture policy is explicit: `none`, `metadata`, `redacted`, or `full`;
- high-risk tickets require rollout and kill-switch metadata;
- unresolved evidence conflicts stop downstream dispatch;
- source, prompt, tool, and review content defaults to redacted or metadata-only
  capture.

## 11. Acceptance demo

Three independent tickets enter Wave 1 simultaneously. A fourth ticket is
blocked by all three.

The system must show that:

1. all three roots receive workspaces from the same base SHA;
2. the fourth ticket is not dispatched;
3. agent self-report cannot satisfy the gate;
4. stale CI is classified as unknown rather than passing;
5. only independently verified merges satisfy the three blockers;
6. the scheduler captures the new `origin/main` SHA;
7. the fourth ticket receives a fresh workspace from that SHA.

The simulator must reproduce this flow without Git, a tracker, or a real
agent before the integration path is considered complete.
