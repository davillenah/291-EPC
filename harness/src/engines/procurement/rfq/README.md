# epc_rfq

Status: **in development**

Procurement engine (MIG-39e, PRD section 12 stage 11, "Documents and lists"): builds the draft request for quotation (pedido de cotizacion) of a board from its bill of quantities, optionally its datasheets, and the explicit commercial terms of the caller. It builds the request DOCUMENT only: it never contacts a supplier, never scrapes a web site, never sets a price or any other commercial value. Pure functions, standard library only, no I/O at import and no file output. Its outputs are drafts (D21).

## Public API
- `build_rfq(board_name, boq, *, suppliers, currency, response_deadline, delivery_site, validity_days, payment_terms=None, notes=None, datasheets=None, requestable_categories=None)`: dict `{rfq_id, board, issued_for, terms, requestable_categories, lines, totals, comparison_template, assumptions, norm_records, issues}`.
- `render_rows(rfq)`: flat rows, ONE ROW PER LINE (not per line x supplier), in line order: `rfq_id, board, line_no, item_id, category, description, unit, quantity, references` (one text), `incomplete, issue`, then one blank column per supplier and response field named `<supplier>: unit_price|delivery_days|brand_offered|remarks` (the `comparison_template["columns"]` after the five fixed ones). No file is written.
- `rfq_to_text(rfq)`: plain-text letter in Spanish (header, terms, numbered lines with their references and incomplete flags, response request). It is produced only by string templates from the values; no number is typed in a template (checked by a test).

## Input formats
- `boq`: the structure of `epc_boq.build_boq` as a plain dict (no import): `items`, each with `item_id`, `category`, `description`, `unit` and `quantity` (positive number or null), and optional `source`, `issues`, `spec`; other keys are ignored. Duplicate `item_id` is rejected.
- Commercial terms, REQUIRED and WITHOUT defaults (one `ValueError` lists every missing one): `suppliers` (non-empty list of `{name, contact?}`, names unique ignoring case, the caller's order is kept), `currency` (text, e.g. `ARS`), `response_deadline` (ISO date `YYYY-MM-DD`; format and calendar validity only, never compared with today), `delivery_site` (text), `validity_days` (positive whole number). Optional: `payment_terms`, `notes` (text).
- `datasheets` (optional): the structure of `epc_datasheets.build_datasheets` as a plain dict (`datasheets`: `item_id`, `kind`, `requirement`, `candidates` with `manufacturer`, `product_id`, `family`, `source`, `catalog_status`).
- `requestable_categories` (optional): list of BOQ categories to include; default all. A category that is not in the BOQ is reported as an issue; if no line remains, `ValueError`.

## Behaviour
- Lines are sorted by `item_id` and numbered `line_no` from 1. Each line copies `item_id, category, description, unit, quantity, source, spec` from the BOQ and carries `references`, `incomplete`, `issues` and an EMPTY `response` `{unit_price, delivery_days, brand_offered, remarks}` (all `null`).
- References: for protective-device and cable lines, the candidates of the datasheet records whose requirement equals the line specification (device: kind, In, poles, breaking capacity; cable: material, insulation, conductors, sections, cores), copied verbatim (`manufacturer, family, product_id, source, catalog_status, datasheet_item_id`), unique per (manufacturer, product), sorted by manufacturer, family, product. They are acceptable references, not a selection. With datasheets given, a requestable cable or device line without reference is an issue.
- `incomplete: true` when the BOQ line has no quantity, carries issue text, or is a cable with unspecified material or insulation. Such lines are carried with their text in `issues` (also in the global `issues`), never dropped.
- `rfq_id`: `RFQ-` plus the first 12 hex digits (upper case) of the SHA-256 of the canonical JSON of board name and supplier names (no clock, no random value). Same board and suppliers give the same id.
- `comparison_template`: `{suppliers: [names], response_fields, columns, rows}`: the blank matrix a person or a later tool fills; `columns` = line_no, item_id, description, unit, quantity, then `<supplier>: <field>` for every supplier; `rows` = one per line with `quotes: {supplier: {field: null}}`.
- `terms` echoes the validated terms; nothing is added.

## Data and provenance
No data table: the engine holds no catalog or norm value, so there is no norm register file and `norm_records` is always `[]`. The catalog status of each reference is copied as given (all `unverified` today); the request stays a draft.

## Not modelled
Sending the request, reading supplier answers, price comparison, award, scoring, partial quantities, alternates, taxes, incoterms, attachments.

## Depends on
Nothing (standard library). It never imports a discipline, the platform, the web or another engine.

## Tests
`python -m unittest discover -s tests` or pytest from this folder (every engine `src/` on `PYTHONPATH`, as the gate does).
