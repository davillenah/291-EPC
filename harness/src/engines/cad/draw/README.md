# epc-dxf

The catalog of DXF layers every drawing is delivered with: name, colour, line weight, line type and state per role (`sld.diagram`, `sld.text`, `plan.ELEC-LUM`...).
Sources, the later winning role by role: `harness/config/dxf/layers.json` (the default and the file to edit; `text.json` there holds the typeface, text heights and tray blocks, `unify.json` the final names; see its README), the global file in `EPC_LAYERS_JSON` (the MASTER edits it in the console), files passed to `layers.load` (later: the project's).

Deliverable service: `deliverable.convert(svg)` turns an SVG in development into the DXF (symbols as blocks, strokes, colour and weight, layer by `data-layer` role); `package.deliver(sheets, out_dir, name)` does it for
several sheets and writes `<name>_entregable.json`. SVG roles: `roles.tag_iram_sheet` marks the IRAM template; generators mark their own elements. See ADR-0023.

Verification (read-only): `verify(doc_or_path, *, min_length, off=())` reports advisory findings of a DXF without changing it: zero-length and tiny lines (shorter than `min_length`, in drawing units, required: no default), duplicated lines, entities on layers that are not defined, inserts of blocks that are not defined and empty texts. Each finding has a rule id (switchable with `off`), a severity, the entity handle, where it is (layout or block) and a text in English and Spanish. `ok` is false only for findings of severity `error`. Nothing blocks and nothing is written; counts are exact and each rule keeps at most 200 findings.

## Symbols (`epc_draw.symbols`)

The IEC 60617 symbol library (SVG and DXF blocks, catalogs) for single-line and multi-line diagrams, LV and MV: `epc_draw.symbols.library_dir(kind)`, `resolve`, `placeholder`, `list_ids`, `terminals`, `svg_fragment`, `dxf_block`. Engines ask for a symbol by id and view and never build a symbol file name. Build scripts for the library: `tools/symbols/`. Schema: `symbols/schema/symbol_catalog.schema.json`. The old name `epc_symbols` is a door to this package.

## Title block (`epc_draw.titleblock`)


IRAM A0-A4 sheets (frame, coordinates, IRAM 4504/4508 title block, optional list of modifications) with company and client logos, as a **service**: a JSON request in, the filled sheets out.
No Excel, no subprocess, nothing written unless the caller asks.

```python
from epc_draw.titleblock import service
result = service.render({"common": {"empresa": "ACME", "cliente": "CLIENTE SA"},
                         "logos": {"provider": "logo-empresa.svg"},
                         "sheets": [{"name": "SLD_T1_H1", "format": "A1", "fields": {"denominacion": "TGBT-01", "proyecto": "PRJ-1"}}]})
svg = result["sheets"][0]["svg"]          # the sheet; <g id="dibujo"> is where the drawing goes
```
The fields are those of the title block (`service.FIELDS`); `service.project_request(titleblock_of_the_project)` turns the platform's data (company, client, who drew, checked and approved, description...) into the common part
of a request. A field nobody gives stays blank. Command line: `python -m epc_draw.titleblock.service request.json out_dir [--dxf]`; one sheet by hand: `python -m epc_draw.titleblock.sheet_generator A4 out.svg`.

The old name `epc_titleblock` is a door to this package.
