"""The cable list: one row per sized circuit, selected from the engine result of stages 6 and 8 and joined with the runs of stage 3. Nothing is calculated here.

The sizing works on the loads of the load list. On a routed floor every branch circuit (IUG-xx, TUG-xx) is a load of its own, sized by the voltage drop by electrical moments, so each is one row; when stage 3
routed the floors (`routing` slice) the row also names the room and the trays and conduits that carry that circuit (the engine's own schedule of containers).
"""
import copy

from disciplines.electrical_lv.stages.circuit_view import circuit_view

def raceway_of(load_id, routing):
    """{"circuit": tag, "containers": [{tag, kind, cables}]} of a branch-circuit load (the trays and conduits that carry it, from the schedule of the plan engine); None when the load is not a routed circuit."""
    for data in ((routing or {}).get("floors") or {}).values():
        for c in data["proposed"]:
            if c["load"] == load_id:
                held = [{"tag": k["tag"], "kind": k["kind"], "cables": k["cables"]} for k in data["schedule"]["containers"] if c["tag"] in k["circuits"]]
                return {"circuit": c["tag"], "room": c["room"], "outlets": c["outlets"], "containers": held}
    return None


def cable_rows(ch, loads, routing=None):
    """The rows of the cable list, in the order of the engine result."""
    by_id = {x["id"]: x for x in loads}
    rows = []
    for tag, v in circuit_view(ch).items():
        load = by_id.get(tag)
        row = {"circuit": tag, "from": v["parent"] or ch["form"]["board"]["name"], "to": v["description"], "phases": v["phases"], "material": v["material"],
               "insulation": v["insulation"], "s_mm2": v["s_mm2"], "neutral_mm2": v["neutral_mm2"], "pe_mm2": v["pe_mm2"], "method": v["method"],
               "length_m": v["length_m"], "ib_a": v["ib_a"], "in_a": v["in_a"], "du_pct": v["du_pct"], "compliant": v["compliant"]}
        if load is not None and load.get("area"):
            row["area"] = load["area"]
            row["raceway"] = raceway_of(tag, routing)
        rows.append(row)
    return rows


def cable_list_document(ch, loads, routing=None):
    return {"document": "cable_list", "status": "draft", "board": ch["form"]["board"]["name"], "rows": copy.deepcopy(cable_rows(ch, loads, routing)),
            "source": "epc_aea90364.aea_pipeline.calculate"}


KIND_OF_TYPE = {"seccional": "feeder", "motor": "motor", "iluminacion": "lighting", "tomacorrientes": "sockets"}     # circuit type of the calculation -> kind of the typical topologies


def board_diagram_assembly(ch, loads, routing=None):
    """The assembled diagram description of the board (`epc_drawing.diagram_assembler`, ADR-0037): the netlist built from the device chain, parent and type of each circuit of the calculation,
    joined with the values of the calculation and the cable-list rows. Nothing is calculated here; the drawing engines read the result."""
    from epc_drawing import diagram_assembler
    view = circuit_view(ch, strict=False)
    circuits = {tag: {"chain": v["chain"], "disp": v["device"] or None, "kind": KIND_OF_TYPE.get(v["type"]), "parent": v["parent"], "load_ref": tag} for tag, v in view.items()}
    values = {tag: {"in_a": v["in_a"], "icu_ka": v["icu_ka"], "s_mm2": v["s_mm2"], "du_pct": v["du_pct"], "ib_a": v["ib_a"]} for tag, v in view.items()}
    return diagram_assembler.assemble_board(ch["form"]["board"]["name"], circuits, values, cable_rows(ch, loads, routing))
