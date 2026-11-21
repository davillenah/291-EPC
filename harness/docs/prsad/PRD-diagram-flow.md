# PRD — Diagram flow: analysis, netlist, cables, calculation, audit, assembly

Status: **proposed** (owner, 2026-11-21). Backlog: DGM-12 (electrical), DGM-14 (photovoltaic). Builds on ADR-0037 (relational diagram model) and the diagram assembler.

## 1. Purpose

Improve times, establish one source of truth per datum and optimize diagram generation. The diagram is not drawn from the calculation: it is assembled from separate results, each with one owner, after an auditor has judged them.

## 2. Problem

Today the calculation chooses the protection and writes it as text (`disp`); the netlist reads that text to learn which devices exist, and the assembler only reports the design constraints as advisory notes. Consequences:

- the calculation decides what the netlist should decide (which devices a load has);
- the calculation cannot size a device it does not yet know, so it guesses its type from the load;
- cable type (conductor, insulation, cores, installation) is mixed with the cross-section, which is the only cable datum that really comes from the calculation;
- nobody is responsible for saying "this is right or wrong" before the diagram exists.

## 3. Flow (electrical)

| # | Step | Owner | Input | Output | Holds values |
| --- | --- | --- | --- | --- | --- |
| 1 | Circuit analysis | design rules + typical topologies | load type, supply, environment, design criteria | list of devices per circuit (roles) | no |
| 2 | Netlist | netlist builder (`epc_drawing.diagram_model`) | the device lists | how devices, loads and wires connect, stable ids per board | no |
| 3 | Cable type estimate | design criteria | load, environment, installation | conductor material, insulation, number of cores, installation method; **no cross-section** | no |
| 4 | Calculation | engines (aea90364 and calculation/*) | netlist + cable types + loads | ratings per device (In, Icu, poles, sensitivity), cross-section, voltage drop, short-circuit | yes (only here) |
| 5 | Audit | auditor (`calc_check` is the base) | all of the above + design constraints | verdict ok / not ok, with findings per rule | no |
| 6 | Assembly | `epc_drawing.diagram_assembler` | netlist, calculation values, cable rows, IEC 60617 symbols, the verdict | the assembly: one package with everything, handed to the generators (step 7) | passes values through |
| 7 | Generation | the generators (drawing engine, documents, procurement) | the assembly only | SLD, MLD, lists (cable list, terminal blocks, BOQ), datasheets, specifications (pliegos) | no, they read the assembly |

Rules of the flow:

- The assembly is the single hand-over: the SLD, the MLD, the lists and the specifications are generated from it, none of them re-reads the calculation (today four selectors do; DGM-13).
- A step reads only the outputs of the steps above it. Nothing is computed twice.
- Design rules give **constraints**, never symbols (example: no 4P MCB downstream of a 2P RCCB). A constraint without its data is not applied.
- The auditor is the only one that decides pass or fail. The assembly runs only once the verdict exists; a "not ok" verdict is carried into the output, never hidden.
- Symbols come from IEC 60617 for now; `epc_symbols` replaces the provider later without touching the other steps.
- The type of a device is fixed by step 1; its rating by step 4. The audit re-checks the constraints with the values in place (for example MCB vs MCCB by current).
- Ids are stable (circuit tag plus role). A change in one circuit does not renumber the others.

## 4. Photovoltaic extension

Same six steps, other roles and constraints. The plant is analysed per generator (array), string, combiner, inverter and point of connection.

| # | Step | PV content |
| --- | --- | --- |
| 1 | Circuit analysis | chain of roles per string and per inverter, from the plant topology: module string, optimizer (if any), DC combiner box, string fuse, DC isolator, DC surge protection, blocking diode (if any), inverter (MPPT input), rapid shutdown device, AC protection, RCMU or insulation monitoring (IMD), AC isolator, connection to the board |
| 2 | Netlist | the same four-file model per board and per array: devices, loads (strings, inverters), wires (DC string cable, DC main, AC), circuits by stable id |
| 3 | Cable type estimate | DC solar cable type (single core, double insulated, UV and weather resistant), AC cable type, installation (tray, conduit, buried); no cross-section |
| 4 | Calculation | the PV engine and the calculation engines: strings, DC and AC power, voltages at the temperature extremes, currents, cross-sections, voltage drops, short-circuit contribution, DC ratings of each device |
| 5 | Audit | PV constraints (candidates below), checked with the values |
| 6 | Assembly | SLD and MLD of the plant, stringing, cabling, from the assembly; the six placeholder symbols (DGM-03) until the real ones exist |

Candidate PV constraints (all `unverified`, each one needs a person's confirmation before it enters `design_constraints.json`; sources and values come from the norm register, never from this document):

- the string voltage at the cold extreme must not exceed the inverter and the module system limits;
- a device in a DC circuit must be rated for DC;
- the string protection (fuse or equivalent) is required when the parallel strings can exceed the module reverse-current withstand;
- the rapid shutdown device and the residual current or insulation monitor are present where the plant type requires them;
- every string and every inverter has its isolating device on the DC and on the AC side.

## 5. Non-goals

- No norm value is added, changed or approved here. New values are `pending review` in the norm register.
- No change to golden files, D15 or D26.
- The functional and control scheme drawing (DGM-10) and the other disciplines (DGM-11) follow the same flow later.

## 6. Impact and rollout

Moving the decision of device roles ahead of the calculation touches stage 3 and the calculation input, which other threads and the golden comparisons depend on. Rollout:

1. Spike: measure what changes if the calculation receives the device list instead of writing it (no behaviour change on `main`).
2. Step 1 and 3 modules (analysis, cable types) beside the current flow, with their tests.
3. Auditor over the current calculation output, replacing the advisory `violations`.
4. Switch the calculation input; compare against the reference snapshot.
5. PV roles, topologies and constraints on the same modules (DGM-14).

## 7. Acceptance

- The device lists, the netlist and the cable types exist before any number is calculated, and contain no value.
- The calculation emits no device text that the netlist depends on.
- The assembly refuses to run without an audit verdict; the verdict and its findings appear in the output (English and Spanish).
- Every new rule, topology and constraint is `unverified` or `pending review`; the status word "verified" never appears.
- Gate and CI green, golden files untouched, no test or check weakened.
