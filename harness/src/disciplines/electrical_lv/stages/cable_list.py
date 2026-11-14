"""The cable list: one row per sized circuit, selected from the engine result of stages 6 and 8 and joined with the runs of stage 3. Nothing is calculated here.

The sizing works on the loads of the load list, so a row is a sized circuit of the board (a derived `L-<floor>` is one row, not one row per branch circuit). When stage 3 routed the floors
(`routing` slice) a row also names the trays and conduits that carry the branch circuits of that load: the engine's own schedule of containers, joined by the family of the load and the floor.
"""
import copy

FAMILY_OF_LOAD = {"lighting": ("IUG", "IUE"), "receptacles": ("TUG", "TUE")}


def raceway_of(load, floor, routing):
    """{"circuits": [...], "containers": [{tag, kind, cables}]} of the branch circuits of a derived load (kind lighting or receptacles) on a floor; None when the floor was not routed."""
    data = ((routing or {}).get("floors") or {}).get(floor)
    families = FAMILY_OF_LOAD.get(load["kind"])
    if data is None or families is None:
        return None
    mine = sorted(c["tag"] for c in data["proposed"] if c["family"] in families)
    held = [{"tag": c["tag"], "kind": c["kind"], "cables": c["cables"]} for c in data["schedule"]["containers"] if set(c["circuits"]) & set(mine)]
    return {"circuits": mine, "containers": held}


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
            row["raceway"] = raceway_of(load, load["area"], routing)
        rows.append(row)
    return rows


def cable_list_document(ch, loads, routing=None):
    return {"document": "cable_list", "status": "draft", "board": ch["form"]["board"]["name"], "rows": copy.deepcopy(cable_rows(ch, loads, routing)),
            "source": "epc_aea90364.aea_pipeline.calculate"}
