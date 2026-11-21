"""The drawings of a photovoltaic plant: layout plan, stringing plan, cabling plan and single-line diagram, as DXF drafts on the `pv.*` layer roles.

The module draws what the layout engine placed (`epc_pv.plan_layout`) and what the yield run counted (`epc_pv.run`); it calculates nothing. Every figure on a drawing is read from those two
results. The plans are in metres (the sheet composer picks the scale), the single-line diagram in millimetres. Layer names, look and typeface come from the catalogs of `epc_dxf`
(`harness/config/dxf`); a drawing asks for a layer by role. Each draft becomes a deliverable through `epc_dxf.deliverable.finish_draft`.

  write_all(geometry, result, out_dir, name, language) -> {plan name: path}      layout, stringing, cabling (plans) and sld (diagram)
"""
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

TEXT = {
    "layout": {"en": "PV PLANT LAYOUT", "es": "IMPLANTACIÓN DE PLANTA FOTOVOLTAICA"},
    "stringing": {"en": "STRINGING PLAN", "es": "PLANO DE CONEXIONADO DE STRINGS"},
    "cabling": {"en": "DC AND AC CABLING PLAN (REFERENCE)", "es": "PLANO DE CABLEADO CC Y CA (REFERENCIAL)"},
    "sld": {"en": "PV PLANT SINGLE-LINE DIAGRAM", "es": "DIAGRAMA UNIFILAR DE PLANTA FOTOVOLTAICA"},
    "north": {"en": "N", "es": "N"},
    "station": {"en": "LV/MV STATION", "es": "ESTACIÓN BT/MT"},
    "pitch": {"en": "row pitch", "es": "paso entre filas"},
    "draft": {"en": "DRAFT: reference drawing, values not verified", "es": "BORRADOR: dibujo de referencia, valores sin verificar"},
    "road": {"en": "ROAD", "es": "CAMINO"},
}
PALETTE = (1, 3, 5, 6, 30, 40, 150, 200)                     # ACI colours cycled over the inverters in the stringing plan


def _t(key: str, language: str) -> str:
    return TEXT[key]["es" if language == "es" else "en"]


def _new_doc(insunits: int):
    import ezdxf
    from epc_dxf import textstyle
    doc = ezdxf.new("R2018", setup=True)
    doc.units = insunits
    doc.styles.get("Standard").dxf.font = "arial.ttf"
    textstyle.add_styles(doc)
    return doc, textstyle.load()["font"]["style"]


def _layers(doc, roles: Tuple[str, ...]) -> None:
    for role in roles:
        if role not in doc.layers:
            doc.layers.add(role)


