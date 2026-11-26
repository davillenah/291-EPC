"""The drawings of a rooftop photovoltaic plant: roof layout, roof stringing and roof cabling plan, as DXF drafts on the `pv.*` layer roles.

The module draws what `epc_pv.plan_roof` placed on the roof planes and what the yield run counted per array (`epc_pv.run`); it calculates nothing. Every figure on a drawing is read from those two results.
Each plane is drawn in its own coordinates (metres, true slope length: x along the eave, y up the slope), side by side, so no foreshortening hides a module; its tilt and azimuth are written beside it. The
strings of a plane are the consecutive modules of its array in placement order (row by row from the eave), as the layout engine counts them; one plane is one array, so no string mixes orientations.
The raceway on the cabling plan is a reference (a line along the eave margin with a short drop from each string); the inverter position is not an input and is not drawn.

  write_all(roof, result, out_dir, name, language, stamp_date) -> {plan name: path}      roof_layout, roof_stringing, roof_cabling
"""
from pathlib import Path
from typing import Any, Dict, List, Tuple

from epc_draw.pv.diagrams import PALETTE, Pen, _layers, _new_doc, _t

TEXT = {
    "roof_layout": {"en": "PV ROOF LAYOUT", "es": "IMPLANTACIÓN FOTOVOLTAICA EN CUBIERTA"},
    "roof_stringing": {"en": "ROOF STRINGING PLAN", "es": "PLANO DE CONEXIONADO DE STRINGS EN CUBIERTA"},
    "roof_cabling": {"en": "ROOF DC CABLING PLAN (REFERENCE)", "es": "PLANO DE CABLEADO CC EN CUBIERTA (REFERENCIAL)"},
    "eave": {"en": "EAVE", "es": "ALERO"},
    "plane": {"en": "plane", "es": "faldón"},
    "modules": {"en": "modules", "es": "módulos"},
    "tilt": {"en": "tilt", "es": "inclinación"},
    "azimuth": {"en": "azimuth (from north)", "es": "azimut (desde el norte)"},
    "scale_note": {"en": "Planes drawn in their own coordinates, true slope length, x along the eave.", "es": "Faldones dibujados en sus coordenadas, largo real, x a lo largo del alero."},
    "string_note": {"en": "Strings are consecutive modules from the eave, row by row.", "es": "Los strings son módulos consecutivos desde el alero, fila por fila."},
    "route_note": {"en": "Raceway route is a reference; the inverter position is not given.", "es": "El recorrido de la canalización es referencial; no se dio la posición del inversor."},
    "rounded": {"en": "whole strings counted by the engine", "es": "strings enteros contados por el motor"},
    "to_inverter": {"en": "to inverter", "es": "al inversor"},
    "wind": {"en": "Wind uplift and ballast: not calculated.", "es": "Succión del viento y lastre: no calculados."},
}
GAP_FACTOR = 4.0


def _tx(key: str, language: str) -> str:
    return TEXT[key]["es" if language == "es" else "en"]


def _scale(roof: Dict[str, Any]) -> float:
    total = sum(p["width_m"] for p in roof["planes"])
    deepest = max(p["slope_m"] for p in roof["planes"])
    return max(total, deepest) / 110.0


def _offsets(roof: Dict[str, Any], h: float) -> List[float]:
    x, out = 0.0, []
    for p in roof["planes"]:
        out.append(x)
        x += p["width_m"] + GAP_FACTOR * h
    return out


def _outline(pen: Pen, p: Dict[str, Any], ox: float, language: str) -> None:
    pen.rect("pv.ROOF", ox, 0, p["width_m"], p["slope_m"])
    s = p["setback_m"]
    if s > 0 and p["width_m"] > 2 * s and p["slope_m"] > 2 * s:
        pen.msp.add_lwpolyline([(ox + s, s), (ox + p["width_m"] - s, s), (ox + p["width_m"] - s, p["slope_m"] - s), (ox + s, p["slope_m"] - s)], close=True, dxfattribs={"layer": "pv.ROOF", "linetype": "DASHED"})
    for o in p.get("obstacles", []):
        pen.rect("pv.ROOF_OBSTACLE", ox + o["x"], o["y"], o["width_m"], o["depth_m"])
    pen.text("pv.ROOF_DATA", _tx("eave", language), ox + p["width_m"] / 2, -pen.h * 1.2, 0.7, True)


