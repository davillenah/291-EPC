---
name: freecad
description: DISABLED (owner, 2026-11-27): the editable 3D model goes through the SolidCraft MCP; do not use this skill. Kept for reference. Builds an editable FreeCAD model (FCStd, STEP, IFC) of what the harness has already designed, for example the frames and modules of a PV plant on a roof or on the ground, through the `freecad` MCP server. Use when the engineer asks for the editable model or the 3D structure.
---

# FreeCAD: the editable model of what the harness designed

> **Disabled (owner decision, 2026-11-27).** FreeCAD is not used any more and is not removed: the editable 3D model goes through the SolidCraft MCP. This file is kept for reference only.

FreeCAD is optional and outside the 12 stages. This skill draws what the engines already decided; it never decides anything. The result is a working copy for the engineer to open and edit by hand. Changes made in FreeCAD do not return to the harness and are not approved.

## 1. Check the environment
- The `freecad` MCP server is declared in the repository `.mcp.json` (`uvx freecad-mcp`). It needs FreeCAD open on the engineer's machine with the MCP add-on and its RPC server started. Check that the server answers before anything else.
- If it does not answer, say so and stop. Do not simulate the model. If `execute_code_headless` is available, it may be used for the heavy operations (booleans, lofts); say it in the answer.

## 2. Where every number comes from
- Read the project through the `epc` tools or the CLI (`epc_project_status`, `epc_stage_table`) and the stage 3 result: `outputs["pv"]["layout"]` (tables, inverters and station, in metres, origin at the south-west corner, x east, y north), `outputs["pv"]["flat_roof"]["structure"]` (frames, tilt, front and rear heights, row pitch) or `outputs["pv"]["roof"]` (planes and module cells). The module size comes from the catalog block of the run.
- Never write a dimension by hand. If a value is not in the engine result, write "not available" and raise a finding; do not assume it. The only values you may choose are modelling ones (names, colours, level of detail), and you say which.
- The assumptions of the run travel with the model: "flat roof assumed", "typical values pending review", "EDIT MODE" when the project is in edit mode.

## 3. Model
- One parametric Python script with the parameters at the top (millimetres), so it can be regenerated. A new document with a descriptive name; never overwrite an existing document without confirmation.
- PV plant: the roof or site slab, one frame per table (a tilted box or a simple truss: front height, rear height, tilt and width from the structure result), the modules on each frame in the engine's grid, the inverter pads and the station. One group per array; names in English.
- Buildings from `epc_arch` (walls, slabs, openings) use the Arch workbench when the engineer asks for them.

## 4. Verify
- Recompute the document: no errors, no invalid objects. Check the bounding box against the layout (site or roof size) and that no frame leaves the site or overlaps another.
- Count modules and frames in the model against the engine result. If they differ, fix the model; do not deliver it with the difference unsaid.

## 5. Deliver
- Save the `.FCStd` and export `.STEP` (parts and assemblies) and `.IFC` (BIM) next to the project in a `freecad/` folder. Never write in `inputs/`, `ssot/`, `deliverables/`, `audit/` or `.epc/`.
- Check that every file exists and is not empty. Write on each one: "editable model derived from the harness result; changes made here are not approved".
- Answer with the file paths, the main parameters and the assumptions. Explain to the engineer in Spanish.

## Language
This text is English. The answer to the engineer is in Spanish. Names inside the model are English.
