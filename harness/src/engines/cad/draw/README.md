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

## Architecture recognition (`epc_draw.arch`)


Architecture recognition: a plan that arrives as a DXF, a vector PDF or an image becomes walls (with their own thickness), doors, windows, openings and rooms, and a clean SVG with layers to work on.
One reader per source (`epc_draw.arch.sources`: DXF, vector PDF, raster image) turns the file into the same primitives (lines, arcs, blocks); the recognizers (`epc_draw.arch.recognizers`) only know primitives, so a new source is a new reader and nothing else changes.
`epc_draw.arch.recognize(data, name)` returns an `Architecture` (JSON-able) and the SVG. Thresholds are data (`params.json`). Depends on `ezdxf`, `numpy`, `pillow` and `pypdfium2`; on no other engine package.
Run: `python -m epc_draw.arch plan.dxf --out DIR` (`--background` draws the original linework faintly underneath).

Drawing a building from a description (`epc_draw.arch.author`): rooms given as rectangles in metres (`box_m` between wall axes, a code and a name each), a wall thickness, and doors and windows by room and side (`N`, `S`, `E`, `W`) become an `Architecture` (`architecture_of`) and a plan on an IRAM sheet (`plan_dxf`, layers and typeface of `epc_style.json`). The plan writes each room's tag (`PB-01 · 53,0 m²`) under its name, so `recognize` reads the same rooms, codes and names back. Nothing is assumed: thickness, boxes and widths are inputs. `python -m epc_draw.arch.author DESCRIPTION.json --out DIR` writes one DXF per floor.

Presentation (`epc_draw.arch.presentation`, `epc_draw.arch.isometric`): every authored plan is a presentation sheet. Doors and windows are blocks (`EPC_DOOR_<hash>`, `EPC_WINDOW_<hash>`, equal shapes share one) with a wipeout (layer `291-A-ANNO-NPLT`) that cleans the wall behind them. The plan carries chains of dimensions between wall axes (south and east, and the overall one), the tag and width of each door and window (`D-01`, `V-01`), the room schedule, the opening schedule and the general notes, all in English and Spanish, at the biggest standard scale that fits beside the panel. With `heights_m` in every floor (`wall_height_m`, `door_head_m`, `window_sill_m`, `window_head_m`, `slab_m`, `elevation_m`; never assumed) `author` also writes `ISO.dxf` (isometric of the whole building, floors at their levels, roof left out), `ELEV_S_<floor>.dxf` and `SEC_A_<floor>.dxf`; without them it says so. Sizes (offsets, steps, panel width, shades) are in `epc_style.json` (`presentation`). Only authored plans get this: the plans of a client are shown as they are. The extra sheets reach the transmittal through `engine_inputs.building.presentation_sheets` (`03_ARCHITECTURE/`).

Review of a plan (`epc_draw.arch.review`): `connections` says which rooms each door, window and opening joins (an empty id is the outside); `notes` lists what is worth a second look (a room no door reaches, a room with no name, a code on two rooms, a written area that differs from the measured one by more than `review.area_tolerance`). `python -m epc_draw.arch plan.dxf --review` writes `NAME.review.json`. They are notes about the drawing, not a check against a standard.

Elevations and sections (`epc_draw.arch.sections`, ADR-0032 decisions 3 and 4): derived from a plan (read or authored) and the heights the person gives for the floor (`wall_height_m`, `door_head_m`, `window_sill_m`, `window_head_m`, `slab_m`, `elevation_m`: all required, none guessed). `elevation(arch, "S", heights)` is the floor seen from a side (N, S, E, W): the walls in sight, the doors and windows of the walls that face it, the ground and the slab. `section(arch, "x", 12.0, "E", heights)` cuts with a vertical plane (x or y, in metres of the plan) and looks one way: cut walls and slabs solid, the door or window the plane passes through left open, the walls beyond with their openings, the cut rooms named. `stack` puts the views of several floors at their levels. `view_drawing` / `view_dxf` draw a view on the sheet at a standard scale (layers of the style; what is seen beyond the plane goes on `291-A-ELEV-N`). Limits: walls along the two directions of the plan, one height per floor, the slab as roof, no stairs.

The building in 3D (`epc_draw.arch.model3d`): `building_solids(arch, heights)` gives the walls of a floor as boxes, open at each door (the wall goes on above the head) and each window (under the sill and above the head, with the glass between), the slab under and over the floor and a plate per room; `building_scene([(arch, heights), ...])` puts the floors at their levels. The scene is plain data (vertices and quads, metres, y up as in CAD, z from the level of the project), the same that `epc_plan.solid.scene` gives for raceways and pipes, so `epc_plan.scene3d` shows both together. Same heights as the sections; nothing is guessed.

