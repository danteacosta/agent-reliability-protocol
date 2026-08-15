# Merge-Gated, Dependency-Aware Agentic Delivery Control Plane

Status: Final v2.1 — open-source readiness refinements and ARP 3.0 integration

License intent: Apache-2.0

## 1. Summary

A model-agnostic control plane that turns an explicit work-item dependency
graph into isolated agent executions and releases downstream work only after
independently verified quality gates and an updated base revision.

The control plane coordinates work. It does not write application code, host a
chat UI, or trust an agent's completion message as authority.

> Agents propose work and produce claims. The control plane verifies external
> state and records portable evidence before releasing dependent work.

## 1.1 Project identity and positioning

The canonical category description is **Merge-Gated, Dependency-Aware Agentic
Delivery Control Plane**. A short project name may be selected later (candidate
names include Wavegate, MergeWave, Dagora, Frontier, Orca-Control, and Fable),
but the descriptive phrase remains the normative one in documentation and
metadata until a name is chosen.

The project coordinates implementation agents; it is not itself an
implementation agent. Its differentiator is the combination of an explicit
dependency graph, merge-gated release, human authority, fresh base revisions,
and portable ARP 3.0 evidence.

It should be compared precisely:

- Devin, OpenHands, Aider, and Cursor Agent execute implementation work;
- Linear and GitHub Actions track work and run checks but do not provide
  dependency-aware agent scheduling with merge gates;
- LangGraph, Temporal, and Prefect orchestrate workflows, but do not define
  code-delivery authority around PR scope, CI, review, merge, and base
  revision.

## 2. Scope and non-goals

Version 1 supports one repository, one tracker project, isolated Git
workspaces, pull requests, CI/review observation, explicit dependencies, and a
human merge gate. It supports two scheduling policies:

- `continuous_frontier`: dispatch every item whose direct blockers are
  independently verified as done;
- `wave_barrier`: dispatch a closed batch from one base revision, then wait for
  the entire batch to pass its release gate.

It does not provide a chat UI or IDE, automatic conflict resolution,
replacement CI, inferred dependencies, multi-repository coordination,
provider-specific scheduler logic, or a mandatory dashboard. Automatic merge
is not the default; an explicitly opt-in soft-auto-merge policy is specified
in Section 4 and is not required for the v1 happy path.

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

### 3.1 Normative minimum schema

