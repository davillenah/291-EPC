# ADR-0032: One model of the building, versioned as text; the 3D view is drawn from it and IFC is an output

Status: proposed. Date: 2026-11-05. Follows ADR-0008 (2D first, with ezdxf and shapely), ADR-0020 and ADR-0021 (the plan editor), ADR-0024 (coordination between disciplines) and ADR-0025 (architecture recognition).

## Context
The clients hand over a photo, a PDF or a DWG, almost never an IFC. `epc_arch` already reads a DXF, a vector PDF or an image and finds walls, doors, windows and rooms; the plan editor works in 2D and the engineering draws its routes over that plan.
The owner wants the architecture that arrives to be read and shown in the browser, always in a form git can follow (traceability), the raceways, trays, cables and motors to be placed over it, the work to stay in 2D (plans, views, cuts and sections) with the 3D model one click away at any time, and an IFC to come out at the end.

## Decisions
1. **The source of truth is a model of the building in plain text** inside the project: one JSON file for the levels (with their elevations and heights) and one per level (walls, openings, rooms, slabs). Keys sorted, fixed numeric precision, stable identifiers, nothing that changes on every run (no dates, no counters). **IFC is not the source**: an IFC file renumbers its entities each time it is written and would fill git with noise.
2. **What is read is a proposal; the person accepts it.** The recognition of `epc_arch` is shown over the original and only what the person accepts is written into the model. Each acceptance is a change with a message, like the changes of the single-line diagram (history, undo and commit message). The raw output of the recognition is a cache, not versioned; the original files that arrived are versioned as inputs.
3. **The heights are set by the person**: elevation of each level, height of the walls, sill and head of each opening. They are fields of the model that the editor asks for before the 3D can be built; a plan does not bring them and none is guessed silently.
4. **The views are derived and drawn at scale.** Plans, elevations and sections are obtained by slicing the model (shapely, already in the stack) and are drawn on the organization's sheet at a scale (1:50, 1:100...) as SVG, DXF and PDF like the other sheets. Nobody works on a full-size model on a screen: the viewer zooms.
5. **The 3D view is drawn from the same model, in the browser**, with Three.js (MIT; React Three Fiber, also MIT, if it helps). It does not need IFC. web-ifc (MPL-2.0) would only be used to open an IFC that somebody else sends.
6. **Git shows it.** The model is JSON, so a change reads element by element (a wall, its thickness, its height). Each level also gets a **preview in SVG generated from the model** (stable order and precision, no dates) and committed next to it, so a change can be *seen* in git (the hosts render SVG and compare images). The SVG is a view, never the source; the rule that an `.svg` is not a deliverable stands.
7. **The electrical elements are elements of the same model**: trays, conduits, cables, boards, motors, luminaires, with their height (the mounting heights come from the design criteria). Each discipline keeps its own file, so two disciplines never edit the same one.
8. **IFC4 is an output, generated at the end** with IfcOpenShell (LGPL; used as a library on the server, not modified): `IfcBuildingStorey`, `IfcWall`, `IfcSlab`, `IfcSpace`, `IfcDoor`, `IfcWindow` and, for the engineering, `IfcCableCarrierSegment`, `IfcCableSegment`, `IfcElectricDistributionBoard`, `IfcLightFixture` and `IfcMotor`, with their property sets. The `GlobalId` of each element is derived from its stable identifier (UUID v5), so the same model always gives the same file.
9. **Phases, each one a branch with its gate**: F1 model v1, the acceptance of what is read and the SVG previews; F2 the 3D viewer; F3 the electrical elements with their height; F4 cuts, sections and elevations; F5 the IFC export. A dependency is added only when its phase needs it.
10. **Out of this decision**: reading DWG (not needed, the owner's decision) and photos with OpenCV (later, in the backlog of the architecture engine).

## Exports of the whole building (every discipline)
When the model carries architecture, electrical, mechanical (HVAC), piping and fire protection, everything comes out of the same model; the formats are not converted into one another (a DXF is never turned into an IFC or the other way round, each conversion would lose information).
1. **DXF is the 2D output**: the plans, sections and elevations at scale on the sheet of the organization, one set per discipline. The layers come from the catalog of layers (three levels: platform, organization and project), with the layers of each discipline. Each symbol is a **block**, ideally with its **attributes** (tag, rating, system, discipline) so that a CAD user can extract schedules from it; whether today's blocks carry attributes has to be checked. A 3D DXF is not a goal: routes may go out as 3D polylines for CAD coordination, the 3D lives in the IFC.
2. **IFC4 is the 3D output**, one file per discipline and, optionally, a federated one. The spatial structure (site, building, storeys) holds every element in its storey.
   - Electrical: `IfcCableCarrierSegment` and its fittings, `IfcCableSegment`, `IfcElectricDistributionBoard`, `IfcLightFixture`, `IfcOutlet`, `IfcProtectiveDevice`, `IfcMotor`.
   - Piping: `IfcPipeSegment`, `IfcPipeFitting`, `IfcValve`, `IfcPump`, `IfcTank`.
   - HVAC: `IfcDuctSegment`, `IfcDuctFitting`, `IfcAirTerminal`, `IfcFan`, `IfcUnitaryEquipment`.
   - Fire protection: `IfcFireSuppressionTerminal`, the pipes of the network, `IfcSensor` and `IfcAlarm`.
   - Each element is assigned to its system (`IfcDistributionSystem`: electrical, ventilation, fire protection, water...) and the **ports and connections** between elements are exported (`IfcDistributionPort`, `IfcRelConnectsPorts`): in MEP the route as a graph is the most valuable part.
   - Properties: the standard sets of each class and a set of the platform with the results of the calculation (current, section, voltage drop, flow, diameter).
   - Geometry: simple and light (pipes, cables and trays as sweeps of the size the calculation gave; equipment as boxes until there is a library of 3D families).
3. **Tables** (cable list, load schedule, quantities) in CSV or XLSX are a third output of the same model.
4. **A table of correspondences per discipline, as data**: type of element -> layer and block in the DXF -> class, predefined type and properties in the IFC. It lives in the catalog of the organization like the layers, so each company can adjust names of layers, blocks and properties; adding a discipline is adding its element types and its table (the norm or the catalog gives data, the engine gives algorithms).
5. **Difficult parts, to keep in view**: generating the fittings and connections (elbows, tees, reducers) from the routes; validating the files with real viewers (BIMvision, Blender with BlenderBIM, the buildingSMART validation service and, if possible, Revit); units and shared coordinates between disciplines.

## Consequences
- The heights become required data of a building; until they are set the plans work as today and the 3D is not offered.
- The model is a new contract between the architecture engine, the plan editor, the views and the export: it carries a schema version.
- Sections and elevations are real work; at scale they are sheets, not a model on a screen.
- Three.js and IfcOpenShell are new dependencies, taken only in their phase and recorded in the licenses list (MIT and LGPL; an IFC from third parties would add MPL-2.0).
- A reading mistake of the recognition can no longer pass unseen into the 3D or the IFC: the acceptance step is where it is caught.

## Open questions
- How the levels of a building with several sheets are aligned in one coordinate system.
- Who may accept what the recognition proposes, and whether an acceptance needs a second person.
- Whether the previews in SVG are committed with each acceptance or only on request.
- Whether the blocks of the DXF symbols carry attributes today, and which properties each discipline must carry.
- Whether the federated IFC is generated by default or only on request.
