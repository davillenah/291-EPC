# `synthetic_lv_small`

Status: **in development**

A small SYNTHETIC low-voltage project used to run the `electrical_lv` pipeline end to end (MIG-3X). Every datum here is invented: the client, the site,
the loads, the suppliers and the two "manufacturers" of `synthetic_catalog/` do not exist. There is no client data and no real product data. The files
are inputs only: no result of any engine is stored here (numbers come from running the engines).

| File | What it is |
| --- | --- |
| `intake_answers.json` | The answers of the guided intake form (project `SYNTH-001`, 380 V, earthing TN, short-circuit level declared as synthetic). |
| `loads.json` | The load list: 8 loads (lighting, receptacles, one motor, two special loads). |
| `engine_inputs.json` | The extra calculation inputs that the load list cannot carry: board data, per-load overrides (the motor starter topology, RCBO protection), transformer section, BOQ allowance, RFQ terms and the catalog folder. `datasheets.catalog_dir` is relative to this folder; a test resolves it before the run. |
| `synthetic_catalog/` | Two invented manufacturers with breakers and cables in the shape of `harness/catalogs/manufacturers/`; every product is `unverified`. |
| `expected_summary.json` | Which deliverables the run must produce (names and kinds only, never a number). |

Used by `harness/tests/integration/test_synthetic_lv_small.py`, `test_reproducibility.py` and `test_synthetic_permissions.py`.