Wall thickness: of the two ways to find a wall (a thick stroke, or two strokes a wall's thickness apart) the one whose thickness puts more ink on a single value wins; a band wins unless the pairs have clearly more (`pairs_win` in `params.json`), so the thick outline of a filled wall does not pass for a band. One thickness per plan: a plan with exterior walls twice as thick as the interior ones reads them as two thin walls.

Annotations (`recognizers/annotations.py`): grid axes (chains of dashes with no wall face beside them) with their bubbles, dimension lines (crossed by oblique ticks, with their figure and extension lines) and labels (a text and the small group of strokes that holds it: the box, hexagon or circle of a tag and its leader) are not walls, but they are not rubbish: they are taken out before walls are read and kept in layers of their own (`291-A-GRID`, `291-A-ANNO-DIMS`, `291-A-ANNO-IDEN` in the SVG, `annotations` in the result, `annotation_counts` in the JSON). The architecture discipline of the platform shows them; every other discipline hides them and sees only walls, doors and windows. The original faint linework (`291-A-ANNO-REFR`) no longer repeats them. They are found from a text layer, so an image has none. A stroke on a layer named as walls, doors or windows is never an annotation, and the box of a label is about the size of its text (`box_to_text`): the corner of a building between two windows, with the name of the room inside, is wall. A DXF `CIRCLE` is read as a whole turn (the bubble of an axis, a round tag). A PDF whose arcs are written in many short pieces (some programs write them dashed) gets them welded back into one arc, so that door swings are found.

Sheets: a drawing sheet (plans of several floors, section, elevation, frame, title block) is taken apart before anything is recognized (`recognizers/sheet.py`). The frame with its title block (the group of strokes that spans the sheet and holds the others) is left out; the strokes that touch form a view, and views drawn close together are separated where fewest strokes cross. Each view is read on its own, with its own wall thickness; those with rooms and doors are plans (sections, elevations and tables are left out). The floor of each plan is the title that sits near it (`PLANTA BAJA`, `PLANTA ALTA`, `PLANTA 2`, `SUBSUELO`...; the patterns are `levels` in `params.json`; DXF text and PDF text layers are read, an image has none), else the plans are numbered in reading order and the result says so. All floors share one frame: each is laid over the lowest by its walls and the frame starts at the corner of what they cover, so a point has the same coordinates on every floor (`reference`). `recognize_sheet(...)` returns one result per floor, from the lowest; `recognize(...)` returns the lowest. The CLI writes `NAME.L0.architecture.json/.svg`, `NAME.L1...` (or `plan1`, `plan2`) and `NAME.sheet.json`, and `NAME.architecture.*` is the lowest floor. A file with no frame and no plan titles is one plan, as before.

How a plan is read:
- Walls by their shape: a long box of about one width with straight unbroken faces, whatever its colour or fill (solid, hatched or a bare outline). A picture is read several ways (thick strokes, lines, outlines and hatching shut into bands, neutral or dark ink only, every mark on the paper, walls at 45 degrees) and the reading that closes the plan into the most rooms is kept. Each wall keeps its own thickness; on a DXF wall layer, partitions thinner than the main walls are walls too.
- Walls are tidied into a network: two directions, shared axes, corners and T joins closed. Structural axes (long thin lines crossing each other) and the sheet frame are left out.
- Doors by their shape: a leaf square to the wall from a jamb and the quarter circle it sweeps, looked for at every wall end and every door width; the arc reaches both ends, the space it sweeps is empty, the doorway is not wall, and the doors of one plan are of similar widths. Windows: thin lines across a gap in an outside wall.
- A corridor that ends in a window: the stretch between the two walls that close the corridor looks like a passage between walls, but when thin panes run across it and the outside lies beyond, it is a window (otherwise the corridor stays open to the outside and is not a room).
- Rooms: what the walls, with their doors and windows shut, close. Sheets with several views keep the view with rooms and doors (the plan). A PDF's written scale ("ESCALA 1:50") gives metres.

Every line of the SVG is a hairline of 0.05 mm of paper (at the written scale, 1:100 when none is written) and a wall is a coloured rectangle of its real thickness: `render` in `params.json`. The SVG follows architectural drawing conventions: cut walls solid with closed corners, windows shut (frame and glass), doors open with a dashed swing, plain openings dashed, rooms tinted with their area, and a footer with title, scale, graphic scale and counts. Layers: `ARQ-AMBIENTES`, `291-A-WALL-FULL-N`, `291-A-SECT`, `291-A-DOOR-N`, `291-A-GLAZ-N`, `291-A-WALL-JAMB-N`, `0-Titleblock`.

Limits: renders and photos are refused; a raster image reads horizontal, vertical and 45-degree walls only; text, dimension lines and hatching are ignored, not read; sizes are in plan units unless the source gives its units or scale.

Training tools (in `scripts/`): `registrar_muestras.py` (sample registry by SHA-256, samples never go to git), `generar_salidas.py` (`out/out_NN.svg` per sample), `informe_aprendizaje.py` (`out/aprendizaje.html`), `planta_prueba.py` (a designed house with known truth, as SVG, DXF and PNG), `generar_biblioteca.py` (furniture symbols in `epc_symbols/library/arch-symbol/`). What was learned from the samples and books: `epc_symbols/library/arch-symbol/REPERTORIO.md`.

The old name `epc_arch` is a door to this package.

## PV drawings (`epc_draw.pv`)

The photovoltaic drawings: ground and roof layouts, the parts detail, the 3D model and the FreeCAD macro (`epc_draw.pv.diagrams`, `roof`, `details`, `model3d`, `roof_model3d`, `freecad`, `parts`; one call `epc_draw.pv.draw.draw_pv(PvDrawInput, ...)`). The old names `epc_drawing.pv_<name>` are a door to these modules. They still raise `epc_drawing.errors.DrawingError` until the reports of `epc_drawing` find their place (owner decision pending).
