"""The irradiation disk as a DXF drawing: a polar chart whose radius is the tilt and whose angle is the orientation (azimuth from north, clockwise), filled by bands of 5 % of the best annual irradiation.

The numbers come from `epc_pv.disk.compute` (handed in by the caller); this module only draws them. Everything is a block: one per percentage band (the filled sectors), the grid with its labels, the legend and the
marker of the best plane; the drawing is the insertion of those blocks. Two palettes: `color` (blue to red, for screens and reports) and `grey` (monochrome, for printed sheets). Units: millimetres.

  render(disk, name, language, palette, stamp_date) -> {<name>_irradiation_disk.dxf: bytes}      nothing is written
"""
import math
from typing import Any, Dict, List, Tuple

from epc_draw.core.errors import DxfError
from epc_draw.pv.diagrams import Pen, _layers, _new_doc
from epc_draw.pv.files import framed as _framed

RADIUS_MM = 100.0
BAND_PCT = 5
PALETTES = ("color", "grey")
ROLES = ("pv.DISK_FILL", "pv.DISK_GRID", "pv.DISK_TEXT")
COLOR_STOPS = ((0.0, (0, 0, 140)), (0.2, (0, 90, 255)), (0.4, (0, 220, 230)), (0.55, (130, 255, 110)), (0.7, (255, 235, 0)), (0.85, (255, 90, 0)), (1.0, (150, 0, 0)))
TEXT = {
    "title": {"en": "IRRADIATION DISK", "es": "DISCO DE IRRADIACIÓN"},
    "subtitle": {"en": "annual irradiation on a fixed plane, % of the best plane", "es": "irradiación anual sobre un plano fijo, % del mejor plano"},
    "tilt": {"en": "Tilt (β)", "es": "Inclinación (β)"},
    "orientation": {"en": "Orientation (γ)", "es": "Orientación (γ)"},
    "north": {"en": "North", "es": "Norte"}, "south": {"en": "South", "es": "Sur"}, "east": {"en": "East", "es": "Este"}, "west": {"en": "West", "es": "Oeste"},
    "best": {"en": "Best plane", "es": "Mejor plano"},
    "draft": {"en": "DRAFT: values from typical data, not verified", "es": "BORRADOR: valores de datos típicos, sin verificar"},
}


def _t(key: str, language: str) -> str:
    return TEXT[key]["es" if language == "es" else "en"]


def point(tilt_deg: float, azimuth_deg: float) -> Tuple[float, float]:
    """The position on the disk (centre at the origin, north up, east right) of a tilt and an azimuth."""
    r = RADIUS_MM * tilt_deg / 90.0
    a = math.radians(azimuth_deg)
    return round(r * math.sin(a), 4), round(r * math.cos(a), 4)


