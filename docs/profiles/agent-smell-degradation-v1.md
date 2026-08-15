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

`variant_ref` MUST be opaque to the implementation agent. Clean/smelly
condition, injected defect class, oracle information, and expected outcome
MUST NOT be exposed in prompts or T0–T3 event attributes/extensions.

## Temporal boundary

| Boundary | ARP checkpoint | Plane | Confirmatory provenance |
| --- | --- | --- | --- |
| T0 | `input.received` | observable | orchestrator/native input receipt |
| T1 | `interpretation.completed` | observable | runtime native |
| T2 | `plan.completed` | observable | runtime native |
| T3 | `execution.started`, `tool.completed`, `retrieval.completed` | observable | runtime native |
| T4 | `artifact.completed`, then `evaluation.completed` | label | external artifact/evaluator |

All T0–T3 events MUST precede the single `artifact.completed` event.
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

T4 events declare `{"plane": "label"}` in the profile extension. Final
labels, defect classes, oracle outputs, and severity may appear only in T4
artifacts or external blinded-label records.

## Grouping and leakage controls

- Splits are grouped by `project_id` and `source_intent_id`; paired variants
  never cross train/calibration/test boundaries.
- Feature extraction for a checkpoint cutoff may consume only records at or
  before that cutoff.
- Preprocessing and calibration are fit on train/calibration only.
- Confirmatory outputs retain immutable source revision, configuration hash,
  capture policy, event sequence, and artifact hashes.

Use `validate_agent_smell_run(manifest, events)` in the producer gate. A
non-empty error list makes the run ineligible for confirmatory analysis.
