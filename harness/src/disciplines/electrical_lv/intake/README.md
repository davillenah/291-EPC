# `intake`

Status: **in development**

Stage 1 of the pipeline (PRD section 12): reads the engineer's input and prepares it for the engines. No calculation, no drawing.

- `form.py`: validates the guided-form answers against `harness/schemas/intake_answers.schema.json`. D24: earthing scheme and available short-circuit level are mandatory and never defaulted.
- `profile.py`: builds the `project_profile` from the answers on top of `projects/_template/project_profile.json` (normative defaults of PRD section 8).
- `hashing.py`: SHA-256 of input files, deterministic manifest of an `inputs/` folder, immutability check `verify_inputs`.
- `loads.py`: reads a JSON load list into `load_list.schema.json` and rejects unknown fields.
- `schema_check.py`: small standard-library validator for the draft-07 subset the schemas use.

Tests: `harness/tests/unit/test_intake_discipline.py`. Still missing: plan files (DXF). The profile is written to the project folder by the pipeline through `../store.py` (MIG-31).
