"""The equipment data the engine reads: inverters, module technologies and formats, mounting structures, accessories and the feasibility references.

One source of truth per datum (ADR-0012). The research records under `data/` are the only source:

  data/pv_inverters/inverters/*.json            inverter data sheets -> the engine inverter blocks (`inverters()`), derived here, never copied into a second file
  data/pv_inverters/accessories/*.json          inverter-side equipment (combiners, SPDs, meters, loggers, optimisers, central stations)
  data/pv_modules/technologies/*.json, formats/*.json   module technologies and physical formats (size, weight); the electrical data of the products stays in `module_catalog.json`
  data/mounting_structures/{ground,roof}/*.json  mounting structures: the foundation of a structure (`foundation()`) and the candidates for a site (`structures()`)
  data/feasibility/*.json                       reference tables and methods of the feasibility study

Nothing is invented. A record carries a status (`unverified`, `typical`, `not_found`); a value the record does not give as one plain number is a gap, and a gap makes an inverter or a depth
unusable (the reason is listed by `inverter_gaps()`), it is never filled in. Every value stays pending review until a person approves it.
"""
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA = Path(__file__).resolve().parent / "data"
REFERENCE_FILES = ("capex_opex_reference", "feasibility_methods", "land_use_fixed_by_province_ar", "lcoe_1xh_ns_by_province_ar", "shading_loss_tables_ar", "uncertainty_reference", "worked_examples_validation")
_RANGE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)")


@lru_cache(maxsize=None)
def _read(relative: str) -> Any:
    return json.loads((DATA / relative).read_text(encoding="utf-8"))


def _records(folder: str) -> List[Dict[str, Any]]:
    """Every record of a data folder (schema files excluded), in file-name order."""
    return [_read(f"{folder}/{p.name}") for p in sorted((DATA / folder).glob("*.json")) if not p.name.endswith(".schema.json")]


def _number(value: Any) -> Optional[float]:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _window(value: Any) -> Optional[Tuple[float, float]]:
    """(low, high) of a text that starts with a range such as `200-800` or `200-800 (usable MPP 80-800)`; None for anything else (`not_found`, two ranges for different things)."""
    if not isinstance(value, str):
        return None
    m = _RANGE.match(value)
    return (float(m.group(1)), float(m.group(2))) if m and ";" not in value else None


def _power_w(el: Dict[str, Any]) -> Optional[float]:
    if _number(el.get("rated_ac_power_w")) is not None:
        return _number(el["rated_ac_power_w"])
    kw = _number(el.get("rated_ac_power_kw"))
    return kw * 1000.0 if kw is not None else None          # a power in kVA or VA is apparent power: the active power is not stated, so it is not used


def _window_of(windows: Any, model: str) -> Any:
    """The MPPT window of a model: the one entry of a dict whose key is the model (or part of its name), else the single window the record gives."""
    if not isinstance(windows, dict):
        return windows
    key = next((k for k in windows if k == model or k in model), None)
    return windows.get(key) if key else None


def _models(rec: Dict[str, Any]) -> List[Tuple[str, Optional[float], Any]]:
    """(model, rated power W, MPPT window) of every model a record covers: one per entry of `rated_ac_power_by_model_*`, else the record itself."""
    el = rec["electrical_ratings"]
    by_model = el.get("rated_ac_power_by_model_w") or ({k: v * 1000.0 for k, v in el["rated_ac_power_by_model_kw"].items()} if el.get("rated_ac_power_by_model_kw") else None)
    windows = el.get("mppt_voltage_range_v")
    if not by_model:
        return [(rec["name"]["en"], _power_w(el), windows)]
    return [(model, _number(power), _window_of(windows, model)) for model, power in by_model.items()]


def _derive(rec: Dict[str, Any], model: str, power: Optional[float], window: Any) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """(engine inverter block, gaps) of one model: the block is None unless every key the string layout needs is one plain number."""
    el = rec["electrical_ratings"]
    low_high = _window(window)
    block = {"pac0_w": power, "mppt_v_min": low_high[0] if low_high else None, "mppt_v_max": low_high[1] if low_high else None, "vdc_max_v": _number(el.get("max_dc_voltage_v")),
             "n_mppt": _number(el.get("n_mppt")), "i_max_input_a": _number(el.get("max_dc_current_per_mppt_a"))}
    isc = _number(el.get("max_sc_current_per_mppt_a")) if _number(el.get("max_sc_current_per_mppt_a")) is not None else _number(el.get("max_sc_current_per_input_a"))
    gaps = [k for k, v in block.items() if v is None]
    if gaps:
        return None, gaps
    block["n_mppt"] = int(block["n_mppt"])
    block["isc_max_input_a"] = isc
    return block, []


