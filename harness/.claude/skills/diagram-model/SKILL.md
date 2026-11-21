---
name: "diagram-model"
description: "Builds and checks the relational diagram model of a board (devices, loads, wires, circuits linked by stable ids) from the calculation, for the SLD and MLD. Holds no values."
---

# diagram-model

Owner plugin: `board-design`. Wrapper over `python -m epc_drawing.diagram_model` (code in `harness/src/engines/cad/drawing`, method in ADR-0037, data in `harness/knowledge/diagrams`). Use the project venv.

## Hard rules
1. **The model says what connects to what and nothing else.** No rating, section, length or any number: those come from the calculation engines and the cable list (stage 8). A wire only carries `cable_ref`, the tag of its row in the cable list.
2. **Never invent a device.** The device chain of a circuit comes from the calculation (`disp`); only when it is missing the typical topology of the circuit kind is used (`circuit_topologies.json`). A device text with no mapping is reported, never guessed.
3. **One model per board**, four files linked only by unique ids: `devices.json`, `loads.json`, `wires.json`, `circuits.json`. Ids are built from the circuit tag and the role, never from a counter.
4. **Knowledge status:** every datum in `knowledge/diagrams` is `unverified`, `typical` or `not_found`; report it. Norm values stay `pending review`.
5. **`.svg` is internal only.** Deliverables are `.dxf` and `.pdf`.

## Assembler
The model alone draws nothing. `epc_drawing.diagram_assembler.assemble(model, values, cable_rows, symbols)` joins four sources: the model (connections), the calculation values, the cable-list rows and the symbols (IEC 60617 reference plus the library symbol, through a swappable provider). The design rules are **constraints** (`design_constraints.json`: for example no 4P MCB behind a 2P RCCB), not symbols: it reports them as `violations`, advisory. Stage 10 hands the result over as `diagram_assembly`. It computes nothing: values are looked up by circuit tag and passed through; a constraint without its data (a device with no pole count) is not applied.

## Run
```
python -m epc_drawing.diagram_model --input boards.json --out <work folder>
```
`boards.json` = `{"boards": {"<board tag>": {"circuits": {"<tag>": {"disp": "MCB > KM > OL (25 A)", "kind": "motor", "parent": null, "load_ref": null}}, "cable_refs": {"<tag>": "<cable list tag>"}}}}`. Output: `<out>/<board>/{devices,loads,wires,circuits}.json`.

## Steps
1. Take the circuits of each board from the stored calculation (device text, kind, parent) and the cable list tags.
2. Run the command; read the `WARNING` lines (devices with no mapping) and report each one.
3. Check the files against `harness/knowledge/diagrams/puente_motor_dibujo/model/*.schema.json`; check that every symbol and port exists in the `epc_symbols` library (`tests/unit/test_diagram_knowledge.py` does it for the examples).
4. Report the boards, the circuits without a load, the unmapped devices and the symbols the library lacks (`device_symbol_map.json`, `not_found`), in the user's language.
