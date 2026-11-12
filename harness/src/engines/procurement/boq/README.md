# epc_boq

Status: **in development**

Procurement engine (MIG-39c, PRD section 12 stage 15, "Documents and lists"): builds the draft bill of quantities (computo) of a calculated board. QUANTITIES ONLY: no prices and no costs (the cost engine is planned for a later phase). Pure functions, standard library only, no I/O at import and no file output. It has tests but stays `in development`: no document renderer consumes the bill yet. Its outputs are drafts (D21).

## Public API
- `build_boq(board_name, circuits, *, allowance_pct, terminal_totals=None, round_up_m=False)`: dict `{board, allowance_pct, round_up_m, items, totals, assumptions, norm_records, issues}`.
- `render_rows(boq)`: flat list of dicts, one per line (`board, item_id, category, description, unit, quantity, source, basis, issue`). No file is written.

Every item: `{item_id, category, description, unit, quantity, source, basis, spec, issues}`. Categories and ids: `cable` (`CAB-001`...), `protective_device` (`DEV-001`...), `terminal_block` (`TRM-001`...), `enclosure` (`ENC-001`). Ids are assigned in category order and then in the sorted order of the specification, so the bill is deterministic. `totals` = `{lines, cable_m, devices}`. Descriptions are English text generated from the specification values; the document builders translate.

## Input format
- `allowance_pct`: REQUIRED. Wastage/allowance percentage applied to every cable length; 0 is allowed, negative is rejected, there is no default (`ValueError` asks for it).
- `circuits`: a non-empty list of objects with keys `tag` (unique text), `phases` (1 or 3), `s_mm2` (> 0) and the optional `neutral_mm2`, `pe_mm2`, `length_m`, `material`, `insulation`, `device_kind`, `in_a`, `poles`, `breaking_capacity_ka`, `description`, `device` (the last two are accepted so the terminal-list circuits can be reused; they are not used). Unknown keys, duplicate tags and invalid values raise `ValueError`.
- `terminal_totals`: optional totals of a terminal-block list, `{"by_terminal_size": {"2.5": 4, ...}}` (or the whole list, whose `totals` key is read). Plain dict, no import of the terminal engine.
- `round_up_m`: when true each cable quantity is rounded up to the next whole metre (default: exact decimals, rounded to 6 places only to remove float noise).

## Behaviour
- Cables: one line per distinct specification (material, insulation, phase conductors, phase section, and the neutral and PE sections when reported). Quantity = sum of the circuit lengths x (1 + allowance_pct / 100). Unit `m`.
- Protective devices: one device per circuit, counted per (kind, rated current A, poles, breaking capacity kA). Unit `un`.
- Terminal blocks: one line per terminal size of `terminal_totals`; terminals without a size are reported as an issue and not counted.
- Enclosure: one item per board, with its name; no sizing.
- A field that was not supplied is never guessed: the line (or the board `issues`) says `<tag>: missing <field>`. A circuit without `length_m` is not counted; a circuit with no device data at all produces `missing device` and no line; missing material, insulation or partial device data keep the line with the value `unspecified`.

## Data and provenance
No data table: the engine holds no catalog or norm value, so there is no norm register file and `norm_records` is always `[]`. Nothing to review in this engine; the inputs it receives come from engines whose values carry their own review state.

## Not modelled
Prices and costs, enclosure sizing, cable drums/standard lengths, accessories, glands, raceways, busbars, contactors and relays of a device chain, spares.

## Depends on
Nothing (standard library). It never imports a discipline, the platform or the web.

## Tests
`python -m unittest discover -s tests` or pytest from this folder (every engine `src/` on `PYTHONPATH`, as the gate does).
