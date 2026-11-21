# Diagram knowledge (SLD, MLD, functional schemes, IEC 60617)

Research data for drawing single-line (SLD), multi-line (MLD) and functional diagrams, LV and MV, with the PV families on top. Facts come from public manufacturer and technical pages; no standard text, PDF or image is stored. Every datum carries `status`: `unverified` (sourced, not checked by a person), `typical` (generic industry value, no source) or `not_found` (never guessed). Nothing is `verified`, and norm values stay `pending review` (only a person approves).

| Folder | Content |
|---|---|
| `sld_mld/` | LV/MV devices (43), typical single-line schemes (9), `decision_rules.json` (when to use MCB, MCCB, RCCB, fuses, relays...), conventions |
| `pv_sld_mld/` | PV architectures (8), PV devices (14), PV decision rules, DC/AC protection, grounding |
| `funcional_iec60617/` | IEC 60617 symbols (38, own geometry descriptions), typical power/control circuits (14: direct, star-delta, reversing...) |
| `pv_funcional/` | PV functional circuits (16): stringing, monitoring, export limit, storage, trackers |
| `puente_motor_dibujo/` | Bridge to the drawing engine: `device_symbol_map.json` (research device -> `epc_symbols` library symbol and ports), `netlist.schema.json` (contract proposal) and 18 netlists |

Rules: one source of truth (ADR-0012): symbols and ports live in `src/engines/cad/symbols` and are only referenced here; engine numbers never come from these files (they are criteria, not calculations). Read by `epc_drawing.diagram_knowledge` (rules, symbol lookup, advisory board check); checked by `tests/unit/test_diagram_knowledge.py`. Pending work: BACKLOG `DGM-*`.