def band_of(pct: float) -> int:
    """The lower edge of the 5 % band of a percentage (0 to 95)."""
    return min(int(pct // BAND_PCT) * BAND_PCT, 100 - BAND_PCT)


def rgb(band: int, palette: str, low: int) -> Tuple[int, int, int]:
    """The colour of a band; `low` is the lowest band that appears, so the scale uses the whole range."""
    t = 0.0 if band <= low else (band - low) / float(100 - BAND_PCT - low)
    if palette == "grey":
        g = int(round(245 - t * 225))
        return g, g, g
    for (t0, c0), (t1, c1) in zip(COLOR_STOPS, COLOR_STOPS[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return tuple(int(round(a + (b - a) * f)) for a, b in zip(c0, c1))
    return COLOR_STOPS[-1][1]


def _runs(tilts: List[float], values: List[float], lo: float, hi: float) -> List[Tuple[float, float]]:
    """The tilt intervals of one ray where the percentage (linear between nodes) lies in [lo, hi), touching pieces joined."""
    runs: List[Tuple[float, float]] = []
    for t0, t1, v0, v1 in zip(tilts, tilts[1:], values, values[1:]):
        if v0 == v1:
            span = (0.0, 1.0) if lo <= v0 < hi else None
        else:
            ua, ub = sorted(((lo - v0) / (v1 - v0), (hi - v0) / (v1 - v0)))
            span = (max(ua, 0.0), min(ub, 1.0)) if max(ua, 0.0) < min(ub, 1.0) else None
        if span is None:
            continue
        piece = (t0 + (t1 - t0) * span[0], t0 + (t1 - t0) * span[1])
        if runs and abs(runs[-1][1] - piece[0]) < 1e-9:
            piece = (runs.pop()[0], piece[1])
        runs.append(piece)
    return runs


def _ray_polygon(ta: float, tb: float, a0: float, a1: float) -> List[Tuple[float, float]]:
    if ta <= 0.0:
        return [point(0, 0), point(tb, a0), point(tb, a1)]
    return [point(ta, a0), point(tb, a0), point(tb, a1), point(ta, a1)]


def _sectors(disk: Dict[str, Any]) -> Dict[int, List[List[Tuple[float, float]]]]:
    """The filled areas grouped by band: {band: [polygon, ...]}. Every azimuth ray of the disk grid gives, per band, the tilt intervals inside the band (exact along the ray, linear between nodes) and each
    interval becomes a thin sector as wide as the ray step, so the edges of a band follow its contour; the caller refines the grid (1 degree of tilt, 2 of azimuth) for a smooth drawing."""
    tilts, azs, pct = disk["tilt_deg"], disk["azimuth_deg"], disk["pct"]
    half = (azs[1] - azs[0]) / 2.0 if len(azs) > 1 else 180.0
    low = band_of(min(min(r) for r in pct))
    bands: Dict[int, List[List[Tuple[float, float]]]] = {}
    for j, az in enumerate(azs):
        column = [row[j] for row in pct]
        for band in range(low, 100, BAND_PCT):
            hi = 101.0 if band >= 100 - BAND_PCT else band + BAND_PCT
            for ta, tb in _runs(tilts, column, band, hi):
                bands.setdefault(band, []).append(_ray_polygon(ta, tb, az - half, az + half))
    return bands


def _band_blocks(doc, disk: Dict[str, Any], palette: str) -> List[Tuple[str, int]]:
    """One block per band with its filled sectors; returns [(block name, band)] from the lowest band up."""
    import ezdxf
    bands = _sectors(disk)
    low = min(bands)
    out = []
    for band in sorted(bands):
        name = f"PVD-BAND-{band:03d}"
        block = doc.blocks.new(name)
        colour = ezdxf.colors.rgb2int(rgb(band, palette, low))
        for poly in bands[band]:
            hatch = block.add_hatch(dxfattribs={"layer": "pv.DISK_FILL", "true_color": colour})
            hatch.paths.add_polyline_path(poly, is_closed=True)
        out.append((name, band))
    return out


def _text(block, s: str, pos: Tuple[float, float], height: float, centre: bool = True) -> None:
    import ezdxf
    t = block.add_text(s, height=height, dxfattribs={"layer": "pv.DISK_TEXT"})
    t.set_placement(pos, align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER if centre else ezdxf.enums.TextEntityAlignment.LEFT)


def _grid_block(doc, language: str) -> str:
    """Outline, rings every 10 degrees of tilt, spokes every 15 degrees of azimuth, azimuth labels and the four cardinal names."""
    block = doc.blocks.new("PVD-GRID")
    for tilt in range(10, 91, 10):
        block.add_circle((0, 0), RADIUS_MM * tilt / 90.0, dxfattribs={"layer": "pv.DISK_GRID"})
    for az in range(0, 360, 15):
        block.add_line((0, 0), point(90, az), dxfattribs={"layer": "pv.DISK_GRID"})
        _text(block, f"{az}°", point(90 + 9.0, az), 3.0)
    for tilt in range(10, 91, 20):
        _text(block, f"{tilt}°", (0.0, -RADIUS_MM * tilt / 90.0 + 2.0), 2.4)
    for key, (x, y) in (("north", (0, RADIUS_MM + 22)), ("south", (0, -RADIUS_MM - 22)), ("east", (RADIUS_MM + 26, 0)), ("west", (-RADIUS_MM - 26, 0))):
        _text(block, _t(key, language), (x, y), 5.0)
    return "PVD-GRID"


def _legend_block(doc, bands: List[Tuple[str, int]], palette: str, language: str) -> str:
    import ezdxf
    block = doc.blocks.new("PVD-LEGEND")
    low, step = bands[0][1], 7.0
    for k, (_, band) in enumerate(bands):
        y = k * step
        hatch = block.add_hatch(dxfattribs={"layer": "pv.DISK_FILL", "true_color": ezdxf.colors.rgb2int(rgb(band, palette, low))})
        hatch.paths.add_polyline_path([(0, y), (10, y), (10, y + step), (0, y + step)], is_closed=True)
        block.add_lwpolyline([(0, y), (10, y), (10, y + step), (0, y + step)], close=True, dxfattribs={"layer": "pv.DISK_GRID"})
        _text(block, f"{band}-{band + BAND_PCT} %" if band < 100 - BAND_PCT else f"{band}-100 %", (13, y + step / 2), 3.0, centre=False)
    _text(block, "%", (5, len(bands) * step + 5), 3.5)
    return "PVD-LEGEND"


def _best_block(doc) -> str:
    block = doc.blocks.new("PVD-BEST")
    block.add_circle((0, 0), 2.0, dxfattribs={"layer": "pv.DISK_TEXT"})
    block.add_line((-4, 0), (4, 0), dxfattribs={"layer": "pv.DISK_TEXT"})
    block.add_line((0, -4), (0, 4), dxfattribs={"layer": "pv.DISK_TEXT"})
    return "PVD-BEST"


def build(disk: Dict[str, Any], language: str = "en", palette: str = "color"):
    """The ezdxf document: the band blocks, the grid, the legend and the best-plane marker inserted at the origin of the sheet."""
    if palette not in PALETTES:
        raise DxfError("err_disk_palette", choices=list(PALETTES), value=palette)
    doc, style = _new_doc(4)
    _layers(doc, ROLES)
    bands = _band_blocks(doc, disk, palette)
    msp = doc.modelspace()
    for name, _ in bands:
        msp.add_blockref(name, (0, 0), dxfattribs={"layer": "pv.DISK_FILL"})
    msp.add_blockref(_grid_block(doc, language), (0, 0), dxfattribs={"layer": "pv.DISK_GRID"})
    best = disk["best"]
    msp.add_blockref(_best_block(doc), point(best["tilt_deg"], best["azimuth_deg"]), dxfattribs={"layer": "pv.DISK_TEXT"})
    msp.add_blockref(_legend_block(doc, bands, palette, language), (RADIUS_MM + 45, -RADIUS_MM / 2), dxfattribs={"layer": "pv.DISK_TEXT"})
    pen = Pen(doc, style, 4.0)
    pen.text("pv.DISK_TEXT", _t("title", language), -RADIUS_MM - 40, -RADIUS_MM - 45, 1.6)
    pen.text("pv.DISK_TEXT", _t("subtitle", language), -RADIUS_MM - 40, -RADIUS_MM - 52, 0.9)
    pen.text("pv.DISK_TEXT", f"{_t('best', language)}: β {best['tilt_deg']:g}°, γ {best['azimuth_deg']:g}° ({best['kwh_m2']:g} kWh/m²)", -RADIUS_MM - 40, -RADIUS_MM - 59, 0.9)
    pen.text("pv.DISK_TEXT", _t("draft", language), -RADIUS_MM - 40, -RADIUS_MM - 66, 0.7)
    pen.text("pv.DISK_TEXT", _t("tilt", language), -RADIUS_MM - 42, RADIUS_MM + 5, 0.9)
    pen.text("pv.DISK_TEXT", _t("orientation", language), RADIUS_MM + 5, -RADIUS_MM - 10, 0.9)
    return doc


def render(disk: Dict[str, Any], name: str, language: str = "en", palette: str = "color", stamp_date=None) -> Dict[str, bytes]:
    """`{<name>_irradiation_disk.dxf: bytes}`. Nothing is written."""
    from epc_draw.core import deliverable
    doc = build(disk, language, palette)
    return {f"{name}_irradiation_disk.dxf": deliverable.finish_draft_bytes(_framed(doc), None, stamp_date, f"{name}_irradiation_disk")["dxf"]}
