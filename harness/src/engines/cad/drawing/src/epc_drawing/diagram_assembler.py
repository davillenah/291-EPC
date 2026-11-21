"""Assembler of a board diagram: joins four independent sources into one assembled description that the SLD and MLD engines draw (ADR-0037).

- the model (netlist, `diagram_model`): what connects to what, by stable ids, no values;
- the calculation values of each circuit (rating, size, drop, ...) and the cable-list rows (spec, length): looked up by circuit tag, passed through, never computed here;
- the design rules (`diagram_knowledge`): constraints on the connections (what may not be installed where, e.g. no 4P MCB behind a 2P RCCB); they give no symbols;
- the symbols: IEC 60617 for now (each device carries its IEC 60617 reference) and the library symbol the drawing uses, through a `symbols` provider that can be swapped later.

Nothing is calculated and nothing is drawn here. The result lists, per circuit, its devices (symbol, IEC 60617 reference, labels), its load and its wires (zone, cable row), in the order of the model, and the design-rule `violations` found in the netlist (advisory).
"""

from epc_drawing import diagram_knowledge as K

PROTECTIVE = {"mcb", "mccb", "acb", "rccb", "rcbo", "mpcb"}                       # devices that show the rating of the calculation
LABELS = {"in_a": "rated_current", "icu_ka": "breaking_capacity"}      # value of the calculation -> label slot of the symbol library


def _labels(device, values):
    """Label slots of one device: its tag, and the rating of the protective device from the calculation (`In`, `Icu`) when the circuit has values."""
    labels = {"tag": device["tag"]}
    if device["device_id"] in PROTECTIVE:
        labels.update({slot: values[key] for key, slot in LABELS.items() if values.get(key) is not None})
    return labels


def _assemble_circuit(c, index, v, rows, symbols):
    """One circuit of the assembly: its devices (the end of each incoming wire: the start hangs from the board or the parent), its load and its wires."""
    devices, ws = index["devices"], [index["wires"][i] for i in c["wires"]]
    ids = [w["to"]["ref"] for w in ws if w["to"]["ref"] in devices]
    return {"id": c["id"], "tag": c["name"]["en"], "values": dict(v),
            "devices": [{"id": i, "symbol": symbols(devices[i]["device_id"])["sld_symbol"], "iec_60617": K.iec_60617_for(devices[i]["device_id"]), "device_id": devices[i]["device_id"], "labels": _labels(devices[i], v)} for i in ids],
            "load": index["loads"].get(c["load"]),
            "wires": [{"id": w["id"], "from": w["from"], "to": w["to"], "zone": w["zone"], "cable": rows.get(w.get("cable_ref"))} for w in ws]}


def assemble(model: dict, values: dict, cable_rows: list = None, symbols=None) -> dict:
    """{'board', 'circuits': [...], 'violations': [...], 'unmapped': [...]} from the model, the per-circuit `values` ({tag: {...}}) and the cable-list rows ([{'circuit': tag, ...}]).

    A wire's `cable_ref` is resolved to its row of the cable list (None when the row is missing: the engine then draws the wire without a cable text). `symbols(device_id) -> {'sld_symbol': ...}` is the symbol provider (default: the library map of `diagram_knowledge`)."""
    rows, symbols = {r["circuit"]: r for r in (cable_rows or [])}, symbols or K.symbol_for
    index = {key: {x["id"]: x for x in model[key]} for key in ("devices", "wires", "loads")}
    out = [_assemble_circuit(c, index, values.get(c["name"]["en"], {}), rows, symbols) for c in model["circuits"]]
    return {"board": model["board"], "circuits": out, "violations": K.check_constraints(model), "unmapped": list(model["unmapped"])}
