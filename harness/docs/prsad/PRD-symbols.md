# PRD — One symbol engine for the whole harness (`epc_symbols`)

Version 0.2 · 2026-11-21 · Status: **direction approved by the owner (one `epc_symbols`, segmented by domain, migrated in parts); details pending review** · Priority: **first in the backlog (`SYM-00`)**

## 1. Purpose

Every symbol that any engine draws comes from one place, `epc_symbols`, and is inserted as a **block** (a named, reusable definition with its attributes), never redrawn as loose strokes. Engines ask for a symbol by id and context; they never draw one themselves.

## 1b. How a diagram is produced today (read from the code, 2026-11-21)

1. **Library.** `epc_symbols` holds, per library, an SVG and a DXF block per symbol (`291_E_LV_SLD_IEC60617_<name>`) and a `_catalog.json` (id, titles, text slots).
2. **Chain of symbols.** The calculation engine (`epc_aea90364`) decides, per circuit, the ordered chain of symbol ids (for example `lv_mccb_basic`, `lv_contactor`, `lv_thermal_overload`, `lv_motor_3ph`) with its texts (poles, In, Icu, tag), from the topology and the protection kind. No number is invented by the drawing.
3. **Working SVG.** `sld_generator.place(id, texts, x, y)` reads the symbol SVG, fills the slots and places it as a group `class="sym" data-sid="<id>"`; lines, busbar, notes, table and titleblock (`epc_titleblock`) are drawn around it. The MLD generator does the same with its own library.
4. **DXF deliverable (`epc_dxf`).** `bloques_dxf.separar` lifts the `data-sid` groups that have a DXF block out of the SVG; the rest is converted as strokes; `bloques_dxf.insertar` imports each block once and places one `INSERT` per occurrence with attributes and `291-*` layers.
5. **PV single-line of the plant** is a separate path: `pv_diagrams` writes DXF directly with ezdxf and imports blocks by full file name, for four symbols only.

The defect of problem 1 below is in step 4: the id of step 3 never matches the file name, so nothing is lifted out and everything becomes strokes.

## 2. Problem (verified on 2026-11-21, read-only)

1. **The blocks of the library are not used in the SLD and MLD deliverables.** A simulation (`sim-18`) produced SLD and MLD DXF sheets with 0 `INSERT` entities and no symbol definitions: every symbol is exploded into lines and polylines. Probable cause: the generators tag a symbol as `lv_mccb_basic`, while `epc_dxf.bloques_dxf._bloque_disponible` looks for `lv_mccb_basic.dxf`; the library file is `291_E_LV_SLD_IEC60617_mccb_basic.dxf`. The two never match. The generator already tries both names for the SVG (`sld_generator.sym_file`); the DXF step does not.
2. **A second, unrelated symbol catalogue.** `epc_plan` has its own `symbols.json` (31 symbols: luminaire, receptacle, board, transformer, motor, earthing, door, window, fire and security devices...) drawn from its own primitives. Some mean the same thing as symbols already in `epc_symbols` (`socket_outlet`, `lighting_load`, `transformer_2w`, `motor_3ph`, `earth_pe`) with no link between them.
3. **A third one in architecture.** `epc_arch/biblioteca` holds 25 furniture and fixture symbols; `epc_arch/svgout.py` and `export_dxf.py` draw walls, doors and windows with their own primitives.
4. **Photovoltaic drawings draw by hand.** `pv_diagrams`, `pv_roof` and `pv_details` use library blocks for four symbols only (`inverter`, `pv_module`, `dc_disconnect`, `energy_meter_kwh`); the LV/MV station, collector, tables, combiner and protection are boxes and polylines. There is no PV domain in the library.
5. **Silent fallback.** `pv_diagrams._symbol` returns `False` for a missing symbol and the caller draws a plain box without any warning.
6. **Gaps in the library.** `mld-mv-symbol` has only a catalogue and `ssd-mv-symbol` only one SVG, with no DXF block.
7. **No guard.** No test or gate check fails when an engine draws a symbol outside the library.

