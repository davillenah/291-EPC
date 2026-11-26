"""The shading abacus as a DXF drawing: the sun paths of the year cut into the standard cells A1 to D14, the share of the annual irradiation of each cell and the obstacle profile on top.

The numbers come from `epc_pv.abacus.compute` (handed in by the caller); this module only draws them. Everything is a block: one per cell (outline, label and weight), the grid with its scales, the obstacle profile and
the legend; the drawing is the insertion of those blocks. A cell hidden in part by the profile is filled in grey by the share hidden (0.25, 0.5, 0.75 or 1). The scale is 2 mm per degree on both axes. Units: millimetres.

  render(abacus, name, language, stamp_date) -> {<name>_shading_abacus.dxf: bytes}      nothing is written
"""
from typing import Any, Dict, List, Tuple

from epc_draw.pv.diagrams import Pen, _layers, _new_doc
from epc_draw.pv.files import framed as _framed

MM_PER_DEG = 2.0
X_RANGE_DEG, Y_MAX_DEG = 130, 90
ROLES = ("pv.ABACUS_CELL", "pv.ABACUS_COVER", "pv.ABACUS_PROFILE", "pv.ABACUS_TEXT")
GREYS = {0.25: 215, 0.5: 170, 0.75: 120, 1.0: 70}
TEXT = {
    "title": {"en": "SHADING ABACUS", "es": "ÁBACO DE ASOLEAMIENTO"},
    "subtitle": {"en": "sun paths of the year, standard cells A1 to D14, obstacle profile", "es": "trayectorias del sol del año, celdas estándar A1 a D14, perfil de obstáculos"},
    "azimuth": {"en": "Azimuth (deg)", "es": "Ángulo acimutal (grados)"},
    "elevation": {"en": "Sun elevation (deg)", "es": "Ángulo altura solar (grados)"},
    "loss": {"en": "Loss by shading", "es": "Pérdida por sombras"},
    "plane": {"en": "Plane", "es": "Plano"},
    "hidden": {"en": "share of the cell hidden", "es": "parte de la celda tapada"},
    "draft": {"en": "DRAFT: values from typical data, not verified", "es": "BORRADOR: valores de datos típicos, sin verificar"},
}


def _t(key: str, language: str) -> str:
    return TEXT[key]["es"] if language == "es" else TEXT[key]["en"]


def xy(x_deg: float, elevation_deg: float) -> Tuple[float, float]:
    """The position on the sheet of a chart point."""
    return round(x_deg * MM_PER_DEG, 4), round(elevation_deg * MM_PER_DEG, 4)


def _label_point(outline: List[List[float]]) -> Tuple[float, float]:
    xs, ys = [p[0] for p in outline], [p[1] for p in outline]
    return xy(sum(xs) / len(xs), sum(ys) / len(ys))


def _text(block, s: str, pos: Tuple[float, float], height: float, centre: bool = True) -> None:
    import ezdxf
    t = block.add_text(s, height=height, dxfattribs={"layer": "pv.ABACUS_TEXT"})
    t.set_placement(pos, align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER if centre else ezdxf.enums.TextEntityAlignment.LEFT)


def _cell_block(doc, cell: Dict[str, Any]) -> str:
    """One block per cell: the fill of the hidden share, the outline, the label and the weight."""
    import ezdxf
    name = f"PVA-CELL-{cell['id']}"
    block = doc.blocks.new(name)
    pts = [xy(x, el) for x, el in cell["outline"]]
    if cell["cover"] > 0:
        g = GREYS[cell["cover"]]
        hatch = block.add_hatch(dxfattribs={"layer": "pv.ABACUS_COVER", "true_color": ezdxf.colors.rgb2int((g, g, g))})
        hatch.paths.add_polyline_path(pts, is_closed=True)
    block.add_lwpolyline(pts, close=True, dxfattribs={"layer": "pv.ABACUS_CELL"})
    cx, cy = _label_point(cell["outline"])
    _text(block, cell["id"], (cx, cy + 1.6), 3.0)
    _text(block, f"{cell['weight_pct']:.2f} %", (cx, cy - 2.2), 1.8)
    return name


