# ADR-0043: One report engine, called as a function and safe to run in parallel

Status: proposed (owner request of 2026-11-26: "same logic as the drawing engine"; name, area and the open decisions below wait for the owner). Builds on ADR-0038 (engines are called, not watching), ADR-0039 (errors and results) and ADR-0042 (one drawing engine). BACKLOG REP-01.

## Context
The calculation engines should only calculate. Today the report code is spread over several places and mixes calculation, wording and format:
- `epc_drawing.export` held the PDF, Word and Excel writers (`report_pdf`, `report_docx`, `logo`, `tables_xlsx`, `transmittal_pdf`); they take a destination path, read logo files and read the clock.
- `disciplines/electrical_lv/stages/rendering.py` builds the blocks of each report (`_pv_report`, `_lighting_report`, `_boq_report`...).
- `epc_aea90364.board_memo` writes the calculation memorandum and the summary of a board inside the calculation engine.
- `epc_descriptive_report` and `epc_documents` have their own outputs.

## Decision
1. **One report engine `epc_report`** with one kernel (`epc_report.core`: block model, layout, cover, i18n, PDF, DOCX and XLSX writers) and one child per kind of report (`report_calc_memo`, `report_descriptive`, `report_summary`, `report_savings`, `report_economic`, `report_commissioning`, `report_om_manual`...). The other modules call it; it calls nothing outside itself.
2. **Called, never searching** (ADR-0038). Every function receives all its data (results of the engines, the text template, logos and figures as bytes, cover data, date, language) and returns the report as bytes plus the list of files. It reads no file, environment variable, clock or folder; the caller writes.
3. **Parallel by construction.** No module state that a call changes, no process cache, no temporary file, no subprocess. Same input, same bytes (dates and metadata travel as data). Checked with the same thread and process test as the drawing engine.
4. **The calculation engines do not write text.** They return numbers, tables, findings and the clause of each. Titles, transitions and narrative live in text templates stored as data (JSON, English and Spanish) inside `epc_report`. No number is written by hand: a template only names the field.
5. **Figures are inputs.** The irradiation disk, the shading abacus, the single-line diagram and the layouts are drawn by `epc_draw` (data in `outputs.pv.charts`) and arrive as data or bytes; the report places them and does not draw them.
6. **Same bytes first.** Each move starts with a characterization of today's output and ends with it unchanged. A step that cannot keep the bytes stops and goes to the owner. Golden files are never edited.
7. **Own nomenclature** for every file, block and code (`NAMING.md`, `naming.py`); everything the user sees in English and Spanish.

## Structure
`harness/src/engines/quality/report/src/epc_report/` with `core/`, `templates/` (text as data), one folder per kind of report, `norm_register/`, `schema/` (typed inputs), and tests (bytes, contract, determinism, parallel, registry, i18n, purity count that only shrinks). Registered like the other engines (gate area, coverage floor, impact map, `ENGINE_CONTRACTS.md`). The old names stay as doors while they are used.

## Steps (each its own pull request)
a) Purity and parallel tests as a measurement of what the writers still read. b) Logos, cover data and date travel as data. c) **Done in the first pull request:** `epc_report.core` with the writers moved from `epc_drawing.export`, which keeps doors; same bytes with a fixed clock. d) The writers return bytes and the caller writes. e) First kind of report: the PV yield study (today `_pv_report`), then the PV calculation memorandum, summary, descriptive, savings and economic memorandums, then commissioning, O&M, performance and quotation. f) The board reports (`board_memo`, lighting, cables, bill of quantities) and the removal of the block building from `rendering.py`. g) Remove the old packages.

## Consequences
- One place for a report rule (format, cover, language, numbering) and a pool of workers can build reports in parallel.
- Texts are data, reviewed without touching code.
- Cost: the moves need careful characterization of PDF and Word bytes. Today the writers read the clock, so equal bytes need a fixed clock until step d.

## Decisions for the owner
1. The name `epc_report` and the area `engines/quality/report` (assumed here).
2. Whether the board reports (`board_memo`) move in this programme or later.
3. Figures as SVG, PNG or both (the PDF needs an image).
4. Default currency, date and number format (es-AR).
5. Who signs and the state each report leaves in.
6. Text templates inside the engine (proposed) or in the document catalogue.
