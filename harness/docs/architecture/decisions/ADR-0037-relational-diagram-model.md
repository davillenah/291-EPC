# ADR-0037: Relational diagram model per board (devices, loads, wires, circuits linked by stable ids)

Status: accepted (owner, 2026-11-21). Follows ADR-0012 (one source of truth per datum).

## Context
The SLD and MLD engines (`epc_sld`, `epc_mld`) deduce how the devices of a board connect from the board workbook and `SLD_CALC_JSON`. That works for a board of loads but gives no data model for what is connected to what, and nothing for schemes that are not a load board (MV intake, PV, generator with ATS, UPS) or for other disciplines. The diagram research of 2026-11-20 (`harness/knowledge/diagrams`) produced devices, typical schemes and a symbol map, but no model that an engine can read.

## Decisions
1. **A netlist does not draw and holds no value.** It only says what connects to what. The SLD and MLD draw; the calculation engines give every value (ratings, sections, drops); the cable list (stage 8) holds length, origin, destination, internal or external zone and specification of each cable.
2. **One model per board**, as four files linked only by unique ids: `devices.json` (`dev-...`), `loads.json` (`load-...`, loads and sources), `wires.json` (`wire-...`: `from` and `to` as id plus symbol port, `zone` internal or external, `cable_ref` = tag of the row of the cable list) and `circuits.json` (`circ-...`, groups of wire ids; derivable). Nothing is duplicated: an engine looks each id up in its file. Example: `dev-IUG-01-rccb -> wire-IUG-01-1 -> dev-IUG-01-mcb -> wire-IUG-01-load -> load-IUG-01`.
3. **Ids are stable.** They are built from the circuit tag and the role, never from a counter, so the same input gives the same ids and adding a circuit changes none of the others (`--resume` sees real changes only).
4. **Templates plus a builder, not hand-written models.** `circuit_topologies.json` holds the typical device chain per kind of circuit (lighting: RCCB, MCB; motor: MCB, contactor, thermal relay...). `epc_drawing.diagram_model.build_board_model` builds the model: the chain comes from the calculation (`disp`, "MCB > KM > OL") and the template is only the fallback; a circuit with `parent` hangs from the last device of its parent (one RCCB for several MCBs); an unknown device text is reported, never guessed. The device choice follows the decision rules of `knowledge/diagrams`.
5. **Other disciplines use the same method**: their own topology kinds, symbols and builder, the same four-file model and the same id rule. HVAC, lighting, PV plants and control schemes are added as topology kinds or builders, never as a new format.
6. **Optional input of the drawing engines.** The board workbook path stays as it is; the SLD and MLD get a second input that reads the model (BACKLOG DGM-02). Until then the model is checked by `tests/unit/test_diagram_knowledge.py` (schemas, referential integrity, ports in the symbol library).

## Consequences
- The research data (`knowledge/diagrams`) become an input of the drawing, not a side document.
- Reviewing a diagram means reviewing ids and connections, not drawing code.
- Schemes with branches (PV strings in parallel, one RCCB with many MCBs) are expressed without special cases.
