# ARP 2.1 Contract Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the Agent Reliability Protocol with neutral evidence claims, gate requests, capture policy, namespaced extensions, and compatibility-safe schemas, then publish the final contract for the merge-gated delivery control plane as an ARP consumer.

**Architecture:** Keep the ARP core domain-neutral. Add generic primitives for claims, typed scalar observations, gate requests, provenance, capture policy, and opaque namespaced extensions. The delivery control plane remains a separate domain that maps its delivery verification records into ARP through an adapter/profile.

**Tech Stack:** Python 3.11+, dataclasses, JSON Schema 2020-12, pytest 9.1.1.

---

### Task 1: Add failing tests for the ARP 2.1 contracts

**Files:**
- Create: `tests/test_arp_v21.py`
- Modify: none

- [x] **Step 1: Write failing tests**

Cover these public behaviors:

- an evidence reference round-trips generic scalar observations, claim, subject, artifact hash, and capture policy;
- evidence accepts boolean, string, and numeric observations but rejects non-scalar objects;
- a gate request round-trips and records required evidence IDs;
- a gate decision round-trips gate identity, decision authority, policy version, and decision timestamp;
- a run manifest and lifecycle event carry profile, capture policy, and namespaced extensions;
- neutral guards allow opaque namespaced extension payloads while still rejecting domain terms in core fields;
- `check_contract` validates evidence and gate-request records.

- [x] **Step 2: Run the focused tests and verify they fail for missing behavior**

Run: `.venv/bin/python -m pytest tests/test_arp_v21.py -q`

Expected: collection or assertion failures showing the new contracts and fields are not implemented.

---

### Task 2: Implement neutral contract primitives

**Files:**
- Modify: `src/agent_reliability_protocol/contracts.py`
- Modify: `src/agent_reliability_protocol/events.py`
- Modify: `src/agent_reliability_protocol/__init__.py`
- Test: `tests/test_arp_v21.py`

- [x] **Step 1: Add a shared capture policy enum and scalar validation**

Define `CapturePolicy` with `none`, `metadata`, `redacted`, and `full`. Keep `CaptureContent` as a compatibility alias in `interchange.py`.

- [x] **Step 2: Extend `EvidenceReference` without removing v2 fields**

Add optional neutral fields: `subject_ref`, `claim`, `observed`, `expected`, `comparator`, `artifact_hash`, and `capture_policy`. Preserve existing positional constructor behavior and existing numeric `observed_value`/`threshold` fields.

- [x] **Step 3: Add `GateRequest`**

Represent a pending gate independently from a final `GateDecision`. Require gate ID, run ID, checkpoint, policy version, request timestamp, and a list of required evidence identifiers.

- [x] **Step 4: Extend `GateDecision` compatibly**

Add optional `gate_id`, `decided_at`, `decision_authority`, `policy_version`, `capture_policy`, and `extensions` fields while preserving legacy v0.1 positional and outcome forms.

- [x] **Step 5: Add profile, capture policy, and extensions to canonical run/event records**

Add optional fields to `RunManifest` and `LifecycleEvent`. Do not add delivery-specific fields to either record.

- [x] **Step 6: Export the new public types**

Export `CapturePolicy` and `GateRequest` from the package root.

- [x] **Step 7: Run focused tests and verify green**

Run: `.venv/bin/python -m pytest tests/test_arp_v21.py -q`

Expected: all focused tests pass.

---

### Task 3: Align JSON Schemas and contract validation

**Files:**
- Modify: `src/agent_reliability_protocol/schemas/evidence-reference.schema.json`
- Modify: `src/agent_reliability_protocol/schemas/decision.schema.json`
- Create: `src/agent_reliability_protocol/schemas/gate-request.schema.json`
- Modify: `src/agent_reliability_protocol/schemas/run-manifest.schema.json`
- Modify: `src/agent_reliability_protocol/schemas/lifecycle-event.schema.json`
- Modify: `src/agent_reliability_protocol/interchange.py`
- Test: `tests/test_arp_v21.py`

- [x] **Step 1: Make evidence schema match the Python API**

Require only identity and stage. Allow optional artifact, claim, scalar observation, comparator, hash, and capture policy fields. Use schema constraints to reject non-scalar observations.

- [x] **Step 2: Add the gate-request schema**

Define a standalone schema with no delivery-specific terms.

- [x] **Step 3: Extend decision, manifest, and lifecycle schemas**

Add the new optional generic fields while preserving existing required fields and legacy compatibility.

- [x] **Step 4: Extend `check_contract`**

Support `evidence` and `gate-request` contract kinds and preserve all existing kinds.

- [x] **Step 5: Run focused tests and verify green**

Run: `.venv/bin/python -m pytest tests/test_arp_v21.py -q`

Expected: all focused tests pass, including schema-facing validation.

---

### Task 4: Permit opaque namespaced extensions without weakening core neutrality

**Files:**
- Modify: `src/agent_reliability_protocol/neutral.py`
- Modify: `tests/test_neutral.py`
- Test: `tests/test_arp_v21.py`

- [x] **Step 1: Write the extension guard regression test**

Verify that domain terms are rejected in core fields but accepted below an `extensions` object.

- [x] **Step 2: Implement opaque extension traversal**

Treat extension payloads as consumer-owned and require only that their namespaces are non-empty strings. Keep source-level dependency and provider-marker checks unchanged.

- [x] **Step 3: Run the neutral and focused tests**

Run: `.venv/bin/python -m pytest tests/test_neutral.py tests/test_arp_v21.py -q`

Expected: all tests pass.

---

### Task 5: Document the ARP 2.1 boundary and software-delivery profile

**Files:**
- Create: `docs/profiles/software-delivery-v1.md`
- Modify: `README.md`
- Modify: `pyproject.toml`

- [x] **Step 1: Document the profile mapping**

Specify how the merge-gated control plane maps work attempts, agent episodes, tracker/graph snapshots, base revisions, delivery artifacts, and gate outcomes into ARP records. Explicitly keep wave, PR, CI, and merge semantics in the profile/extensions, not the ARP core.

- [x] **Step 2: Document capture policy and compatibility**

State that ARP 2.1 adds optional fields without breaking the v2.0.5 wire contract, and that ARP 3.0 may later generalize the manifest’s experiment-oriented required fields.

- [x] **Step 3: Add the final control-plane specification**

Include the final project contract: scope, non-goals, domain model, authority boundary, wave/frontier policies, adapters, ARP recorder boundary, invariants, acceptance demo, and verification requirements.

- [x] **Step 4: Update package metadata**

Move the package/wire documentation to the ARP 2.1 release intent without claiming a release until the implementation and full suite are verified.

---

### Task 6: Full verification and review

**Files:**
- Test: `tests/`
- Review: all changed files

- [x] **Step 1: Run the complete test suite**

Run: `.venv/bin/python -m pytest -q`

Expected: 0 failures.

- [x] **Step 2: Run the contract CLI against existing and new fixtures**

Run: `.venv/bin/python -m agent_reliability_protocol check --run-directory src/agent_reliability_protocol/fixtures/v2`

Expected: existing fixture behavior remains unchanged and new records validate.

- [x] **Step 3: Review the diff for neutrality and compatibility**

Confirm there are no imports of application, model, provider, harness, Linear, GitHub, PR, merge, or wave concepts in the ARP package core.

- [x] **Step 4: Review documentation against the implementation**

Confirm every documented ARP 2.1 field exists in Python and JSON Schema, and every delivery-specific concept is confined to the profile document.

- [ ] **Step 5: Commit the implementation**

Use a focused commit such as `feat: add neutral evidence and gate contracts`.
