# ADR-0040: One public entry point for the MLD, the plan, the architecture reader and the PV drawings

Status: accepted under the owner's standing authorization of 2026-11-23 (verbs `draw`, `draw_plan`, `draw_pv`; the PV drawings stay in `epc_drawing`; golden drawings are never re-recorded). Implemented for the MLD, the plan and the PV drawings; the architecture 3D calls are pending (BACKLOG OPT-02). Applies ADR-0038 (engines are called functions) to the four engines it left for later (OPT-02, DGM-16).

## Context
ADR-0038 asks every engine for one public entry point that receives all its data and answers. The SLD has it (`epc_sld.draw` with `SldInput`). The others, as they stand today:

- **MLD** (`epc_mld`): `generate(data, calc, out_dir, name, lib, maxw, stamp_date, ...)` is already one function, but `data` and `calc` are loose dicts and `lib` is a folder it reads from.
- **Plan** (`epc_plan`): a drawing takes two calls, `core.process(document, params, rules)` and `dxfout.write_dxf(result, path, ...)`; the 3D model takes more (`solid.solids`, `detail.parts`, `scene3d.write_dxf`).
- **Architecture reader** (`epc_arch`): `recognize(data, name, options)` and `recognize_sheet(...)` read a plan; the 3D solids come from `model3d.building_solids` and the sections from `sections`. The command line (`cli_v2`) is the adapter that fetches the sheet and writes the manifest.
- **PV drawings** (`epc_drawing.pv_roof`, `pv_details`): the stage `pv_drawings` calls them by module.

Each of them has an `api.py` door (COD-02), so what is missing is not a door but one call per job with a typed input.

## Proposal
1. **One verb per job, same shape as the SLD:** `epc_mld.draw(entrada, out_dir, name)`, `epc_plan.draw_plan(entrada, out_dir, name)`, `epc_drawing.draw_pv(entrada, out_dir, name)`; `epc_arch.recognize` stays the one entry of the reader. `entrada` is a frozen dataclass (COD-22) with the assembled data, the title block, the date and the options. The old names stay as thin aliases until nothing calls them.
2. **Same bytes first.** Each conversion starts with a characterization test of today's output (COD-13) and ends with the same test passing unchanged. A conversion that changes a drawing is not this decision; it goes through the golden review.
3. **No self-sourced input** (ADR-0038, point 2): the library folder, the layer file and the text style travel inside `entrada`, not through environment variables (this closes COD-04 for `epc_dxf` as each drawing engine stops reading them).
4. **Order:** MLD (already closest), then the plan (two calls into one), then the PV drawings, then the architecture 3D calls. One pull request each.

## Decisions for the owner
- Names of the verbs (`draw`, `draw_plan`, `draw_pv`) or others.
- Whether the PV drawings stay inside `epc_drawing` or become an engine of their own (they are the only drawing code there that does not belong to the assembler).
- Whether the golden drawings may be re-recorded if a conversion cannot keep the bytes (the default is no).

## Consequences
- The pipeline calls four functions instead of a dozen module paths, and the engine contracts (GEN-09) can list their inputs from the dataclass.
- The cost is a typed input per engine and the aliases during the move.
- Converted so far: the MLD, the plan and the PV drawings (same bytes, characterization tests unchanged).
