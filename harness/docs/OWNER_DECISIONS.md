# Decisions that wait for the owner

Written 2026-11-23. Each item says what it is, what the agents did not do and why, **the exact change expected if you accept**, and the words to say. Nothing here has been applied. The golden files, the norm values and the ADR status lines are never changed by an agent.

## 1. Drawing base (DRW-01)

### Stage 3, one IRAM title block: already one geometry (correction of an earlier note)
`epc_arch.export.sheet_iram` does **not** draw a second title block. It reads the SVG that `epc_titleblock` makes (`template_from_svg`) and turns its marks into items of the common drawing. The geometry has one source. What differs is only the **layer name** of the marks: `A-TITLE` in the architecture drawings, `291-G-ROTULO` (role `sld.titleblock` of `config/dxf/layers.json`) in the diagrams and sheets; at the transmittal `config/dxf/unify.json` renames layers to the `<discipline>-<element>` convention.
- Expected diff if you accept "stage 3 is closed as done": none (only the BACKLOG line changes).
- Expected diff if you want one layer name for the title block everywhere: the layer name inside every architecture DXF/SVG/PNG/PDF sheet (`A-TITLE` to the chosen name); the file bytes of every architecture sheet change, so their golden files must be recorded again.
- To decide: "close stage 3" or "rename the layer to X".

### Stage 1, one source of layers and pens
Today: `config/dxf/layers.json` holds 105 roles (`plan.*` 84, `pv.*` 17, `sld.*` 4) with name, colour, line type and `lineweight`, and **every `lineweight` is empty**; `epc_arch/epc_style.json` holds 18 `A-*` layers with a pen (five widths, 0.13 to 0.5 mm), line type and colour. The two files describe different layers, so no datum is written twice (ADR-0012 holds), but there are two places and two formats.
- Option A (recommended, no byte change): move the 18 `A-*` layers and the five pens into `layers.json` as `arch.*` roles with `lineweight` filled from the pen, and make `epc_arch` read them through its own loader with a copy-free path (the engines stay independent: the file is handed to `epc_arch` as data by the caller). Expected diff: none in any drawing, if the values are copied exactly; the test `test_characterization_*` proves it.
- Option B (changes bytes): also give the `plan.*`, `pv.*` and `sld.*` roles pen widths. Expected diff: a `lineweight` appears on those layers in every plan, PV and diagram DXF, and in the PDF that draws from them; all their golden files change. It needs your choice of the widths.
- To decide: "do Option A" (the agent does it, bytes identical) or "Option B with these widths".

## 2. Golden SYM-00: INSERT blocks in the SLD
`epc_dxf.bloques_dxf._bloque_disponible` looks for `<sid>.dxf`; the library file is `291_E_LV_SLD_IEC60617_<name>.dxf`, so the SLD of the example board has 0 `INSERT`. Checked 2026-11-22: trying both file names and taking the block name from the library file gives 42 `INSERT`, 17 block definitions and no audit error; it changes the DXF bytes, so `test_characterization_drawings` fails in 3 cases (the example boards). A second trial on 2026-11-23 on `dev` with the same idea did not change the characterization result, so the trial must be redone against the exact drawing path before recording anything; the MLD does not pass a symbol library to the conversion at all and needs its own change.
- Expected diff if you accept: the three golden drawing cases of `harness/src/engines/cad/drawing/tests/golden/` record the new DXF hashes; the SLD files gain `INSERT` entities and 17 block definitions; no value, layer or text changes.
- To decide: "do SYM-00 and record the golden files". The agent then makes the change, shows the before and after counts, and records the new golden with `engine_cases.py --write` only on your word.

## 3. `epc_documents` raises `ValueError`
The golden `harness/src/engines/quality/documents/tests/golden/documents.json` pins the text `ValueError: <Spanish message>` in 1764 strings (`ccpm_matrix` 1751, `ccpm` 11, `project` 1, `specification` 1); the engine has 61 `raise ValueError` in five modules. Converting to a `DocumentsError` with a code and `.en`/`.es` (ADR-0039) keeps the message and changes only the prefix to `DocumentsError:`.
- Expected diff if you accept: those 1764 strings change their prefix; nothing else. An alternative that changes no byte: keep `ValueError` for this engine and record the exception in ADR-0039.
- To decide: "convert and record the golden" or "keep ValueError, record the exception".

## 4. ADRs to accept
- ADR-0039 (PR #97), engine errors and results: 29 engines already follow it; status line says `proposed`.
- ADR-0041, functional and control schemes (new, 2026-11-23): `proposed`; its three questions are at its end (view of the relational model, layout convention, symbol geometry).
- To accept: say "accept ADR-0039" and/or "accept ADR-0041"; the agent edits only the status line and the index row.

## 5. IEC 60617 geometry
Six devices have a block placeholder, not a real symbol: `lv_imd`, `lv_pv_blocking_diode`, `lv_pv_power_optimizer`, `lv_pv_rapid_shutdown`, `lv_pv_rcmu`, `lv_pv_combiner_box` (DGM-03), and the 33 control symbols of `knowledge/diagrams/funcional_iec60617/` have no geometry in the library (ADR-0041 point 4). The standard is not stored in the repository: a person supplies or confirms the geometry (as SVG or DXF drawn by the owner); the agent then adds the blocks and the catalog entries.

## 6. Still blocked by the above or by a person
DGM-02 (optional model path of the SLD/MLD, more constraints each confirmed by a person), DGM-07, DGM-11 to DGM-15 (they depend on ADR-0041, on confirmed norm values and on the roster duties, which are the owner's).