class Pen:
    """Draws on role layers with one text style and one text height."""

    def __init__(self, doc, style: str, height: float):
        self.msp, self.style, self.h = doc.modelspace(), style, height

    def rect(self, role: str, x: float, y: float, w: float, d: float, color: int = None) -> None:
        attribs = {"layer": role, **({"color": color} if color is not None else {})}
        self.msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + d), (x, y + d)], close=True, dxfattribs=attribs)

    def line(self, role: str, a: Tuple[float, float], b: Tuple[float, float], color: int = None) -> None:
        self.msp.add_line(a, b, dxfattribs={"layer": role, **({"color": color} if color is not None else {})})

    def poly(self, role: str, pts: List[Tuple[float, float]], color: int = None) -> None:
        self.msp.add_lwpolyline(pts, dxfattribs={"layer": role, **({"color": color} if color is not None else {})})

    def text(self, role: str, s: str, x: float, y: float, scale: float = 1.0, centre: bool = False) -> None:
        import ezdxf
        t = self.msp.add_text(s, height=self.h * scale, dxfattribs={"layer": role, "style": self.style})
        t.set_placement((x, y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER if centre else ezdxf.enums.TextEntityAlignment.LEFT)


def _text_height(geometry: Dict[str, Any]) -> float:
    return max(geometry["site"]["width_m"], geometry["site"]["length_m"]) / 110.0


def _frame_plan(pen: Pen, geometry: Dict[str, Any], language: str) -> None:
    """Site boundary, setback line, road, station and north arrow, common to every plan."""
    s = geometry["site"]
    pen.rect("pv.SITE", 0, 0, s["width_m"], s["length_m"])
    f = geometry["frame"]
    pen.msp.add_lwpolyline([(f["x0"], f["y0"]), (f["x1"], f["y0"]), (f["x1"], f["y1"]), (f["x0"], f["y1"])], close=True, dxfattribs={"layer": "pv.SITE", "linetype": "DASHED"})
    st = geometry["station"]
    road = geometry["road_width_m"]
    pen.rect("pv.ROAD", f["x0"], f["x0"], f["x1"] - f["x0"], road)
    pen.text("pv.TEXT", _t("road", language), (f["x0"] + f["x1"]) / 2, f["x0"] + road / 2, 0.8, True)
    pen.rect("pv.STATION", st["x"], st["y"], st["width_m"], st["depth_m"])
    pen.text("pv.TEXT", _t("station", language), st["x"] + st["width_m"] / 2, st["y"] - pen.h, 0.8, True)
    nx, ny = s["width_m"] + pen.h * 4, s["length_m"] - pen.h * 4
    pen.line("pv.SITE", (nx, ny - pen.h * 2), (nx, ny + pen.h * 2))
    pen.text("pv.TEXT", _t("north", language), nx, ny + pen.h * 3, 1.5, True)


def _tables(pen: Pen, geometry: Dict[str, Any], colour_by_inverter: bool, labels: str) -> None:
    order = {inv["id"]: n for n, inv in enumerate(geometry["inverters"])}
    for t in geometry["tables"]:
        colour = PALETTE[order.get(t["inverters"][0], 0) % len(PALETTE)] if colour_by_inverter and t["inverters"] else None
        pen.rect("pv.TABLE", t["x"], t["y"], t["width_m"], t["depth_m"], colour)
        text = t["id"] if labels == "id" else ", ".join(t["strings"])
        pen.text("pv.TEXT", text, t["x"] + t["width_m"] / 2, t["y"] + t["depth_m"] / 2, 0.7 if labels == "id" else 0.5, True)
        if labels == "id":
            pen.text("pv.TEXT", f"{t['modules']}", t["x"] + t["width_m"] / 2, t["y"] + t["depth_m"] / 2 - pen.h * 0.9, 0.5, True)


def _inverters(pen: Pen, geometry: Dict[str, Any]) -> None:
    for inv in geometry["inverters"]:
        if inv["x"] is None:
            continue
        pen.rect("pv.INVERTER", inv["x"] - inv["width_m"] / 2, inv["y"] - inv["depth_m"] / 2, inv["width_m"], inv["depth_m"])
        pen.text("pv.TEXT", inv["id"], inv["x"], inv["y"] + inv["depth_m"], 0.45, True)


def _notes(pen: Pen, geometry: Dict[str, Any], title: str, language: str) -> None:
    s = geometry["site"]
    pen.text("pv.TEXT", title, 0, s["length_m"] + pen.h * 3, 1.6)
    pitch = ", ".join(f"{p} m" for p in geometry["pitch_m"])
    c = geometry["counts"]
    pen.text("pv.TEXT", f"{_t('pitch', language)}: {pitch}; tables: {c['tables']}; inverters: {c['inverters']}", 0, s["length_m"] + pen.h * 1.2, 0.8)
    pen.text("pv.TEXT", _t("draft", language), 0, -pen.h * 2.5, 0.8)


def _plan(geometry: Dict[str, Any], key: str, language: str, colour: bool, labels: str, cabling: bool = False):
    doc, style = _new_doc(6)
    _layers(doc, ("pv.SITE", "pv.ROAD", "pv.TABLE", "pv.INVERTER", "pv.STATION", "pv.DC", "pv.AC", "pv.TEXT"))
    pen = Pen(doc, style, _text_height(geometry))
    _frame_plan(pen, geometry, language)
    _tables(pen, geometry, colour, labels)
    _inverters(pen, geometry)
    if cabling:
        _routes(pen, geometry)
    _notes(pen, geometry, _t(key, language), language)
    return doc


def _routes(pen: Pen, geometry: Dict[str, Any]) -> None:
    """Reference routes: each table to its inverter along its row gap (DC), each inverter to the station along the row gap and the road (AC). Lines only, no length."""
    st, road_y = geometry["station"], geometry["frame"]["x0"] + geometry["road_width_m"] / 2
    by_id = {i["id"]: i for i in geometry["inverters"]}
    for t in geometry["tables"]:
        inv = by_id.get(t["inverters"][0]) if t["inverters"] else None
        if inv and inv["x"] is not None:
            pen.poly("pv.DC", [(t["x"] + t["width_m"] / 2, t["y"] + t["depth_m"]), (t["x"] + t["width_m"] / 2, inv["y"]), (inv["x"], inv["y"])])
    for inv in by_id.values():
        if inv["x"] is not None:
            pen.poly("pv.AC", [(inv["x"], inv["y"]), (geometry["frame"]["x0"] - 1.0, inv["y"]), (geometry["frame"]["x0"] - 1.0, road_y), (st["x"] + st["width_m"], road_y)])


# ---- single-line diagram (millimetres)

PER_ROW, CELL_W, CELL_H, ROW_STEP = 8, 52.0, 26.0, 62.0


def _sld(geometry: Dict[str, Any], result: Dict[str, Any], language: str):
    doc, style = _new_doc(4)
    _layers(doc, ("pv.DIAGRAM", "pv.TEXT", "pv.STATION"))
    pen = Pen(doc, style, 3.0)
    pen.text("pv.TEXT", _t("sld", language), 0, 20, 1.8)
    pen.text("pv.TEXT", _t("draft", language), 0, 10, 0.9)
    y = 0.0
    for a in result["arrays"]:
        y = _array_block(pen, a, [i for i in geometry["inverters"] if i["array"] == a["id"]], y, language)
    return doc


SYMBOL_SCALE = 0.55      # the library symbols are drawn about 30 units wide; the cell is 44 wide


def _symbol(pen: Pen, name: str, x: float, y: float, scale: float = SYMBOL_SCALE) -> bool:
    """Inserts the IEC 60617 symbol `name` of the SLD library (`epc_symbols`, SVG source converted to DXF blocks) at (x, y); False when the library has no such symbol (the caller keeps its plain box)."""
    from pathlib import Path as P
    import ezdxf
    from ezdxf.addons.importer import Importer
    from epc_symbols import library_dir
    path = P(str(library_dir("sld-lv-symbol"))) / f"291_E_LV_SLD_IEC60617_{name}.dxf"
    if not path.is_file():
        return False
    block = f"291_E_LV_SLD_IEC60617_{name}"
    doc = pen.msp.doc
    if block not in doc.blocks:
        source = ezdxf.readfile(str(path))
        importer = Importer(source, doc)
        importer.import_block(block)
        importer.finalize()
    pen.msp.add_blockref(block, (x, y), dxfattribs={"layer": "pv.DIAGRAM", "xscale": scale, "yscale": scale, "zscale": scale})
    return True


def _inverter_cell(pen: Pen, inv: Dict[str, Any], x: float, y: float) -> float:
    """One inverter box with its strings above and its AC output below; returns the x of its centre."""
    mid = x + (CELL_W - 8) / 2
    pen.rect("pv.DIAGRAM", x, y - CELL_H, CELL_W - 8, CELL_H)
    _symbol(pen, "inverter", x + CELL_W - 8 - 4, y - 3)      # the inverter symbol in the corner of the box
    pen.text("pv.TEXT", inv["id"], mid, y - 9, 0.9, True)
    pen.text("pv.TEXT", f"{len(inv['strings'])} strings", mid, y - 18, 0.8, True)
    pen.line("pv.DIAGRAM", (mid, y), (mid, y + 8))
    pen.text("pv.TEXT", "DC", mid + 4, y + 5, 0.7)
    pen.line("pv.DIAGRAM", (mid, y - CELL_H), (mid, y - CELL_H - 10))
    return mid


def _array_block(pen: Pen, a: Dict[str, Any], inverters: List[Dict[str, Any]], y_start: float, language: str) -> float:
    """One array: inverters in rows of up to 8 (each over its AC busbar), the busbars joined by a collector that goes to the station. Returns the y where the next array starts."""
    st = a["strings"]
    note = {"en": "strings", "es": "strings"}[language if language in ("en", "es") else "en"]
    pen.text("pv.TEXT", f"{a['id']}: {a['modules']} modules, {a['dc_kwp']} kWp DC, {st['strings']} {note} x {st['n_series']} modules, {a['inverters']} inverters, {a['ac_kw']} kW AC", 0, y_start - 10, 1.0)
    rows = -(-len(inverters) // PER_ROW)
    width = PER_ROW * CELL_W - 8
    bus_y = []
    for r in range(rows):
        top = y_start - 40 - r * ROW_STEP
        row = inverters[r * PER_ROW:(r + 1) * PER_ROW]
        mids = [_inverter_cell(pen, inv, c * CELL_W, top) for c, inv in enumerate(row)]
        by = top - CELL_H - 10
        pen.line("pv.DIAGRAM", (mids[0], by), (width + 10, by))
        pen.text("pv.TEXT", f"AC {r + 1}", mids[0], by - 5, 0.8)
        bus_y.append(by)
    collector_x = width + 10
    pen.line("pv.DIAGRAM", (collector_x, bus_y[0]), (collector_x, bus_y[-1]))
    mid_y = (bus_y[0] + bus_y[-1]) / 2
    pen.line("pv.DIAGRAM", (collector_x, mid_y), (collector_x + 24, mid_y))
    pen.rect("pv.STATION", collector_x + 24, mid_y - 20, 70, 40)
    pen.text("pv.TEXT", _t("station", language), collector_x + 59, mid_y, 0.9, True)
    return bus_y[-1] - 40


def write_all(geometry: Dict[str, Any], result: Dict[str, Any], out_dir, name: str, language: str = "en", stamp_date=None) -> Dict[str, Path]:
    """Writes `<name>_layout.dxf`, `_stringing.dxf`, `_cabling.dxf` and `_sld.dxf` under `out_dir`; returns {plan name: path}."""
    from epc_dxf import deliverable
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    docs = {"layout": _plan(geometry, "layout", language, False, "id"), "stringing": _plan(geometry, "stringing", language, True, "strings"),
            "cabling": _plan(geometry, "cabling", language, False, "id", cabling=True), "sld": _sld(geometry, result, language)}
    written = {}
    for key, doc in docs.items():
        path = out / f"{name}_{key}.dxf"
        deliverable.finish_draft(doc, path, None, stamp_date, f"{name}_{key}")
        written[f"{name}_{key}"] = path
    return written
