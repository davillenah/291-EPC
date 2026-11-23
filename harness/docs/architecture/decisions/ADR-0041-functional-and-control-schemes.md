# ADR-0041: The harness draws functional and control schemes from the relational model

Status: proposed (written by Claude on the owner's standing authorization of 2026-11-23, DGM-10 and DGM-11 "design first"; nothing here is implemented, and the owner accepts, changes or rejects it). Extends ADR-0037 and applies ADR-0038.

## Context
DGM-10 asks the harness to draw power and control circuits (direct on line, star-delta, reversing, ATS, soft starter, drives, MV protection relays) and DGM-11 asks for the same method for PV strings and combiners, HVAC, lighting and control. The research data is in `knowledge/diagrams/funcional_iec60617/` (14 typical circuits as `circuits/*.json` against `circuit.schema.json`, 33 symbols as `symbols/*.json`, all `unverified`) and `knowledge/diagrams/pv_funcional/` (16 PV circuits). The relational model of ADR-0037 already links devices, loads, wires and circuits by stable ids, and its builder knows typical topologies. What is missing is a drawing path for a scheme read left to right by function, not by board position.

## Decisions proposed
1. **Same model, a second view.** A functional scheme is a view of the relational model (devices, wires, circuits), never a second model. A control circuit adds one thing to the four files: a `rung` and a `sheet` on each wire (the line of the ladder it belongs to) and a `terminal` marking on each port; the model keeps no value.
2. **One drawing function, `epc_drawing.draw_functional(FunctionalInput, out_dir, name)`,** same shape as `epc_sld.draw` (ADR-0040): a frozen dataclass with the model, the circuit id, the language, the date and the title block request; it answers the sheets drawn. It reads no environment variable and no file by itself.
3. **Layout by rule, not by hand.** Power circuit on the left (vertical, phases L1 L2 L3 from the top), control circuit as a ladder on the right (rungs between the two supply rails, each rung left to right: protection, contacts, coil). Cross-references (contact to coil, `13-14` terminals) come from `reference_designations_and_terminals.md`; the reference designation of a device is built from its kind and its circuit tag, the same way ids are built (stable).
4. **Symbols from the one symbol engine.** The IEC 60617 control symbols come from `epc_symbols` as blocks (never redrawn by the drawing code). A symbol without a library geometry stays a placeholder box with the device name (DGM-03), flagged in the drawing notes, until a person supplies or confirms the geometry (the standard is not stored here).
5. **Sheets by the IRAM title block service** (`epc_titleblock`), as the SLD and MLD do; layers and typeface from `config/dxf/layers.json`.
6. **Other disciplines (DGM-11)** add topology kinds to `circuit_topologies.json` and a builder entry each (PV string and combiner, HVAC unit, lighting circuit with its switches), always `unverified` until a person confirms them; none changes a calculation result or a norm value.
7. **Order of work:** (a) the ladder layout and the symbol placement for the three simplest circuits (start-stop with self-holding, direct on line, emergency stop) with characterization tests of the drawing; (b) star-delta and reversing (interlocks, timers); (c) ATS and MV protection; (d) PV and HVAC kinds. One pull request each.

## Decisions for the owner
- Accept the view approach (point 1) or ask for a separate model.
- Confirm the layout convention of point 3 (power left, ladder right) or give another.
- Supply or confirm the IEC 60617 geometry of the control symbols that are placeholders today (the only item that blocks real symbols).

## Consequences
- One drawing path for every functional scheme; the wiring of star-delta contactors and the ATS second source (waiting for this since DGM-02) get a place to live.
- The cost is a typed input, a ladder layout engine and the symbols; nothing changes for the SLD and the MLD.
