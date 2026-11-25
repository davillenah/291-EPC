"""The ladder tray line of the catalogue as functions over the `tray_catalogue` block of the typical values (`core.PARAMS["tray_catalogue"]`): widths, rail heights, sheet gauges and finishes.

Pure functions in metres or millimetres as named; the data is the single source of the sizes (sizing, library and detail read it here).
"""
from typing import Any, Dict, List, Tuple


def gauge_mm(cat: Dict[str, Any], gauge: str) -> float:
    """The sheet thickness of a gauge number (22, 20, 18, 14)."""
    return float(cat["gauge_mm"][str(gauge)])


def rail_gauge(cat: Dict[str, Any], ala_mm: float, finish: str = "", gauge: str = "") -> str:
    """The gauge of the rail: the asked one when the height has it, else the default; the 150 rail exists only in the heavy gauge."""
    allowed = cat["rail_heights_mm"][str(int(ala_mm))]["gauges"]
    want = gauge or cat["default"]["gauge"]
    return want if want in allowed else allowed[-1] if want > allowed[-1] else allowed[0]


def rail_thickness_mm(cat: Dict[str, Any], ala_mm: float, finish: str = "", gauge: str = "") -> float:
    return gauge_mm(cat, rail_gauge(cat, ala_mm, finish, gauge))


def cover_thickness_mm(cat: Dict[str, Any], width_mm: float, finish: str = "") -> float:
    """The sheet of the cover of a width: by the finish (Z or G) and the nearest width at or above."""
    table = cat["cover_gauge"][finish or cat["default"]["finish"]]
    widths = sorted(int(w) for w in table)
    chosen = next((w for w in widths if w >= width_mm), widths[-1])
    return gauge_mm(cat, table[str(chosen)])


def sizes(cat: Dict[str, Any]) -> List[Tuple[float, float, float]]:
    """Every commercial (width, rail height, useful height) in mm, smallest free section first."""
    rows = [(float(w), float(a), float(h["useful_mm"])) for w in cat["widths_mm"] for a, h in cat["rail_heights_mm"].items()]
    return sorted(rows, key=lambda r: (r[0] * r[2], r[0]))


def fill_candidates(cat: Dict[str, Any]) -> List[Dict[str, float]]:
    """The sizes as the sizing reads them: the width, the useful height (the fill is over it) and the rail height."""
    return [{"ancho_mm": w, "alto_mm": u, "ala_mm": a} for w, a, u in sizes(cat)]


def ladder(q: Dict[str, Any], cat: Dict[str, Any]) -> Dict[str, Any]:
    """The ladder sizes of the drawing (`detail.ladder`, metres) with the ones the catalogue fixes filled in: the sheet of the rail and of the covers, the length of a section and the bends."""
    finish, widest = cat["default"]["finish"], max(cat["widths_mm"])
    wide = [int(w) for w, g in cat["cover_gauge"][finish].items() if g != cat["cover_gauge"][finish][str(min(cat["widths_mm"]))]]
    return {**q, "rail_m": rail_thickness_mm(cat, 90, finish) / 1000, "cover_m": cover_thickness_mm(cat, min(cat["widths_mm"]), finish) / 1000,
            "cover_wide_m": cover_thickness_mm(cat, widest, finish) / 1000, "cover_wide_from_m": (min(wide) if wide else widest) / 1000,
            "elbow_radius_m": cat["inner_bend_radius_mm"] / 1000, "vertical_links": cat["articulated_bend"]["links"], "joint_m": cat["length_mm"] / 1000}
