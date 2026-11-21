"""The AC feeders of the photovoltaic plant: one circuit per inverter in the board form, so the board, the cable list, the terminal list and the memorandum grow with the plant (PVX-06).

Only a plant-only project (every load in area `PV`) takes them: there the board is the plant's collection point and its main feeder carries what the plant generates. In a building project the generation is not added to
the consumption of the board. The power of each feeder is the AC rating of one inverter as stage 3 counted it (`inverter_ac_kw`); phases, run length and power factor are the ones the engineer gives in
`engine_inputs["pv_feeders"]` (the landing form proposes them, `pending review`). Nothing is calculated here: the board engine sizes them.
"""

PV_AREA = "PV"
CACHE_KEY = "pv_plant"          # the plant result of the `pv` slice (it runs first in stage 3, before the board chain is built)
GIVEN = ("phases", "length_m")
PHASE_CODE = {1: "1F", 3: "3F"}


def _plant_only(context):
    loads = (context.loads or {}).get("loads") or []
    return bool(loads) and all(x.get("area") == PV_AREA for x in loads)


def inverter_ids(array):
    """`<array>-INV<k>` for every inverter of the array (the ids the roof single-line uses)."""
    return [f"{array['id']}-INV{k}" for k in range(1, int(array["inverters"]) + 1)]


def feeder_rows(context, given):
    """Board-form rows (one per inverter) of the plant of stage 3; [] when there is no plant, the project has a building or `given` (the `pv_feeders` input) is not there."""
    pv = context.engine_cache.get(CACHE_KEY)
    if not pv or not isinstance(given, dict) or not _plant_only(context) or any(given.get(k) in (None, "") for k in GIVEN):
        return []
    rows = []
    for a in pv.get("arrays") or []:
        for ident in inverter_ids(a):
            row = {"tag": f"E-{ident}", "description": f"PV inverter feeder {ident} / Alimentador del inversor FV {ident}", "load": a["inverter_ac_kw"], "unit": "kW",
                   "phase": PHASE_CODE[int(given["phases"])], "topology": "single", "kind": "auto", "length_m": given["length_m"]}
            if given.get("fp") is not None:
                row["fp"] = given["fp"]
            rows.append(row)
    return rows
