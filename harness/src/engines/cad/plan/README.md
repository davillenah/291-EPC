# epc-plan

Plan-drawing engine: nodes and lines drawn over a plan become a graph with correlative tags, circuit routes (moment-method lengths), schedules and DXF. Profiles: low-voltage electrical and sanitary sewer. Pure functions; depends only on `ezdxf`.
Run: `python -m epc_plan --demo`.

Coordination between disciplines (ADR-0024): `epc_plan.footprint` turns a drawing into what it occupies (metres, heights, free space) and `epc_plan.clash` finds the clashes between footprints of different disciplines with rules that are data (`clash_rules.json`; company and project levels merge with `merge_rules`). `epc_plan.occupancy` says how full a tray or a conduit is. Typical sizes are in each profile (`geom`) and limits in `params.json`; the engineer confirms them for the project.

## Raceways and pipes in 3D (`solid.py`)

From the same footprint as the clash detection (plan points in metres, width, heights from the floor of the project): a tray or a duct is a rectangle swept along its route, a conduit, a cable or a pipe a circle (its width as diameter), a board or an equipment a box. `solids(document, sheet)` gives them as data, `mesh` their faces, `scene` everything a 3D viewer needs (plain data, stable), `isometric` the edges in an isometric view for a sheet, and `write_dxf_3d` a 3D DXF (the axis of each as a 3D polyline and its body as faces, on the layer of its kind). Round or rectangular is data: `geom.seccion` of the kind in its profile, else `solid.round_layers` in `params.json`. Nothing is calculated; fittings (elbows, tees) are not generated.

## The 3D scene of a project and its detail sections (`scene3d.py`)

`merge` joins scenes (the building from `epc_arch.model3d.building_scene`, the services of each discipline and floor from `solid.scene`) into one; `groups` lists them by discipline and layer. There is no screen: the outputs are files for CAD. `write_dxf` is the 3D model (a 3DFACE per face on the layer of its solid) and `write_obj` a Wavefront OBJ any 3D program opens. `cut(scene, axis, at_m, look, depth_m)` is the section of everything by a vertical plane: what the plane cuts, exactly (a tray is its rectangle, a conduit its circle, a wall its thickness, open at its door or window), each with its tag and the level of its middle, and the edges of what lies beyond up to a depth; `write_section_dxf` writes it as a 2D DXF in real metres (outlines closed and filled on the layer of each solid, tag and level by every cut service), to detail at any scale. A section is as detailed as the model: supports, fixings and fittings are not modelled yet, so it is the base of a fabrication detail (LOD 400), not the finished one.
