# `intake`

Status: **in development**

Stage 1 of the pipeline (PRD section 12): reads the engineer's input and prepares it for the engines. No calculation, no drawing.

- `form.py`: validates the guided-form answers against `harness/schemas/intake_answers.schema.json`. D24: earthing scheme and available short-circuit level are mandatory and never defaulted.
- `profile.py`: builds the `project_profile` from the answers on top of `projects/_template/project_profile.json` (normative defaults of PRD section 8).
- `hashing.py`: SHA-256 of input files, deterministic manifest of an `inputs/` folder, immutability check `verify_inputs`.
- `loads.py`: reads a JSON load list into `load_list.schema.json` and rejects unknown fields.
- `building.py`: the recognised floors (`epc_arch` rooms with `area_m2` and `size_m`) become the lighting rooms and the `L-<floor>` loads of the load list, before stage 1 freezes it; the power of each load is the installed power returned by `epc_lighting`. Input: `engine_inputs.building` (a floor gives its `architecture` or the `plan` file of `inputs/`, which `resolve_plans` recognises with `epc_arch`); nothing is defaulted (a room without data is an error unless excluded). With `building.receptacles` it also derives `T-<floor>` (VA, from `epc_receptacles`); `circuit_options` gives the per-circuit options of the derived loads.
- `routing.py`: with a `board` per floor, `design_floor` places the luminaires and outlets of the lighting and receptacle results on the plan, lays the runs and routes the circuits with `epc_plan.design`; every branch circuit becomes a load with its power and the length riser + moment length (voltage drop by electrical moments). Stage 3 slice `routing` (`stages/routing_stage.py`) re-routes it.
- `schema_check.py`: small standard-library validator for the draft-07 subset the schemas use.

Tests: `harness/tests/unit/test_intake_discipline.py`. Still missing: plan files (DXF). The profile is written to the project folder by the pipeline through `../store.py` (MIG-31).