def _modules(pen: Pen, p: Dict[str, Any], ox: float, colour_of=None) -> None:
    w, d = p["module"]["width_m"], p["module"]["depth_m"]
    for i, c in enumerate(p["cells"]):
        pen.rect("pv.MODULE", ox + c["x"], c["y"], w, d, colour_of(i) if colour_of else None)


def _label(pen: Pen, p: Dict[str, Any], ox: float, language: str, counted: int) -> None:
    top = p["slope_m"] + pen.h * 1.5
    pen.text("pv.TEXT", f"{_tx('plane', language)} {p['id']}: {p['modules']} {_tx('modules', language)}", ox, top + pen.h * 3.2, 0.9)
    pen.text("pv.TEXT", f"{_tx('tilt', language)} {p['tilt_deg']:g} deg, {_tx('azimuth', language)} {p['azimuth_deg']:g} deg", ox, top + pen.h * 1.6, 0.7)
    if counted != p["modules"]:
        pen.text("pv.TEXT", f"{counted} {_tx('modules', language)} ({_tx('rounded', language)})", ox, top, 0.6)


def _notes(pen: Pen, roof: Dict[str, Any], title: str, language: str, extra: Tuple[str, ...]) -> None:
    deepest = max(p["slope_m"] for p in roof["planes"])
    pen.text("pv.TEXT", title, 0, deepest + pen.h * 9, 1.6)
    notes = (_tx("scale_note", language),) + extra + (_tx("wind", language), _t("draft", language))
    for n, line in enumerate(notes):
        pen.text("pv.TEXT", line, 0, -pen.h * (3.5 + 1.4 * n), 0.7)


def _counted(result: Dict[str, Any], plane_id: str) -> int:
    return next((a["modules"] for a in result["arrays"] if a["id"] == plane_id), 0)


def _string_of(result: Dict[str, Any], plane_id: str):
    """(n_series, strings) of the plane's array."""
    a = next(a for a in result["arrays"] if a["id"] == plane_id)
    return a["strings"]["n_series"], a["strings"]["strings"]


def _doc(roof: Dict[str, Any]):
    doc, style = _new_doc(6)
    _layers(doc, ("pv.ROOF", "pv.ROOF_OBSTACLE", "pv.ROOF_DATA", "pv.MODULE", "pv.CONDUIT", "pv.DC", "pv.TEXT"))
    return doc, Pen(doc, style, _scale(roof))


def _layout(roof: Dict[str, Any], result: Dict[str, Any], language: str):
    doc, pen = _doc(roof)
    for p, ox in zip(roof["planes"], _offsets(roof, pen.h)):
        _outline(pen, p, ox, language)
        _modules(pen, p, ox)
        _label(pen, p, ox, language, _counted(result, p["id"]))
    _notes(pen, roof, _tx("roof_layout", language), language, ())
    return doc


