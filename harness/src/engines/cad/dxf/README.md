# epc-dxf

The catalog of DXF layers every drawing is delivered with: name, colour, line weight, line type and state per role (`sld.diagram`, `sld.text`, `plan.ELEC-LUM`...).
Sources, the later winning role by role: `harness/config/dxf/layers.json` (the default and the file to edit; `text.json` there holds the typeface, text heights and tray blocks, `unify.json` the final names; see its README), the global file in `EPC_LAYERS_JSON` (the MASTER edits it in the console), files passed to `layers.load` (later: the project's).

Deliverable service: `deliverable.convert(svg)` turns an SVG in development into the DXF (symbols as blocks, strokes, colour and weight, layer by `data-layer` role); `package.deliver(sheets, out_dir, name)` does it for
several sheets and writes `<name>_entregable.json`. SVG roles: `roles.tag_iram_sheet` marks the IRAM template; generators mark their own elements. See ADR-0023.

Verification (read-only): `verify(doc_or_path, *, min_length, off=())` reports advisory findings of a DXF without changing it: zero-length and tiny lines (shorter than `min_length`, in drawing units, required: no default), duplicated lines, entities on layers that are not defined, inserts of blocks that are not defined and empty texts. Each finding has a rule id (switchable with `off`), a severity, the entity handle, where it is (layout or block) and a text in English and Spanish. `ok` is false only for findings of severity `error`. Nothing blocks and nothing is written; counts are exact and each rule keeps at most 200 findings.
