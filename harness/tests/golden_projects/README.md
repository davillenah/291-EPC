# `golden_projects`

Status: **in development**

Projects used as end-to-end references.

- `synthetic_lv_small/`: a small SYNTHETIC low-voltage project (invented data only, no client data) that runs the `electrical_lv` pipeline from the intake answers to `deliverables/` (MIG-3X). Its inputs are in the folder; its results are never stored (numbers come from the engines).
- `reference_dwelling/`, `reference_shed/`, `reference_pv_plant/` (GEN-02): three more invented projects with the same four input files (a dwelling, an industrial shed with motors, a small PV plant with an `epc_pv` array). `python harness/tools/ci/reference_run.py` runs all four and compares each with its previous run; `test_reference_projects.py` checks that each finishes.
- `aea90364_reference_cases/`: reference cases of the AEA 90364 engine.
- `309kva_logistics_center`: planned (MIG-42, owner task).