def _stringing(roof: Dict[str, Any], result: Dict[str, Any], language: str):
    doc, pen = _doc(roof)
    for k, (p, ox) in enumerate(zip(roof["planes"], _offsets(roof, pen.h))):
        n_series, n_strings = _string_of(result, p["id"]) if _counted(result, p["id"]) else (1, 0)
        string = lambda i: min(i // n_series, max(n_strings - 1, 0))      # noqa: E731
        _outline(pen, p, ox, language)
        _modules(pen, p, ox, lambda i: PALETTE[(string(i) + k) % len(PALETTE)])
        _string_labels(pen, p, ox, n_series, n_strings)
        _label(pen, p, ox, language, _counted(result, p["id"]))
    _notes(pen, roof, _tx("roof_stringing", language), language, (_tx("string_note", language),))
    return doc


def _string_labels(pen: Pen, p: Dict[str, Any], ox: float, n_series: int, n_strings: int) -> None:
    """The id of each string at its first module."""
    for s in range(n_strings):
        i = s * n_series
        if i < len(p["cells"]):
            c = p["cells"][i]
            pen.text("pv.TEXT", f"{p['id']}-S{s + 1}", ox + c["x"] + p["module"]["width_m"] / 2, c["y"] + p["module"]["depth_m"] / 2, 0.45, True)


def _cabling(roof: Dict[str, Any], result: Dict[str, Any], language: str):
    doc, pen = _doc(roof)
    for p, ox in zip(roof["planes"], _offsets(roof, pen.h)):
        n_series, n_strings = _string_of(result, p["id"]) if _counted(result, p["id"]) else (1, 0)
        _outline(pen, p, ox, language)
        _modules(pen, p, ox)
        _route(pen, p, ox, n_series, n_strings, language)
        _label(pen, p, ox, language, _counted(result, p["id"]))
    _notes(pen, roof, _tx("roof_cabling", language), language, (_tx("route_note", language),))
    return doc


def _route(pen: Pen, p: Dict[str, Any], ox: float, n_series: int, n_strings: int, language: str) -> None:
    """A raceway along the eave margin and one drop from the first module of every string (lines only, no length)."""
    if not p["cells"]:
        return
    y = p["setback_m"] / 2
    pen.line("pv.CONDUIT", (ox + p["setback_m"], y), (ox + p["width_m"] - p["setback_m"], y))
    pen.text("pv.TEXT", _tx("to_inverter", language), ox + p["setback_m"], y + pen.h * 0.9, 0.5)
    for s in range(n_strings):
        i = s * n_series
        if i < len(p["cells"]):
            c = p["cells"][i]
            x = ox + c["x"] + p["module"]["width_m"] / 2
            pen.line("pv.DC", (x, c["y"]), (x, y))


def _inverters_of(a: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The inverters of an array without positions (a roof plan does not place them): ids `<array>-INV<k>`, the array's strings shared among them in order."""
    n, total = max(int(a["inverters"]), 1), int(a["strings"]["strings"])
    share = [total // n + (1 if k < total % n else 0) for k in range(n)]
    out, first = [], 0
    for k, count in enumerate(share, start=1):
        out.append({"id": f"{a['id']}-INV{k}", "array": a["id"], "strings": [f"{a['id']}-S{i + 1}" for i in range(first, first + count)]})
        first += count
    return out


def _sld(roof: Dict[str, Any], result: Dict[str, Any], language: str):
    """The plant single-line diagram of a roof plant: the arrays of the run with their inverters (no positions) and strings, to the station."""
    from epc_draw.pv import diagrams as D
    doc, style = D._new_doc(4)
    D._layers(doc, ("pv.DIAGRAM", "pv.TEXT", "pv.STATION"))
    pen = Pen(doc, style, 3.0)
    pen.text("pv.TEXT", D._t("sld", language), 0, 20, 1.8)
    pen.text("pv.TEXT", D._t("draft", language), 0, 10, 0.9)
    y = 0.0
    for a in result["arrays"]:
        y = D._array_block(pen, a, _inverters_of(a), y, language)
    return doc


def render_all(roof: Dict[str, Any], result: Dict[str, Any], name: str, language: str = "en", stamp_date=None) -> Dict[str, bytes]:
    """{`<name>_roof_layout.dxf`, `_roof_stringing.dxf`, `_roof_cabling.dxf`, `_roof_sld.dxf`: bytes}. Nothing is written."""
    from epc_draw.core import deliverable
    docs = {"roof_layout": _layout(roof, result, language), "roof_stringing": _stringing(roof, result, language), "roof_cabling": _cabling(roof, result, language), "roof_sld": _sld(roof, result, language)}
    return {f"{name}_{key}.dxf": deliverable.finish_draft_bytes(doc, None, stamp_date, f"{name}_{key}")["dxf"] for key, doc in docs.items()}


def write_all(roof: Dict[str, Any], result: Dict[str, Any], out_dir, name: str, language: str = "en", stamp_date=None) -> Dict[str, Path]:
    """Writes the four drawings of `render_all` under `out_dir`; returns {plan name: path}."""
    from epc_draw.pv import files
    return {Path(k).stem: v for k, v in files.save(out_dir, render_all(roof, result, name, language, stamp_date)).items()}
