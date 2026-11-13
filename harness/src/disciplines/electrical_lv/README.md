# `electrical_lv`

Status: **in development**

Part of the PRD structure; filled by the relocation and migration tasks.

- `pipeline.py`, `stages/`, `rules/`, `intake/`, `requirements/`: the 16-stage pipeline (MIG-30).
- `store.py` (MIG-31): `ProjectStore`, the only module that writes the project folder. Profile, state, progress log, `ssot/` and run folders need a `PipelineToken`; only `ProjectStore.pipeline_session()`, called by `pipeline.run()`, creates one. Atomic, deterministic files; `inputs/` frozen after intake (hash manifest in `ssot/inputs_manifest.json`).
- `manifest.py`, `norm_records.py` (MIG-32): the transmittal manifest (PRD section 13: one manifest per transmittal `TR-NNN`, with the hash of every file in it) built from the frozen inputs, the engine calls of the run, the project profile and the norm records of the called engines with their review state (read only; the register is derived from the engines, `data/review.json` supplies the review). `approved_for_construction` raises `ApprovalBlocked` while a listed record is not `verified` (D21); `signed` stays null; `supersede` marks the earlier transmittal's manifest as replaced by a later one. Limitation: the stage outputs do not name the records a value came from, so all records of the called engine packages are listed (a superset). `store.py` writes manifests under `.epc/manifests/` (`write_manifest`, `update_manifest`) and copies the drawing files into `deliverables/TR-NNN/` (`copy_deliverable`) with the same token and guarantees.
- `stages/calc_check_stage.py` (MIG-35a): stage 13 calls `epc_calc_check.check_run` (engine `validation/calc_check`) with the JSON form of stages 1-12 and the installation inputs the calculation chain used, and returns its findings (`findings_count`, `by_severity`); stage 16 repeats it for the cross-document and manifest checks. The discipline only passes data and returns findings; it never blocks on them.
- `recorder.py` (MIG-31): what `run()` records when the context has a `store`: a progress line, `ssot/stage_<NN>_<slug>.json` and the project state after every stage; profile and freeze after stage 1; stages 2+ are blocked (rule IM-01) if an input changed.

Architecture tests: no other module under `disciplines` writes files (`harness/tests/architecture/test_ssot_writes.py`).
