# ARP 3.0 and Merge-Gated Control Plane Specification Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ARP 3.0 the canonical domain-neutral wire contract and rewrite the merge-gated control-plane specification around an ARP 3.0 reliability port.

**Architecture:** Add a focused v3 contract module with generic source, executor, episode, evidence, gate, and lifecycle records. Keep v0.1/2.x readers and serializers as explicit compatibility adapters. The control plane remains independent of ARP; its `ReliabilityRecorder` port emits ARP 3.0 through the `software-delivery/v1` profile.

**Tech Stack:** Python 3.11+, dataclasses, JSON Schema 2020-12, pytest, JSONL fixtures, Markdown specifications.

---

### Task 1: Define ARP 3.0 acceptance contract

**Files:**
- Create: `tests/test_arp_v3.py`
- Create: `docs/superpowers/specs/2026-08-14-arp-3-0-design.md`

- [x] **Step 1: Write failing behavior tests** for canonical v3 manifest, episode identity, evidence, gate request/decision, lifecycle event, v2-to-v3 adaptation, and v3 run-directory validation.
- [x] **Step 2: Run the focused tests and confirm they fail because v3 contracts do not exist.**
- [x] **Step 3: Document invariants and compatibility policy** in the design document: v3 records are generic, v2 records remain readable, new producers emit only v3, pending gates are not decisions, and domain fields live only in profile extensions/artifacts.

### Task 2: Implement canonical ARP 3.0 contracts

**Files:**
- Create: `src/agent_reliability_protocol/v3.py`
- Modify: `src/agent_reliability_protocol/__init__.py`
- Modify: `src/agent_reliability_protocol/contracts.py`

- [x] **Step 1: Add generic v3 value objects** for `SourceIdentity`, `ExecutorIdentity`, and `EpisodeIdentity` without application, model, provider, tracker, or harness imports.
- [x] **Step 2: Add canonical v3 records** for `RunManifest`, `EvidenceRecord`, `GateRequest`, `GateDecision`, and lifecycle records with explicit schema version, run identity, capture policy, provenance, and namespaced extensions.
- [x] **Step 3: Add compatibility properties/adapters** so existing v0.1/2.x consumers can still read their payloads without making legacy fields part of v3 serialization.
- [x] **Step 4: Export the v3 API** while preserving the existing compatibility API under explicit legacy names.

### Task 3: Add v3 schemas and interchange validation

**Files:**
- Create: `src/agent_reliability_protocol/schemas/run-manifest-3.0.0.schema.json`
- Create: `src/agent_reliability_protocol/schemas/episode-identity-3.0.0.schema.json`
- Create: `src/agent_reliability_protocol/schemas/evidence-record-3.0.0.schema.json`
- Create: `src/agent_reliability_protocol/schemas/gate-request-3.0.0.schema.json`
- Create: `src/agent_reliability_protocol/schemas/gate-decision-3.0.0.schema.json`
- Create: `src/agent_reliability_protocol/schemas/lifecycle-event-3.0.0.schema.json`
- Modify: `src/agent_reliability_protocol/interchange.py`
- Modify: `src/agent_reliability_protocol/events.py`
- Modify: `src/agent_reliability_protocol/__main__.py`

- [x] **Step 1: Add schema fixtures and dispatch** for v3 records, evidence, gate requests, and run directories.
- [x] **Step 2: Make the validator select v3 or legacy parsing from `schema_version`.**
- [x] **Step 3: Add CLI support** for `evidence`, `gate-request`, and v3 contracts.
- [x] **Step 4: Run focused schema and CLI tests and confirm they pass.**

### Task 4: Update the delivery profile and control-plane spec

**Files:**
- Modify: `docs/profiles/software-delivery-v1.md`
- Modify: `docs/merge-gated-delivery-control-plane-spec.md`
- Modify: `README.md`

- [x] **Step 1: Map `WorkAttempt` to ARP 3.0** using generic source/executor/input fields.
- [x] **Step 2: Define the `ReliabilityRecorder` port** and the exact `DeliveryVerification` → evidence/artifact → gate request/decision flow.
- [x] **Step 3: Specify authority, recovery, wave release, stale CI, human merge, capture policy, and privacy rules** without putting delivery terms into ARP core fields.
- [x] **Step 4: Add an end-to-end acceptance scenario** for three parallel roots and one merge-gated dependent item.

### Task 5: Verify, review, and publish

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/agent_reliability_protocol/__init__.py`
- Modify: `README.md`

- [x] **Step 1: Bump the package to `3.0.0` and document the migration path.**
- [x] **Step 2: Run the complete test suite, JSON parsing, AST parsing, neutral-contract checks, and `git diff --check`.**
- [x] **Step 3: Review the diff for SOLID, clean-code, and domain-neutrality regressions.**
- [ ] **Step 4: Commit the scoped changes, push `codex/arp-3-0`, open the PR, and verify PR metadata.**
- [ ] **Step 5: Merge the PR only after fresh verification and record the merge commit.**
