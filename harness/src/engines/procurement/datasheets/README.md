# epc_datasheets

Status: **in development**

Procurement engine (MIG-39d, PRD section 12 stage 11, "Documents and lists"): draft equipment datasheet records. For each equipment requirement derived from the calculation (protective devices, cables) it lists the manufacturer-catalog products that satisfy the requirement BY COMPARISON, with the catalog fields copied verbatim. It never picks a winner, never calculates an electrical value and never invents product data. Pure functions, standard library only, no I/O at import and no file output. Its outputs are drafts (D21).

## Public API
- `build_datasheets(board_name, requirements, catalog)`: dict `{board, datasheets, totals, assumptions, norm_records, issues}`. Each datasheet: `{item_id, kind, requirement, candidates, issues, review_status, review_reason}` with `review_status: "pending review"` and `review_reason: "catalog values are unverified manufacturer data"`. `totals = {items, items_without_candidate}`. Records are sorted by `item_id`; candidates by manufacturer, family, id.
- `requirements_from_circuits(circuits, voltage_v=None)`: the deduplicated requirements of the per-circuit shape of the bill-of-quantities engine (same field names; duplicated validation, no import of `epc_boq`). One device requirement per distinct (kind, In, poles, breaking capacity) and one cable requirement per distinct (material, insulation, phase conductors, sections), each with the sorted circuit tags and a deterministic id (`DS-DEV-001`..., `DS-CAB-001`...). `voltage_v` (optional) is copied to the device requirements; it is never guessed.
- `render_rows(ds)`: flat rows, one per candidate (one empty-product row for a record without candidate). No file is written.
- `load_catalog_dir(path)`: the only I/O, explicit and separate: reads `<path>/<manufacturer>/manufacturer.json` plus `breakers.json` / `cables.json` of each manufacturer into the `catalog` argument (adds `manufacturer_name`). Clear `ValueError` for a missing folder, a missing or invalid file, bad JSON, missing required keys, wrong numbers, duplicate product ids. `build_datasheets` never locates or reads the repository catalog.

## Input formats
- Device requirement: `{item_id, kind: "protective_device", device_kind (mccb, mcb...), in_a, poles, breaking_capacity_ka, voltage_v, circuits: [tags]}` (everything but `item_id`, `kind`, `circuits` may be `null`).
- Cable requirement: `{item_id, kind: "cable", material, insulation, phase_conductors, s_mm2, neutral_mm2, pe_mm2, cores, circuits}`.
- `catalog`: a list of product-file documents as parsed JSON, `{"manufacturer", "category": "breakers"|"cables", "products": [...]}`. A product has `id, family, type, status (unverified|verified), source` and optionally `rated_current_a` (`{"min"?, "max"}` as in the repository catalog, or a list of numbers), `poles` (list), `breaking_capacity` (`[{voltage_v, icu_ka, class?, standard?}]`), `voltage`, `standards`, `construction`, `temperature_c`, `notes`. The manufacturer file is `{id, name, categories, country?, web?}`. Schema: `harness/schemas/manufacturer_catalog.schema.json`.

## Satisfaction rules (comparisons only)
- Protective device: the product is in a `breakers` document; its `type` equals the requested kind; its rated-current data contains In (`min <= In <= max`, a missing `min` is no lower bound; an object without `max` or a product without the field is NOT satisfied); when a breaking capacity is required, a catalog entry at a voltage >= the required voltage (any voltage when none is given, reported as an issue) has `icu_ka` >= the required kA (equal passes). Poles: compared only when the catalog lists them (must include the requested number); otherwise the candidate lists `poles` in `unconfirmed`.
- Cable: the product is in a `cables` document; when an insulation is required, the catalog `construction` or `family` text must mention it as a whole word. The catalog carries no material, section or conductor count: every cable candidate lists `material, section, conductors` in `unconfirmed`.
- A requirement the catalog cannot answer is not satisfied (never relaxed). With no satisfying product the record has `candidates: []` and the issue `<item_id>: no catalog product satisfies the requirement`. A device requirement without kind or In is not compared (issue). Each candidate carries `catalog_status` verbatim (all `unverified` today), `matched` (the compared values and the satisfying breaking-capacity entries) and `unconfirmed`.

## Data and provenance
The engine holds no norm value; the catalog values are manufacturer data, all `unverified`, and every record stays `pending review`. `norm_records` of the output lists, per (manufacturer, category) that supplied a candidate, the catalog values used with their pending state. The norm register (`src/epc_datasheets/norm_register/params.json`) has one pending record per repository catalog file (`harness/catalogs/manufacturers/{abb,schneider-electric,siemens}/breakers.json`, `prysmian/cables.json`), pointing at `/products` of that file (location `file` is repository-relative, as the register schema allows). A new manufacturer file needs its own record. Nothing is marked verified.

## Not modelled
Choosing or ranking products, prices, availability, derating, selectivity or coordination between devices, matching cable section or material to the catalog (the catalog has no such data yet), accessories, enclosures.

## Depends on
Nothing (standard library). It never imports a discipline, the platform or the web.

## Tests
`python -m unittest discover -s tests` or pytest from this folder (every engine `src/` on `PYTHONPATH`, as the gate does). One test reads the real repository catalog read-only.