## 3. Goals

- G1. One package, `epc_symbols`, is the only source of symbols (ADR-0012, one source of truth per datum).
- G2. Every drawing engine inserts symbols through one API; no engine owns a symbol file or a symbol table.
- G3. DXF deliverables carry symbols as blocks with attributes (one definition per symbol, one `INSERT` per occurrence).
- G4. The library is organised by **domain** and **view**, so the same meaning can have a different drawing per view without duplicate ids.
- G5. A gate check fails the build when a drawing draws a symbol outside the library or when a requested symbol does not exist.
- G6. No symbol is reinvented: a missing one is added to the library (and recorded in the catalogue), never drawn in the engine.

## 4. Non-goals

- Site geometry that is not a symbol (walls, roads, the table grid of a plant, cable routes) stays in the engines.
- Titleblock frames and logos stay in `epc_titleblock`.
- No change to norm values, golden files or calculation results (`SYM-00` to `SYM-06` change drawings only).
- No standards text or figures are copied. A symbol is our own drawing; the catalogue records only the symbol identifier and its title (owner rule on copyrighted material).

## 5. Design

### 5.1 Domains and views

| Domain | Content | Views |
| --- | --- | --- |
| `electrical-lv` | protection, switching, metering, motors, loads (today `sld-lv-symbol`, `mld-lv-symbol`) | `sld`, `mld` |
| `electrical-mv` | cells, MV breakers, relays, earthing devices (today `sld-mv-symbol`; `mld-mv` and `ssd-mv` to be completed) | `sld`, `mld`, `ssd` |
| `photovoltaic` | module, string, combiner, inverter, optimizer, tracker, DC protection, rapid shutdown, LV/MV station | `sld`, `mld`, `layout` |
| `electrical-plan` | luminaire, receptacle, board, junction box, outlets, ELV and security devices as drawn on floor plans (today `epc_plan/symbols.json`) | `plan` |
| `architecture` | doors, windows, furniture, fixtures (today `epc_arch/biblioteca`) | `plan`, `3d` |

A symbol has one stable id (`<domain>.<name>`), one meaning, and one drawing per view. The plan-view luminaire and the SLD `lighting_load` are two views of related meanings, linked by a `relates_to` field, not two catalogues.

### 5.2 Catalogue

One generated catalogue (`_catalog.json` per domain, already present for the electrical libraries) is the single index: id, titles in English and Spanish, domain, views, terminals (connection points with names and directions), attributes (the slots a drawing fills: tag, rating, poles...), nominal size, source file, standard identifier, status. `catalogo_simbolos.xlsx` becomes a generated view of it, not a second source.

### 5.3 API (`epc_symbols`)

```
resolve(symbol_id, view)          -> SymbolRecord (raises UnknownSymbol, never returns a stand-in)
svg_fragment(symbol_id, view)     -> element ready to place, with its terminals
dxf_block(symbol_id, view)        -> block definition name, imported once per document
insert(doc, symbol_id, view, at, scale, layer, attribs) -> INSERT entity
terminals(symbol_id, view)        -> connection points, so engines connect lines without redrawing
list(domain=None, view=None)      -> ids
```

Id aliases of the old names (`lv_mccb_basic`, `291_E_LV_SLD_IEC60617_mccb_basic`, `mccb_basic`) resolve to the same record, so the old generators keep working during the migration.

### 5.4 Rules the engines follow

- An engine never opens a symbol file and never builds the file name; it calls the API.
- A missing symbol is an error with a clear message (English and Spanish), not a plain box.
- Layers of inserted blocks follow `epc_dxf` layer roles (no layer names in `epc_symbols`).
- Block names carry the library prefix and the id, one definition per document.

## 6. Plan (migration in parts: one pull request per phase, gate green before the next)

The owner approved the direction and asked for the migration to go in parts (2026-11-21). Order: SYM-00 first and alone; SYM-01 and SYM-02 next (they remove the cause of SYM-00); SYM-03, SYM-04 and SYM-05 are independent of each other after SYM-01 and can be reordered or paused; SYM-06 and SYM-07 last.

