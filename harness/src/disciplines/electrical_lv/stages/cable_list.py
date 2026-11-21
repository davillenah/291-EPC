"""The cable list: one row per sized circuit, selected from the engine result of stages 6 and 8 and joined with the runs of stage 3. Nothing is calculated here.

The sizing works on the loads of the load list. On a routed floor every branch circuit (IUG-xx, TUG-xx) is a load of its own, sized by the voltage drop by electrical moments, so each is one row; when stage 3
routed the floors (`routing` slice) the row also names the room and the trays and conduits that carry that circuit (the engine's own schedule of containers).
"""
import copy

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
    for tag, data in ch["calc"]["datos"].items():
        detail = ch["calc"]["detalle"][tag]
        load = by_id.get(tag)
        row = {"circuit": tag, "from": detail.get("padre") or ch["form"]["board"]["name"], "to": detail.get("descripcion") or "", "phases": detail["fases"], "material": detail.get("material"),
               "insulation": detail.get("aislacion"), "s_mm2": data["S"], "neutral_mm2": detail.get("neutro_mm2"), "pe_mm2": detail.get("pe_mm2"), "method": detail.get("metodo"),
               "length_m": detail.get("largo_m"), "ib_a": detail.get("ib_a"), "in_a": data.get("In"), "du_pct": data.get("dU"), "compliant": detail.get("cumple")}
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
    from epc_drawing import diagram_assembler, diagram_model
    datos, detalle = ch["calc"]["datos"], ch["calc"]["detalle"]
    circuits = {tag: {"disp": d.get("disp"), "kind": KIND_OF_TYPE.get(detalle[tag].get("tipo")), "parent": detalle[tag].get("padre") or None, "load_ref": tag} for tag, d in datos.items()}
    board = ch["form"]["board"]["name"]
    model = dict(diagram_model.build_board_model(board, circuits), board=board)
    values = {tag: {"in_a": d.get("In"), "icu_ka": d.get("icu"), "s_mm2": d.get("S"), "du_pct": d.get("dU"), "ib_a": detalle[tag].get("ib_a")} for tag, d in datos.items()}
    return diagram_assembler.assemble(model, values, cable_rows(ch, loads, routing))
