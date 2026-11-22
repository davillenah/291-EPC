"""One view of the circuits of the calculation: every field the lists and documents read, selected once from the engine result of stages 6 and 8 (`ch["calc"]`). Nothing is calculated here.

The cable list, the terminal list, the bill of quantities and the report used to select these fields each on its own (DGM-13); they now derive from this view, so a field is read from the
calculation in one place only. The assembly of the board (`cable_list.board_diagram_assembly`) is the hand-over of the diagram flow; this view is the one reader of the calculation behind it."""


def circuit_view(ch):
    """{tag: view} of every sized circuit, in the order of the engine result."""
    out = {}
    for tag, data in ch["calc"]["datos"].items():
        detail = ch["calc"]["detalle"][tag]
        head = (detail.get("cadena") or [{}])[0]
        out[tag] = {"tag": tag, "parent": detail.get("padre") or None, "description": detail.get("descripcion") or "", "phases": detail["fases"],
                    "material": detail.get("material"), "insulation": detail.get("aislacion"), "method": detail.get("metodo"),
                    "s_mm2": data["S"], "neutral_mm2": detail.get("neutro_mm2"), "pe_mm2": detail.get("pe_mm2"), "length_m": detail.get("largo_m"),
                    "ib_a": detail.get("ib_a"), "in_a": data.get("In"), "du_pct": data.get("dU"), "icu_ka": data.get("icu"), "compliant": detail.get("cumple"),
                    "device": data.get("disp") or "", "device_kind": head.get("short"), "poles": head.get("poles")}
    return out
