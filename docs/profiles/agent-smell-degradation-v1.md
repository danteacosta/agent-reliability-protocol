# ARP Profile: `agent-smell-degradation/v1`

Status: Confirmatory profile for ARP 3.0

This profile records controlled requirement-quality experiments without
placing smell, model, dataset, or outcome semantics in ARP core. It separates
the observable execution plane (T0–T3) from the artifact/evaluation label
plane (T4), and fails closed when a confirmatory run does not have
runtime-native checkpoints.

## Manifest extension

Every run uses `profile: agent-smell-degradation/v1` and the following
namespaced extension:

```json
{
  "extensions": {
    "agent-smell-degradation/v1": {
      "experiment_id": "exp-2026-01",
      "project_id": "project-01",
      "project_domain": "ecommerce-order-management",
      "lifecycle_role": "functional-requirement",
      "lifecycle_phase": "specification",
      "dataset_schema": "confirmatory-v2",
      "conditional_semantics_schema": "conditional-semantics/v1",
      "source_intent_id": "intent-017",
      "variant_ref": "sha256:opaque-variant-identity",
      "split": "test",
      "confirmatory": true,
      "checkpoint_provenance": "runtime_native"
    }
  }
}
```

`split` is one of `train`, `calibration`, `test`, or `pilot`.
`checkpoint_provenance` is one of `runtime_native`, `replay_derived`, or
`synthetic`. A confirmatory run MUST use `runtime_native`; replay-derived and
synthetic runs are development evidence only.

In this profile, `runtime_native` means **externally materialized by an
instrumented runtime while the episode is active**. It does not mean access to
model chain-of-thought, hidden activations, or privileged internal reasoning.
A separate provider call made after or independently of terminal generation is
a retrospective/prompted snapshot and MUST NOT be labeled `runtime_native`.
Bounded interpretation, plan, tool, and retrieval summaries are eligible when
they are observable before T4 and belong to the same episode that produces the
artifact.

`variant_ref` MUST be opaque to the implementation agent. Clean/smelly
condition, injected defect class, oracle information, and expected outcome
MUST NOT be exposed in prompts or T0–T3 event attributes/extensions.
Project-domain and lifecycle fields are static source metadata for grouped
heterogeneity and external-validity analyses. They are not deployable feature
values and MUST NOT be copied into T0–T3 feature rows.

## Temporal boundary

| Boundary | ARP checkpoint | Plane | Confirmatory provenance |
| --- | --- | --- | --- |
| T0 | `input.received` | observable | orchestrator/native input receipt |
| T1 | `interpretation.completed` | observable | runtime native |
| T2 | `plan.completed` | observable | runtime native |
| T3 | `execution.started`, `tool.completed`, `retrieval.completed` | observable | runtime native |
| T4 | `artifact.completed`, then `evaluation.completed` | label | external artifact/evaluator |

All T0–T3 events MUST be materialized and available to the feature plane before
the single `artifact.completed` event. Merely assigning earlier timestamps to a
retrospectively generated grouped JSON object is invalid.
`evaluation.completed`, when present, MUST follow `artifact.completed`.
Runtime checkpoints contain:

```json
{
  "extensions": {
    "agent-smell-degradation/v1": {
      "checkpoint_source": "runtime_native",
      "content_hash": "sha256:..."
    }
  }
}
```

The thesis-specific T1 interpretation extension may additionally contain the
bounded `conditional_semantics/v1` list:

```json
{
  "conditional_semantics": [
    {
      "antecedent": "the request exceeds five minutes",
      "consequent": "the request is rejected",
      "necessity_status": "sufficient_only",
      "temporal_relation": "next_state",
      "negative_case": {
        "status": "specified",
        "description": "the request is at or below five minutes"
      }
    }
  ]
}
```

An empty list means no conditional clause was identified. The annotation is
pre-final interpretation evidence; it contains no smell label, defect family,
oracle result, artifact, or severity. The allowed necessity statuses are
`sufficient_only`, `also_necessary`, and `undetermined`; temporal relations
are `during`, `next_state`, `eventually`, `irrelevant`, or `undetermined`.

T4 events declare `{"plane": "label"}` in the profile extension. Final
labels, defect classes, oracle outputs, and severity may appear only in T4
artifacts or external blinded-label records.

## Grouping and leakage controls

- Splits are grouped by `project_id` and `source_intent_id`; paired variants
  never cross train/calibration/test boundaries.
- Feature extraction for a checkpoint cutoff may consume only records at or
  before that cutoff.
- Preprocessing and calibration are fit on train/calibration only.
- The primary H2 comparison may define nested models in the experiment
  profile; for `confirmatory-thesis-v3` these are B0=static+operational and
  B1/B2/B3=B0 plus cumulative T1/T2/T3 provenance. ARP carries the evidence
  boundary and does not select models or feature families.
- Confirmatory outputs retain immutable source revision, configuration hash,
  capture policy, event sequence, and artifact hashes.

Use `validate_agent_smell_run(manifest, events)` in the producer gate. A
non-empty error list makes the run ineligible for confirmatory analysis.