The machine-readable contract is
[`docs/work-item.schema.json`](https://github.com/danteacosta/MergeWave/blob/main/docs/work-item.schema.json).
The validator must reject an item that is missing any of these fields:

```text
id, title, problem, scope.in, scope.out, behavior, technical_context,
affected_paths, acceptance_criteria, test_scenarios, blocked_by,
estimate_points, risk, rollout, observability
```

`blocked_by` is always present, including as `[]`. `title` is imperative and
specific; `scope.out` is explicit even when it contains `[]`. The example at
[`docs/work-item.example.json`](https://github.com/danteacosta/MergeWave/blob/main/docs/work-item.example.json)
is the minimum README-quality example for authors and adapter implementers.

The authoring validator is a pre-scheduling gate. In addition to structural
schema validation, it checks that:

- all blocker IDs exist in the imported project snapshot;
- no dependency cycle exists;
- the item is not a test-only, migration-only, schema-only, or speculative
  foundation item;
- estimate points are between 1 and 5;
- affected paths, acceptance criteria, and test scenarios are non-empty;
- risk metadata is present for changes that declare rollout, kill-switch, or
  externally observable behavior;
- the work item does not silently introduce requirements outside `scope.in`.

Authoring errors are reported with a stable error code, field path, human
explanation, and suggested correction. They are not silently repaired by the
orchestrator.

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
  workspace_id
  runtime_ref
  started_at
  state
}

Workspace {
  workspace_id
  repository
  worktree_path
  branch_ref
  base_revision
  initial_head_revision
  current_head_revision
}
```

At workspace creation, `initial_head_revision` must equal `base_revision`.
During implementation, `current_head_revision` is expected to advance as the
agent commits; a changed HEAD is not, by itself, workspace drift. At every
observation the control plane refreshes `current_head_revision` and verifies
that the repository, worktree, and branch still match the assignment.

For delivery, the relevant relation is ancestry, not HEAD equality:
`base_revision` must be an ancestor of the pull request's `head_sha`. This
allows the agent to create one or more commits while preventing a PR from
silently being based on unrelated history.

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

The default release policy is `human_merge`: a human reviews and merges the
pull request. The control plane may expose `soft_auto_merge` as an explicit
project policy, but it is disabled by default and must never be inferred from
green CI. An implementation may take that path only when all of the following
are true:

1. the policy explicitly enables it for the repository and risk class;
2. the configured minimum number of independent approvals is satisfied;
3. required checks are green for the current head revision;
4. scope validation passes with no unresolved warning promoted to a blocker;
5. there are no unresolved blocking review threads or merge conflicts;
6. the target branch and head revision are unchanged since the observations;
7. the action is recorded as a gate decision with policy, evidence IDs, and
   actor `control_plane`, then reconciled against the actual merge.

Soft-auto-merge is a convenience policy, not an authority shortcut. A human
can always reject or disable it, and high-risk items remain human-gated unless
an explicit allowlist says otherwise.

## 5. Authority boundary

The core accepts a release transition only after independently verifying:

1. the PR exists and is linked to the work item;
2. `initial_head_revision == base_revision` was true at workspace creation;
3. the assigned repository, worktree, and branch are still correct;
4. CI checks refer to the PR's current head revision;
5. `base_revision` is an ancestor of the PR's `head_sha`;
6. required reviews are resolved;
7. the diff is inside declared scope, with best-effort warnings in v1;
8. acceptance signals and agent claims are recorded but are not authority;
9. the merge exists in the target base branch;
10. a fresh base revision has been observed before dependent dispatch.

An agent cannot mark a ticket done, satisfy a gate, or unblock a dependency by
self-report alone. Contradictory or stale observations stop downstream
dispatch.

## 5.1 Failure classification

Every item that cannot advance has a structured failure record. The record is
both human-readable and actionable by a retrying agent:

```text
FailureRecord {
  code
  phase
  severity: info | warning | blocking | terminal
  retryable: boolean
  human_summary
  agent_guidance
  observed_at
  evidence_ids[]
  suggested_action
}
```

The v1 code set includes:

```text
invalid_work_item
dependency_cycle
missing_dependency
runtime_unavailable
agent_timeout
agent_cancelled
workspace_creation_failed
workspace_drift
base_revision_mismatch
missing_pull_request
out_of_scope_diff
ci_failed
stale_ci
review_rejected
review_pending
merge_conflict
merge_not_observed
external_state_unknown
evidence_capture_failed
policy_rejected
```

`stale_ci`, `workspace_drift`, `base_revision_mismatch`, and
`external_state_unknown` are blocking but potentially retryable after fresh
observation. `workspace_drift` means the assigned repository, worktree, or
branch is incorrect, an unexpected reset occurred, or the local history no
longer descends from the recorded initial state. It does not mean that the
agent committed and changed `current_head_revision`.

`base_revision_mismatch` is the specific delivery failure emitted when the
ancestry check fails: `base_revision` is not an ancestor of the PR's
`head_sha`. It is distinct from workspace identity/drift checks and must not be
reported merely because the workspace HEAD advanced normally. `out_of_scope_diff`,
`review_rejected`, `invalid_work_item`, and `dependency_cycle` require
correction rather than blind retry. Each failure is emitted to the event log
and, when capture is permitted, to an ARP evidence record. The tracker comment
or agent continuation must include the same code, summary, and next action so
that a person does not need to reconstruct the reason from raw logs.

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

interface AgentRuntimeAdapter {
  id(): string
  protocol(): "acp" | "cli"
  capabilities(): RuntimeCapabilities
  start(input: RunSpec): Promise<RunHandle>
  mapEvent(event: unknown): AgentEvent
  cancellation(): "cooperative" | "process_tree" | "unsupported"
  retryPolicy(): RetryPolicy
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

### 7.1 Runtime plugin contract

ACP is the preferred runtime protocol because it provides a stable lifecycle
and event boundary. The CLI adapter is the compatibility path for runtimes
that expose a reliable command-line entry point. Both paths must preserve the
same `RunSpec`, event vocabulary, cancellation semantics, workspace boundary,
and failure classification.

A new runtime is an adapter, never a scheduler branch. The integration guide
must demonstrate at least Claude Code, Aider, and OpenHands through either ACP
or the generic CLI fallback, without adding their names to core domain types.
Each adapter documents:

- installation and credential requirements;
- command or protocol invocation;
- capabilities and unsupported lifecycle operations;
- event-to-`AgentEvent` mapping;
- timeout, cancellation, and retry behavior;
- workspace and network policy;
- evidence capture defaults and redaction behavior.

The compatibility suite runs every adapter against the same fake scheduler and
asserts that a successful run, timeout, cancellation, retry, and completion
claim produce equivalent control-plane outcomes.

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

## 11. Acceptance demo and implementation order

The simulator is the first implementation gate. It must be deterministic,
offline-first, and runnable without Git, a tracker, provider credentials, or a
real agent. It uses fake ports for the tracker, workspace factory, runtime,
observer, clock, and ARP recorder. It must expose a trace containing dispatch,
observation, classification, gate, and reconciliation events.

The simulator must reproduce this flow:

1. three independent tickets enter wave 1;
2. all three roots receive workspaces from the same base revision;
3. a fourth ticket blocked by all three is not dispatched;
4. an agent completion message cannot satisfy any gate;
5. stale CI is classified as unknown, not passing;
6. only independently verified merges produce approved gate decisions;
7. the scheduler fetches and records the new `origin/main` revision;
8. the fourth ticket receives a fresh workspace from that revision;
9. each run, evidence record, gate request, and decision validates as ARP 3.0.

The simulator also injects these failures and asserts their stable outcomes:

- CI for an old head is `stale_ci`, never passing;
- a changed file outside the declared paths is `out_of_scope_diff`;
- a worker that stops emitting events is `agent_timeout`;
- a workspace created with `initial_head_revision != base_revision` is
  rejected at creation;
- a normally committed workspace with
  `initial_head_revision == base_revision` and an advanced
  `current_head_revision` is not drift;
- a PR whose `head_sha` does not descend from `base_revision` is
  `base_revision_mismatch`;
- a repository, worktree, branch, or history reset that violates the workspace
  assignment is `workspace_drift`;
- a rejected review is `review_rejected` and does not release dependents;
- a restart reconciles existing state without creating a duplicate attempt or
  gate record.

The implementation sequence is normative for the initial public milestone:

1. deterministic simulator and contract tests;
2. CLI plus mock tracker/runtime/observer adapters;
3. real Git workspaces and pull-request observation;
4. Linear adapter, ACP runtime, and ARP recorder;
5. production hardening and optional webhook optimization.

## 12. Open-source surface

The Apache-2.0 core contains the model-agnostic pieces:

- work-item schema and authoring validator;
- dependency graph compiler and cycle diagnostics;
- continuous-frontier and wave-barrier schedulers;
- authority-bound gate evaluator;
- failure classifier and human/agent explanations;
- event log, reconciliation, idempotency, and simulator;
- narrow ports for trackers, workspaces, runtimes, observers, and evidence.

Official adapters are separate integration boundaries: Linear, GitHub,
Git/worktrees, ACP, generic CLI, and ARP 3.0. An adapter may be distributed in
the same repository or a separate package, but it must not leak provider types
into the core. Third-party adapters follow the same port and compatibility
suite, and may add provider-specific evidence only under namespaced profile
extensions.

The public README must include the one-line positioning, the architecture
diagram, the complete work-item example, simulator output, installation, and a
comparison that distinguishes implementation agents, workflow orchestrators,
and this delivery control plane. The README must not claim that real Linear,
GitHub, or agent integrations exist before their adapters and acceptance tests
are present.

## 13. Acceptance criteria for v1

The first release is accepted only when:

- the schema and authoring validator reject malformed or underspecified items;
- both schedulers pass the simulator's dependency, base-revision, and merge
  barrier scenarios;
- workspace creation, normal agent commits, workspace identity, and PR
  ancestry produce their distinct expected outcomes;
- no agent self-report can produce an approved release;
- every blocking failure has a stable code, explanation, and next action;
- the default human gate is exercised end to end;
- the soft-auto-merge policy, if implemented, is disabled by default and
  rejects stale or incomplete evidence;
- the ACP and CLI runtime paths produce equivalent lifecycle outcomes;
- ARP 3.0 records validate with `software-delivery/v1` extensions;
- restart and reconciliation do not duplicate work or gate decisions;
- the core can run offline with no provider credentials.
