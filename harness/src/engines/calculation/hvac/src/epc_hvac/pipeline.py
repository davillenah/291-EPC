"""run(): the cooling load of every space of a document, its supply air flow and the ventilation it needs."""
import json
from typing import Any, Dict, List, Optional, Union

from epc_hvac import config, loads
from epc_hvac.model import HvacError, Options, Result

DESIGN_KEYS = ("t_out_c", "t_in_c", "w_out_kg_kg", "w_in_kg_kg", "supply_delta_t_k")


def _document(doc: Union[dict, str, bytes]) -> dict:
    if isinstance(doc, (str, bytes)):
        try:
            doc = json.loads(doc)
        except ValueError as e:
            raise HvacError(f"the input is not valid JSON: {e}") from e
    if not isinstance(doc, dict) or not isinstance(doc.get("spaces"), list) or not doc["spaces"]:
        raise HvacError("the input needs a non-empty list `spaces`")
    return doc


def _design(doc: dict) -> Dict[str, float]:
    d = doc.get("design") or {}
    missing = [k for k in DESIGN_KEYS if k not in d]
    if missing:
        raise HvacError(f"design is missing: {', '.join(missing)}")
    return {k: float(d[k]) for k in DESIGN_KEYS}


def _envelope(space: dict, dt: float) -> Dict[str, float]:
    """Conduction through the walls and roofs and conduction plus solar through the windows."""
    cond = solar = 0.0
    for e in space.get("envelope") or []:
        cond += loads.conduction_w(e["u_w_m2k"], e["area_m2"], e.get("delta_t_k", dt))
        if e.get("kind") == "window":
            solar += loads.solar_w(e["area_m2"], e.get("shgc", 0.4), e.get("orientation", "N"))
    return {"conduction": cond, "solar": solar}


def _space(space: dict, d: Dict[str, float]) -> Dict[str, Any]:
    p = config.params()
    area, height = float(space["area_m2"]), float(space.get("height_m", 3.0))
    n, use = float(space.get("occupants", 0)), str(space.get("use", "default"))
    env = _envelope(space, d["t_out_c"] - d["t_in_c"])
    ppl = loads.people_w(n)
    light = loads.internal_w(area, space.get("lighting_w_m2", 0), p["default_lighting_use_factor"])
    equip = loads.internal_w(area, space.get("equipment_w_m2", 0))
    inf = loads.air_w(loads.infiltration_ls(area * height, space.get("infiltration_ach", p["default_infiltration_ach"])), d["t_out_c"] - d["t_in_c"], d["w_out_kg_kg"] - d["w_in_kg_kg"])
    vent_ls = loads.ventilation_ls(use, n, area)
    vent = loads.air_w(vent_ls, d["t_out_c"] - d["t_in_c"], d["w_out_kg_kg"] - d["w_in_kg_kg"])
    sensible = env["conduction"] + env["solar"] + ppl["sensible"] + light + equip + inf["sensible"] + vent["sensible"]
    latent = ppl["latent"] + inf["latent"] + vent["latent"]
    supply = loads.supply_flow_ls(sensible, d["supply_delta_t_k"])
    return {"id": space["id"], "name": space.get("name", space["id"]), "area_m2": area, "sensible_w": round(sensible, 1), "latent_w": round(latent, 1), "total_w": round(sensible + latent, 1),
            "total_tr": round(loads.refrigeration_tons(sensible + latent), 2), "supply_ls": round(supply, 1), "ventilation_ls": round(vent_ls, 1),
            "parts_w": {"conduction": round(env["conduction"], 1), "solar": round(env["solar"], 1), "people": round(ppl["sensible"] + ppl["latent"], 1), "lighting": round(light, 1),
                        "equipment": round(equip, 1), "infiltration": round(inf["sensible"] + inf["latent"], 1), "ventilation": round(vent["sensible"] + vent["latent"], 1)}}


def run(doc: Union[dict, str, bytes], options: Optional[Options] = None) -> Result:
    """The load of each space and the totals of the document (the options are reserved: the typical values are in `params.json`)."""
    document = _document(doc)
    d = _design(document)
    spaces: List[Dict[str, Any]] = []
    for s in document["spaces"]:
        if "id" not in s or "area_m2" not in s:
            raise HvacError("every space needs `id` and `area_m2`")
        spaces.append(_space(s, d))
    totals = {k: round(sum(s[k] for s in spaces), 1) for k in ("sensible_w", "latent_w", "total_w", "supply_ls", "ventilation_ls")}
    totals["total_tr"] = round(loads.refrigeration_tons(totals["total_w"]), 2)
    warnings = ["Typical values not yet confirmed by the owner: do not use the result to size equipment."]
    return Result(spaces=spaces, totals=totals, warnings=warnings)
