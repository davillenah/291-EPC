# epc_descriptive_report

Status: **in development**

Quality engine (MIG-39g, PRD section 12 stage 11 "Documents", item "descriptive report"): builds the DESCRIPTIVE REPORT (memoria descriptiva) of a board as structured data and renders it as Spanish plain text. It describes the installation in prose (what it is, how it is organised, which protections and earthing it has, which norms apply, what is pending); the calculation report (memoria de calculo, `epc_aea90364.board_memo`) holds the numbers, so nothing is duplicated. Pure functions, standard library only, no I/O, no file output, no calculation. Its outputs are drafts (D21).

## Public API
- `build_descriptive_report(design_basis, circuits, *, terminals=None, boq=None, pending_documents=None, unreviewed_norm_records=None)`: dict `{sections, issues, assumptions, norm_records, status}`; `status` is always `draft`, `norm_records` is always `[]`. `sections` is a list of `{id, title, items}`, each item `{key, label, value, unit, source, review_status}` (cable-specification items also carry `spec`).
- `descriptive_report_to_text(doc)`: plain text in Spanish, produced only by string templates and the document's values; no digit is written in a template (checked by a test). A sentence whose values are missing is left out.

## Input formats
- `design_basis` (required): the document of `epc_design_basis` (a dict with a list `sections`, each `{id, items:[{key, label, value, unit, source, review_status}]}`, optional `open_items`). Plain dict, no import of that engine.
- `circuits` (required, non-empty list): one dict per circuit with `tag` (unique text) and the optional `kind` (type of circuit), `phases`, `device_kind`, `s_mm2` (> 0), `material`, `insulation`, `length_m`, `description`. A field not given is shown as `not specified`. Invalid input raises `ValueError`.
- `terminals` (optional): a terminal-block list (its `totals` key is read) or its totals `{"terminals": n}`.
- `boq` (optional): a bill of quantities (its `totals` `lines`, `devices`, `cable_m` are copied).
- `pending_documents` (optional): list of `{name, status, reason?}`.
- `unreviewed_norm_records` (optional): whole number, zero or more, as the caller counted it.

## Sections
1. `object_scope`: project, client, site, country, installation type, language (copied from the design-basis identification).
2. `supply_earthing`: source, voltage, earthing system, short-circuit level and its origin (copied).
3. `board_organisation`: number of circuits, and counts by type and by phases.
4. `cables_installation`: the distinct cable specifications (material, insulation, section) with the number of circuits of each; terminal and BOQ counts when given.
5. `protection_earthing`: the kinds of protective device present with their circuit counts, the earthing system and the disconnection times of the design basis.
6. `standards`: jurisdiction, revision of each part and criteria set (copied).
7. `status_limitations`: the draft notice (D21), the pending documents with their reasons, the number of unreviewed norm records and the number of open requirements.

## Rules
- The only operation on the data is COUNTING (stated in `assumptions`); no sum, ratio, minimum or maximum, and no value of its own.
- A missing optional input is an entry of `issues` (`not provided: boq`) and its sentence is omitted; a design-basis section or item that cannot be found is also an issue. Nothing is invented.
- Deterministic; inputs are not modified.

## Data and provenance
No data table: the engine owns no value, so there is no norm register file and `norm_records` is `[]`. The values it copies carry the review status they have in the design basis.

## Not modelled
Verification, approval, sign-off, figures of the calculation, free-text narrative written by a person.

## Depends on
The standard library only. It never imports a discipline, the platform, the web or another engine.

## Tests
`python -m unittest discover -s tests` or pytest from this folder (every engine `src/` on `PYTHONPATH`, as the gate does).