@lru_cache(maxsize=None)
def _derived() -> Tuple[Tuple[Dict[str, Any], ...], Tuple[Dict[str, Any], ...]]:
    usable, gaps = [], []
    for rec in _records("pv_inverters/inverters"):
        maker, many = rec["name"]["en"].split()[0], bool((rec["electrical_ratings"].get("rated_ac_power_by_model_w") or rec["electrical_ratings"].get("rated_ac_power_by_model_kw")))
        source = (rec.get("sources") or [{}])[0]
        for model, power, window in _models(rec):
            ident = f"{rec['id'].split('.')[0]}.{model.lower().replace(' ', '')}" if many else rec["id"]
            block, missing = _derive(rec, model, power, window)
            if block is None:
                gaps.append({"id": ident, "model": model, "missing": missing})
                continue
            usable.append({"id": ident, "manufacturer": maker, "model": model, "inverter": block, "record": rec["id"], "data_status": rec.get("status", "unverified"), "verified_by": None,
                           "source": f"{source.get('title', '')} ({source.get('publisher', '')})".strip(" ()")})
    return tuple(usable), tuple(gaps)


def inverters() -> List[Dict[str, Any]]:
    """The inverters the engine can lay strings on: one record per model whose data sheet gives every needed value as a plain number (each record: id, manufacturer, model, `inverter` block, record, data_status)."""
    return [dict(r, inverter=dict(r["inverter"])) for r in _derived()[0]]


def inverter_gaps() -> List[Dict[str, Any]]:
    """The models that cannot be used and why: `missing` lists the engine keys the data sheet does not give as one plain number (`n_mppt`, `i_max_input_a`, `pac0_w`, ...)."""
    return [dict(g) for g in _derived()[1]]


def inverter_records() -> List[Dict[str, Any]]:
    """The full inverter research records (parts, geometry, ratings, mechanical data, sources)."""
    return list(_records("pv_inverters/inverters"))


def accessories() -> List[Dict[str, Any]]:
    """The inverter-side equipment records (combiners, switches, SPDs, meters, data loggers, optimisers, central inverters)."""
    return list(_records("pv_inverters/accessories"))


def accessory(ident: str) -> Dict[str, Any]:
    found = next((a for a in accessories() if a["id"] == ident), None)
    if found is None:
        raise KeyError(ident)
    return found


def module_technologies() -> List[Dict[str, Any]]:
    return list(_records("pv_modules/technologies"))


def module_formats() -> List[Dict[str, Any]]:
    return list(_records("pv_modules/formats"))


def module_format(dimensions_mm: List[float], tolerance_mm: float = 1.0) -> Optional[Dict[str, Any]]:
    """The module format record whose outline (long and short side) matches `dimensions_mm`, or None. Several formats can share an outline: the first in file order is returned."""
    want = sorted(float(d) for d in dimensions_mm[:2])
    for rec in module_formats():
        size = (rec.get("geometry") or {}).get("module_dimensions_mm")
        if size and all(abs(a - b) <= tolerance_mm for a, b in zip(sorted(float(d) for d in size[:2]), want)):
            return rec
    return None


def module_weight_kg(dimensions_mm: List[float]) -> Optional[float]:
    """The weight of the module format that has this outline, when its record gives one number; None otherwise."""
    rec = module_format(dimensions_mm)
    return _number(((rec or {}).get("mechanical_ratings") or {}).get("weight_kg"))


def structures(mounting: Optional[str] = None) -> List[Dict[str, Any]]:
    """The mounting structure records, all or only those of one `mounting` (`ground` or `roof`)."""
    found = _records("mounting_structures/ground") + _records("mounting_structures/roof")
    return [s for s in found if mounting is None or s["family"] == mounting]


def structure(ident: str) -> Dict[str, Any]:
    found = next((s for s in structures() if s["id"] == ident), None)
    if found is None:
        raise KeyError(ident)
    return found


_KINDS = (("micropile", "embedded"), ("pile", "embedded"), ("screw", "embedded"), ("concrete_footing", "concrete"), ("ballast", "ballast"))


def _foundation_kind(rec: Dict[str, Any]) -> str:
    if rec["family"] == "roof":
        return "ballast" if "ballast" in rec["category"] else "roof_fixed"
    return next((k for word, k in _KINDS if word in rec["category"]), "other")


def _embedment_element(rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The element of the record that states an embedment depth greater than zero, or None."""
    return next((e for e in rec["geometry"].get("elements", []) if "embedment" in e.get("id", "") and (_number(e.get("length_mm")) or 0) > 0), None)


def foundation(ident: str) -> Dict[str, Any]:
    """What a structure stands on, from its record: `kind` (`embedded` piles or screws, `concrete`, `ballast`, `roof_fixed`, `other`), `embedment_m` (the depth the record states, else None: never assumed),
    the `status` of that depth and the structure `family`. A depth of 0 or a missing one means nothing is drawn below the surface."""
    rec = structure(ident)
    element = _embedment_element(rec)
    return {"structure_id": rec["id"], "family": rec["family"], "kind": _foundation_kind(rec), "embedment_m": round(element["length_mm"] / 1000.0, 3) if element else None,
            "status": element["status"] if element else "not_found", "record_status": rec["status"]}


def reference(name: str) -> Dict[str, Any]:
    """A feasibility reference or method file by name (see `REFERENCE_FILES`); every one is `pending review`."""
    if name not in REFERENCE_FILES:
        raise KeyError(name)
    return _read(f"feasibility/{name}.json")
