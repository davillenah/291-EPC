# `requirements`

Status: **in development**

Stages 2 and 3 of the pipeline (PRD section 12). No calculation, no engine call.

- `design_basis.py`: assembles the design basis from profile, criteria and assumptions (copies and merges only; each assumption records its reason).
- `verify_inputs.py`: input verification entry point. Rules IV-01 to IV-04 (empty load list, unknown area, missing plan input, duplicate load id) return findings in the shape of the finding schema.

Tests: `harness/tests/unit/test_requirements_discipline.py`. Still missing: plan-versus-load checks that need the `cad/plan` engine.
