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

## Single-line diagram (`epc_draw.sld`)


Single-line diagram of a board on IRAM sheets (SVG and DXF per sheet, plus the circuit table). It only draws: the calculation (`SLD_CALC_JSON`, `SLD_CALC_DETAIL`) and the board figures (`SLD_FIGURES_JSON`) come from `epc_aea90364`. Use it through `epc_drawing.board_design`.
Needs `epc_aea90364`; the symbols, the title block (it asks for its sheets) and the deliverable are in `epc_draw`. Example workbook: `examples/sld/`.

The old name `epc_sld` is a door to this package.

## Multi-line diagram (`epc_draw.mld`)


Multi-line diagram of a board: each line of the single-line expanded into its conductors (L1 L2 L3 N) at a uniform pitch, with the MLD symbols. It only draws what `epc_aea90364` calculated.
Needs `epc_aea90364`, `epc_symbols`, `epc_titleblock` (it asks for its sheets) and `epc_dxf` (the deliverable). It does not need `epc_sld`.

The old name `epc_mld` is a door to this package.

## Plan (`epc_draw.plan`)


Plan-drawing engine: nodes and lines drawn over a plan become a graph with correlative tags, circuit routes (moment-method lengths), schedules and DXF. Profiles: low-voltage electrical and sanitary sewer. Pure functions; depends only on `ezdxf`.
Run: `python -m epc_draw.plan --demo`.

Coordination between disciplines (ADR-0024): `epc_draw.plan.footprint` turns a drawing into what it occupies (metres, heights, free space) and `epc_draw.plan.clash` finds the clashes between footprints of different disciplines with rules that are data (`clash_rules.json`; company and project levels merge with `merge_rules`). `epc_draw.plan.occupancy` says how full a tray or a conduit is. Typical sizes are in each profile (`geom`) and limits in `params.json`; the engineer confirms them for the project.

## Raceways and pipes in 3D (`solid.py`)

From the same footprint as the clash detection (plan points in metres, width, heights from the floor of the project): a tray or a duct is a rectangle swept along its route, a conduit, a cable or a pipe a circle (its width as diameter), a board or an equipment a box. `solids(document, sheet)` gives them as data, `mesh` their faces, `scene` everything a 3D viewer needs (plain data, stable), `isometric` the edges in an isometric view for a sheet, and `write_dxf_3d` a 3D DXF (the axis of each as a 3D polyline and its body as faces, on the layer of its kind). Round or rectangular is data: `seccion` of the kind in its profile, else `solid.round_layers` in `params.json`. Nothing is calculated; fittings (elbows, tees) are not generated.

## The 3D scene of a project and its detail sections (`scene3d.py`)

`merge` joins scenes (the building from `epc_arch.model3d.building_scene`, the services of each discipline and floor from `solid.scene`) into one; `groups` lists them by discipline and layer. There is no screen: the outputs are files for CAD. `write_dxf` is the 3D model (a 3DFACE per face on the layer of its solid) and `write_obj` a Wavefront OBJ any 3D program opens. `cut(scene, axis, at_m, look, depth_m)` is the section of everything by a vertical plane: what the plane cuts, exactly (a tray is its rectangle, a conduit its circle, a wall its thickness, open at its door or window), each with its tag and the level of its middle, and the edges of what lies beyond up to a depth; `write_section_dxf` writes it as a 2D DXF in real metres (outlines closed and filled on the layer of each solid, tag and level by every cut service), to detail at any scale. A section is as detailed as the model: supports, fixings and fittings are not modelled yet, so it is the base of a fabrication detail (LOD 400), not the finished one.

## Disciplines of a building and of a plant

Each discipline is a profile (`profiles/*.json`: its kinds of lines and nodes, with the layer, the symbol and the size each is drawn with) and nothing else: the plan DXF, the footprint, the clash detection, the 3D solids and the sections work for all of them from that data. Besides low-voltage electrical, communications, instrumentation, civil and architecture there are: fire protection (`pci`: pipes, risers, sprinklers, detection, hydrants, pump, tank, alarm check valve station, fire department connection, panel), HVAC (`hvac`: supply, return and exhaust ducts, chilled, hot and condensate water, refrigerant, air handling unit, chiller, cooling tower, boiler, pumps, fan coils, VAV boxes, fans, fire dampers, duct and water risers), sewer (`sanitaria_cloacas`: pipes, vents, stacks, chambers, floor drains, sump), storm drainage (`sanitaria_pluvial`: gutters, roof drains, downpipes, pipes, chambers, gratings), cold and hot water (`sanitaria_agua`: pipes, risers, tanks, pumps, heaters, valves, fixtures), gas (`gas`: pipes, risers, meter, regulator, valves, appliances) and mechanical (`mecanica`: process, compressed air and steam pipes, pipe racks, tanks, pumps, compressors, heat exchangers, valves, conveyors, cranes, lift and goods-lift shafts, escalators). A riser, a downpipe or a shaft is a node of a `vertical` kind: it stands one storey high (`altura_m`) until the person writes its height on it. The sizes in a profile are what an element is drawn with until the person writes its own (`ancho_m`, `alto_m`, `z_m`): they are not design values, and the new profiles carry no calculation and no norm.

## The fabrication model (`detail.py`, towards LOD 400)

`parts(solids)` turns every run into what it is built from: its straight pieces with their cut length, a mitred elbow at each bend (with its angle), a tee where a run ends on the side of another of its discipline and a reducer where two runs of different size meet end to end. `supports(solids, spec)` hangs the horizontal runs from the slab above: a trapeze (two rods and a channel) for trays and ducts, a rod and a clamp for pipes, no further apart than the spacing. `takeoff(parts)` adds it all up: straight lengths by size, fittings by type, size and angle, supports by type with the rod they need. `detail.scene` is the scene of the parts, the supports and the equipment, so the 3D DXF and the sections show them; a section (`scene3d.write_section_dxf`) writes by every cut service its tag, size, level and bottom level, and a chain of dimensions between the services and the ends of the building. Design values are inputs and none is assumed: the spacing of the supports and the underside of each slab (`spec`). The sizes parts are drawn with (leg of an elbow, rod, channel) are drawing data in `params.json` (`detail`) that `spec` overrides. Not there yet: flanges, couplings and covers, fixings to the structure, supports of vertical runs, splitting the main run at a tee, and hidden lines in what is seen beyond a cut.

The old name `epc_plan` is a door to this package.