| Id | Phase | Result | Acceptance |
| --- | --- | --- | --- |
| SYM-00 | Fix the DXF block lookup in the SLD and MLD path | The deliverables carry `INSERT` blocks | A test generates an SLD and an MLD and fails if the count of `INSERT` is 0 or any known symbol appears as loose strokes |
| SYM-01 | Catalogue schema and API in `epc_symbols` (5.2, 5.3), with aliases | `resolve/insert/terminals` over the five existing libraries | Unit tests on every public function; catalogue validates against its schema; every existing file is in the catalogue |
| SYM-02 | SLD and MLD generators use the API | Path and name guessing removed from `sld_generator`, `mld_generator`, `bloques_dxf` | Existing SLD/MLD tests pass; no engine builds a symbol file name |
| SYM-03 | `photovoltaic` domain and PV drawings | Station, collector, combiner, string, tracker, protection and meters exist as symbols; `pv_diagrams`, `pv_details` insert them; the silent box fallback is removed | PV single-line sheet has no box standing for a symbol; missing symbol raises |
| SYM-04 | `electrical-plan` domain | The 31 symbols of `epc_plan` move into `epc_symbols` as plan-view blocks; `epc_plan` calls the API; `symbols.json` is deleted by a reviewed change | Plan DXF equals the old one geometrically (characterization test) with blocks instead of strokes |
| SYM-05 | `architecture` domain | The 25 `biblioteca` symbols and the door and window drawings move; `epc_arch` calls the API | Architecture DXF/SVG characterization tests pass |
| SYM-06 | Complete `electrical-mv` | DXF blocks for `mld-mv` and `ssd-mv` | Every symbol listed in the catalogue has an SVG and a DXF block |
| SYM-07 | Gate guard | New gate check: no drawing engine draws a symbol outside `epc_symbols`; deliverable DXF files of the golden projects have `INSERT` blocks; every symbol id used in the code exists | The check fails on a seeded violation (negative test), passes on `main` |

SYM-00 can go first and alone: it is a small fix that already makes the deliverables correct. SYM-01 and SYM-02 follow because the API removes the cause of SYM-00 (two places building a file name). The domain moves (SYM-03 to SYM-06) are independent of each other after SYM-01.

## 7. Risks

- **Golden and characterization files change** when strokes become blocks. They are never edited (D27): the comparison is geometric (the same lines in the same place) and a new golden is requested from the owner only through the normal review.
- **Scale and anchor differences** between the plan symbols (sized by drawing scale) and the SLD symbols (fixed size). The catalogue carries a nominal size and an anchor point; plan blocks are inserted with a scale.
- **Block names and CAD tools.** Some CAD programs treat attributes differently; check with the owner's CAD software before closing SYM-00.
- **Size of the work in SYM-04 and SYM-05.** Both move code that draws walls and rooms; they stay separate pull requests with their own characterization tests.

## 8. Metrics

- `INSERT` blocks per deliverable DXF: greater than 0 for every sheet that has a symbol.
- Symbol files or tables outside `epc_symbols`: 0.
- Engines that build a symbol file name: 0.
- Missing-symbol fallbacks that draw a box: 0.

## 9. Open decisions (owner)

0. Decided (2026-11-21): one `epc_symbols` segmented by domain, migrated in parts.
1. Ids: keep the existing `291_E_LV_SLD_IEC60617_<name>` file names and add aliases (proposed), or rename the files.
2. Whether plan-view symbols that mean the same as an SLD symbol (luminaire, receptacle, transformer, motor, earth) share one record with two views (proposed) or stay separate records.
3. Where the generated catalogue spreadsheet (`catalogo_simbolos.xlsx`) lives after it becomes a view.
4. Whether architecture symbols belong in `epc_symbols` as their own domain (proposed, one catalogue) or stay in `epc_arch` behind the same API. The domain structure was approved; this placement is the open point.