def _grid_block(doc, language: str) -> str:
    """The frame, the azimuth ticks every 10 degrees and the elevation ticks every 10 degrees, with the numbers every 20."""
    block = doc.blocks.new("PVA-GRID")
    x0, x1, y1 = -X_RANGE_DEG * MM_PER_DEG, X_RANGE_DEG * MM_PER_DEG, Y_MAX_DEG * MM_PER_DEG
    block.add_lwpolyline([(x0, 0), (x1, 0), (x1, y1), (x0, y1)], close=True, dxfattribs={"layer": "pv.ABACUS_CELL"})
    for deg in range(-120, 121, 10):
        block.add_line(xy(deg, 0), xy(deg, 2), dxfattribs={"layer": "pv.ABACUS_CELL"})
        if deg % 20 == 0:
            _text(block, f"{deg}", (deg * MM_PER_DEG, -5.0), 3.0)
    for deg in range(0, Y_MAX_DEG + 1, 10):
        block.add_line(xy(-X_RANGE_DEG, deg), xy(-X_RANGE_DEG + 2, deg), dxfattribs={"layer": "pv.ABACUS_CELL"})
        _text(block, f"{deg}", (x0 - 7.0, deg * MM_PER_DEG), 3.0)
    _text(block, _t("azimuth", language), (0.0, -13.0), 3.5)
    _text(block, _t("elevation", language), (x0 - 7.0, y1 + 8.0), 3.5, centre=False)
    return "PVA-GRID"


def _profile_block(doc, profile: List[List[float]]) -> str:
    block = doc.blocks.new("PVA-PROFILE")
    if len(profile) > 1:
        block.add_lwpolyline([xy(x, el) for x, el in profile], dxfattribs={"layer": "pv.ABACUS_PROFILE"})
    for x, el in profile:
        block.add_circle(xy(x, el), 1.0, dxfattribs={"layer": "pv.ABACUS_PROFILE"})
    return "PVA-PROFILE"


def _legend_block(doc, language: str) -> str:
    import ezdxf
    block = doc.blocks.new("PVA-LEGEND")
    _text(block, _t("hidden", language), (0, 12.0), 3.0, centre=False)
    for k, (share, grey) in enumerate(GREYS.items()):
        x = k * 22.0
        hatch = block.add_hatch(dxfattribs={"layer": "pv.ABACUS_COVER", "true_color": ezdxf.colors.rgb2int((grey, grey, grey))})
        hatch.paths.add_polyline_path([(x, 0), (x + 10, 0), (x + 10, 7), (x, 7)], is_closed=True)
        block.add_lwpolyline([(x, 0), (x + 10, 0), (x + 10, 7), (x, 7)], close=True, dxfattribs={"layer": "pv.ABACUS_CELL"})
        _text(block, f"{int(share * 100)} %", (x + 12, 3.5), 3.0, centre=False)
    return "PVA-LEGEND"


def build(abacus: Dict[str, Any], language: str = "en"):
    """The ezdxf document: one block per cell, the grid, the obstacle profile and the legend inserted at the origin."""
    doc, style = _new_doc(4)
    _layers(doc, ROLES)
    msp = doc.modelspace()
    for cell in abacus["cells"]:
        msp.add_blockref(_cell_block(doc, cell), (0, 0), dxfattribs={"layer": "pv.ABACUS_CELL"})
    msp.add_blockref(_grid_block(doc, language), (0, 0), dxfattribs={"layer": "pv.ABACUS_CELL"})
    msp.add_blockref(_profile_block(doc, abacus["profile"]), (0, 0), dxfattribs={"layer": "pv.ABACUS_PROFILE"})
    msp.add_blockref(_legend_block(doc, language), (-X_RANGE_DEG * MM_PER_DEG, -45.0), dxfattribs={"layer": "pv.ABACUS_TEXT"})
    pen = Pen(doc, style, 4.0)
    base = -X_RANGE_DEG * MM_PER_DEG
    pen.text("pv.ABACUS_TEXT", _t("title", language), base, -70.0, 1.6)
    pen.text("pv.ABACUS_TEXT", _t("subtitle", language), base, -77.0, 0.9)
    pen.text("pv.ABACUS_TEXT", f"{_t('plane', language)}: β {abacus['tilt_deg']:g}°, γ {abacus['azimuth_deg']:g}°   {_t('loss', language)}: {abacus['loss_pct']:g} %", base, -84.0, 0.9)
    pen.text("pv.ABACUS_TEXT", _t("draft", language), base, -91.0, 0.7)
    return doc


def render(abacus: Dict[str, Any], name: str, language: str = "en", stamp_date=None) -> Dict[str, bytes]:
    """`{<name>_shading_abacus.dxf: bytes}`. Nothing is written."""
    from epc_draw.core import deliverable
    doc = build(abacus, language)
    return {f"{name}_shading_abacus.dxf": deliverable.finish_draft_bytes(_framed(doc), None, stamp_date, f"{name}_shading_abacus")["dxf"]}
