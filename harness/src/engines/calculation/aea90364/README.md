# epc-aea90364

The AEA 90364 norm as an engine: everything that belongs to the norm is in this one package, `epc_aea90364`.

```
src/epc_aea90364/
├── aea_*.py, board_*.py, ...     the calculation: demand, protection, ampacity, cable section, voltage drop, short circuit, earthing, route, special locations
├── data/
│   ├── review.json               who approved which point of the norm data, when, and the fingerprint of the approved value (the owner's review state)
│   ├── review-log.jsonl          every review action, appended
│   ├── installation_types.json   vocabulary of installation types (D14: project logic, not a norm value)
│   └── insulation_by_role.json   insulation by circuit role (D6: project rule, not a norm value)
├── standards/<STANDARD-ID>/rules.json   standards ingested with `epc_standards` and promoted (schema 1.1), one folder per part of the norm
├── norm_data.py                  the ONE loader of the norm data (see below) and the place of the review state
└── policy.py                     the protection constants (to move to aea_tables.json)
```
The **norm data** is not in the package any more (MIG-37a): it is in `harness/config/normative/AR/electrical/aea90364/` and is read only through `epc_aea90364.norm_data`:

```
harness/config/normative/AR/electrical/aea90364/
├── aea_tables.json               tables and constants of the norm (capacity tables, correction factors), each with its clause
├── rules/*.json                  the engineering rules derived from the norm (paraphrased; norm, edition, clause and page as reference) and `_indice.json`
├── design-criteria.json          the catalog of base design criteria (the norm reviewer corrects the values here; a project overrides them)
├── standard-solutions.json       which symbols build each circuit
└── system_voltages.json          230/400 V and 220/380 V systems and their U0 (D16)
```
`norm_data.normative_dir()` finds that folder: the environment variable `EPC_NORMATIVE_ROOT` (the `normative` folder that holds `AR/`) when set, else the nearest parent of the module with `harness/config/normative` (the repository, or `lib/` in a built plugin, where the build copies the folder), else a `FileNotFoundError` that names what was searched. `load_json(name)` reads lazily and caches; `clear_cache()` (and the old `aea_tables.limpiar_cache_tablas()` / `aea_rules.limpiar_cache_reglas()`) forget it. An installed wheel does not carry the folder: set `EPC_NORMATIVE_ROOT`.

Other norms get an engine of their own with the same shape (`engine/iec60364/`, `engine/nfpa70/`...): the calculation, the data and the rules of a norm are never spread over other folders.
The private material (the PDFs and the study notes) stays out of the repository, in `local/dev-knowledge/standards/<country>/<id>/`.

Which norm engine a country uses for a domain is said by `harness/config/normative/<CC>/jurisdiction.json` (`packs`: `{"electrical": "aea90364"}`).
Run: `python -m epc_aea90364.aea_pipeline input.xlsx`. Tests: `python -m unittest discover -s tests` from this folder with `PYTHONPATH` on the `engine/*/src` folders.
Limits: `hazen_williams.py` and `hvac_airflow.py` are not AEA calculations and should move to engines of their own (`lighting.py` already did: it is `harness/src/engines/calculation/lighting`, ADR-0030); the calculation is written for this norm only (no selector of norm yet, see `harness/docs/architecture/GUIA_NORMAS.md`).

## Split into calculation packages (MIG-37b)
The cohesive calculation modules moved, unchanged, to packages of their own under `harness/src/engines/calculation/`; each old module name here is a shim that IS the new module (same object), kept for one release:
`calc_common` (`norm_data`, `aea_tables`, `policy`, `_validate`, `fmt`, `aea_rounding`), `load_balance` (`aea_demand`, `current_and_loads`, `system_voltage`), `voltage_drop` (`aea_voltage_drop`, `voltage_drop`),
`feeder_sizing` (`aea_conductors`, `aea_ampacity`, `conductor_selection`, `cable_thermal`, `aea_route`), `short_circuit` (`short_circuit`, `aea_icc_decay`, `aea_icc_factors`), `grounding` (`aea_earthing`), `selectivity` (`aea_protection`).
This package keeps the orchestrator (`aea_pipeline`), the board documents (`board_*`, `aea_feeder_report`), `grouping`, `solutions`, `simultaneity`, `insulation_roles` (they read this package's `data/`), the motor, backup, reactive, lightning, panel-thermal, special-locations, HVAC/hydraulic and catalog/export modules, and the owner's review state (`data/review*`). Dependency direction: `epc_aea90364` -> the packages above -> `epc_calc_common`; the packages never import `epc_aea90364`.
