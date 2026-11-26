"""What turns a plan the harness draws into a sheet of a presentation: dimension chains, tags of doors and windows, the room schedule, the opening schedule and the general notes.

It is added only to the plans that the harness itself authors (`epc_draw.arch.author`): the plans a client gives are shown as they are. Every number written here comes from the geometry of the
plan (metres between wall axes, areas of the rooms, widths of the openings), never from a value typed in. Every text carries English and Spanish (`EN / ES`), English first.
The sizes (offsets, steps, ticks, the width of the panel and of its rows) are in `epc_style.json` (`presentation`), the only copy.
"""
import json
import math
import re
from typing import Dict, List, Optional, Sequence, Tuple

from epc_draw.arch.drawing import STYLE_PATH, Poly, TextItem, arc_points, text_width  # noqa: F401  (arc_points kept for callers that draw round marks)
from epc_draw.arch.geometry import axis_of
from epc_draw.arch.model import Architecture, Opening, Room

Pt = Tuple[float, float]
LAYER_DIM, LAYER_NOTE, LAYER_FRAME = "291-A-ANNO-DIMS", "291-A-ANNO", "0-Titleblock"
KIND_NAMES = {"door": ("Door", "Puerta"), "window": ("Window", "Ventana")}


def settings() -> Dict[str, object]:
    """The `presentation` section of the style of the engine."""
    return json.loads(STYLE_PATH.read_text(encoding="utf-8"))["presentation"]


def reserve(side: str) -> float:
    """Paper mm the plan leaves free on a side of its area for the dimension chains (left and bottom) or for the panel of tables (right)."""
    p = settings()
    chain = p["dim_offset_mm"] + 2 * p["dim_step_mm"] + 6.0
    return {"left": 4.0, "bottom": chain + 12.0, "top": 4.0, "right": chain + p["panel_mm"] + p["panel_gap_mm"]}[side]


def _line(a: Pt, b: Pt, layer: str = LAYER_DIM) -> Poly:
    return Poly((a, b), layer)


def _tick(at: Pt, size: float) -> Poly:
    return _line((at[0] - size, at[1] + size), (at[0] + size, at[1] - size))


def _metres(arch: Architecture, units: float) -> str:
    return f"{units / arch.units_per_metre:.2f}"


def _axes(arch: Architecture) -> Tuple[List[float], List[float]]:
    """The x of the walls that run north-south and the y of those that run east-west, in plan units, sorted and without repeats."""
    xs, ys = set(), set()
    for w in arch.walls:
        if abs(w.a[0] - w.b[0]) < 1e-6:
            xs.add(round(w.a[0], 3))
        if abs(w.a[1] - w.b[1]) < 1e-6:
            ys.add(round(w.a[1], 3))
    return sorted(xs), sorted(ys)


def _chain(values: Sequence[float], at: float, horizontal: bool, m, arch: Architecture, step: float, edge: float) -> List[object]:
    """One chain of dimensions along the plan: a line at `at` (paper mm), a tick on each value, the extension lines from the plan edge and the measure of each stretch."""
    p = settings()
    pts = [m((v, 0.0))[0] if horizontal else m((0.0, v))[1] for v in values]
    here = lambda s: (s, at) if horizontal else (at, s)                  # noqa: E731
    out: List[object] = [_line(here(pts[0]), here(pts[-1]))]
    for s in pts:
        out += [_tick(here(s), p["dim_tick_mm"]), _line(here(s), (s, edge) if horizontal else (edge, s))]
    for (s0, s1), (v0, v1) in zip(zip(pts, pts[1:]), zip(values, values[1:])):
        mid = (s0 + s1) / 2
        if horizontal:
            out.append(TextItem(_metres(arch, v1 - v0), (mid, at - 1.2), "TXT_25", LAYER_DIM, "middle"))
        else:
            out.append(TextItem(_metres(arch, v1 - v0), (at - 1.2, mid), "TXT_25", LAYER_DIM, "middle", rotation=-90.0))
    return out


def dimension_items(arch: Architecture, m) -> List[object]:
    """Chains of dimensions between wall axes along the south and the east of the plan, and the overall dimension of each, one step farther out. Never on the north or the west side: a reader
    of the file takes the origin of the plan from its top left corner, and that must stay the corner of the building."""
    if not arch.units_per_metre:
        return []
    p = settings()
    xs, ys = _axes(arch)
    if len(xs) < 2 or len(ys) < 2:
        return []
    south, east = m((0.0, ys[-1]))[1], m((xs[-1], 0.0))[0]
    edge_s, edge_e = south + p["dim_ext_gap_mm"], east + p["dim_ext_gap_mm"]
    out: List[object] = []
    for lvl, vals in ((1, None), (2, "all")):
        off = p["dim_offset_mm"] + (lvl - 1) * p["dim_step_mm"]
        x_vals = xs if vals is None else [xs[0], xs[-1]]
        y_vals = ys if vals is None else [ys[0], ys[-1]]
        out += _chain(x_vals, south + off, True, m, arch, off, edge_s)
        out += _chain(y_vals, east + off, False, m, arch, off, edge_e)
    return out


def tag_name(o: Opening) -> str:
    """The tag of an opening as it is written on the sheet and in the schedule: a letter or two, a hyphen and the number (`D-01`, `V-02`), the form a plan reader knows as the tag of a door or a window."""
    m = re.match(r"^([A-Za-z]+)-?(\d+)$", o.id)
    return f"{m.group(1).upper()}-{int(m.group(2)):02d}" if m else o.id.upper()


def _tag_point(o: Opening, T: float, m) -> Pt:
    """Where the tag of a door or a window goes: beside the wall, on the side the door does not swing to (windows: on the south or west side)."""
    ax = axis_of(o.angle)
    sign = 1.0
    if o.swing:
        sign = -1.0 if (o.swing[0] - o.at[0]) * ax.nx + (o.swing[1] - o.at[1]) * ax.ny > 0 else 1.0
    gap = T / 2 + settings()["tag_offset_mm"] / m.k
    return m((o.at[0] + ax.nx * sign * gap, o.at[1] + ax.ny * sign * gap))


def tag_items(arch: Architecture, m) -> List[object]:
    """The tag of every door and window: its id and its width in metres."""
    T = arch.wall_thickness or 1.0
    out: List[object] = []
    for o in arch.openings:
        if o.kind in KIND_NAMES and arch.units_per_metre:
            at = _tag_point(o, T, m)
            out += [TextItem(tag_name(o), (at[0], at[1] - 0.4), "TXT_18", LAYER_NOTE, "middle", bold=True), TextItem(_metres(arch, o.width), (at[0], at[1] + 2.0), "TXT_18", LAYER_NOTE, "middle")]
    return out


# ---------------------------------------------------------------- the panel of tables
def _cell(value: str, width_mm: float, height: float = 1.8) -> str:
    """The text cut to fit a column (with a dot at the end when it is cut)."""
    room = int(max(width_mm - 2 * settings()["column_pad_mm"], 1.0) / (0.55 * height))
    return value if len(value) <= room else value[:max(room - 1, 1)] + "."


def _table(x: float, y: float, widths: Sequence[float], rows: Sequence[Sequence[str]], heading_rows: int = 1) -> Tuple[List[object], float]:
    """A table of text rows from (x, y) down: its grid and its cells. Returns the items and the y under the last row."""
    p = settings()
    h, pad = p["row_mm"], p["column_pad_mm"]
    total = sum(widths)
    out: List[object] = []
    for r, row in enumerate(rows):
        top = y + r * h
        out.append(_line((x, top), (x + total, top), LAYER_FRAME))
        at = x
        for c, (value, w) in enumerate(zip(row, widths)):
            out.append(TextItem(_cell(value, w), (at + pad, top + h * 0.7), "TXT_25" if r < heading_rows else "TXT_18", LAYER_NOTE, bold=r < heading_rows))
            at += w
    end = y + len(rows) * h
    out.append(_line((x, end), (x + total, end), LAYER_FRAME))
    edges = [x]
    for w in widths:
        edges.append(edges[-1] + w)
    out += [_line((e, y), (e, end), LAYER_FRAME) for e in edges]
    return out, end


def _room_rows(arch: Architecture) -> List[List[str]]:
    rows = [["CODE / CÓDIGO", "ROOM / AMBIENTE", "AREA m²", "SIZE / MEDIDAS m"]]
    total = 0.0
    for r in arch.rooms:
        rows.append([r.code or r.id, r.name or "-", f"{r.area_m2:.2f}" if r.area_m2 is not None else "-", _size(arch, r)])
        total += r.area_m2 or 0.0
    rows.append(["", "TOTAL", f"{total:.2f}", ""])
    return rows


def _size(arch: Architecture, r: Room) -> str:
    from epc_draw.arch.model import _box_m
    box = _box_m(r, arch.units_per_metre)
    return f"{box[2] - box[0]:.2f} x {box[3] - box[1]:.2f}" if box else "-"


def _opening_rows(arch: Architecture) -> List[List[str]]:
    rows = [["ID", "TYPE / TIPO", "WIDTH / ANCHO m", "WALL / MURO"]]
    for o in arch.openings:
        if o.kind in KIND_NAMES:
            rows.append([tag_name(o), " / ".join(KIND_NAMES[o.kind]), _metres(arch, o.width) if arch.units_per_metre else "-", o.wall or "-"])
    return rows


def _notes(arch: Architecture, d_scale: int) -> List[str]:
    level = f"{arch.level.name} ({arch.level.index})" if arch.level else "-"
    lines = ["GENERAL NOTES / NOTAS GENERALES",
             "1. Dimensions in metres, between wall axes. / Cotas en metros, entre ejes de muros.",
             "2. Room areas are clear areas inside the walls. / Las superficies son útiles, interiores a los muros."]
    if arch.units_per_metre and arch.wall_thickness:
        lines.append(f"3. Wall thickness {arch.wall_thickness / arch.units_per_metre:.2f} m. / Espesor de muros {arch.wall_thickness / arch.units_per_metre:.2f} m.")
    lines += [f"4. Level: {level}. Scale 1:{d_scale}. / Nivel: {level}. Escala 1:{d_scale}.",
              "5. Doors and windows are blocks with a wipeout. / Puertas y ventanas son bloques con wipeout."]
    return lines


def _wrapped(text: str, width_mm: float) -> List[str]:
    room = max(int(width_mm / (0.55 * 1.8)), 10)
    out, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > room:
            out.append(line)
            line = "      " + word if text[:2].strip(". ").isdigit() or text[1:2] == "." else word
        else:
            line = f"{line} {word}".strip()
    return out + [line]


def panel_items(arch: Architecture, free: Tuple[float, float, float, float], d_scale: int) -> Tuple[List[object], List[str]]:
    """The panel at the right of the sheet: the room schedule, the opening schedule and the notes. Returns the items and the warnings (when the tables do not fit)."""
    p = settings()
    x0, x1, y = free[2] - p["panel_mm"], free[2], free[1] + 28.0
    w = p["panel_mm"]
    items, warnings = [], []
    for rows, parts in ((_room_rows(arch), (0.18, 0.38, 0.18, 0.26)), (_opening_rows(arch), (0.14, 0.34, 0.26, 0.26))):
        out, y = _table(x0, y, [w * f for f in parts], rows)
        items += out
        y += 8.0
    for i, line in enumerate(_notes(arch, d_scale)):
        for part in _wrapped(line, w):
            items.append(TextItem(part, (x0 + 1.0, y + 4.0), "TXT_25" if i == 0 else "TXT_18", LAYER_NOTE, bold=i == 0))
            y += 5.0
    if y > free[3]:
        warnings.append("the tables of the sheet do not fit it: use a bigger sheet / las tablas no caben en la lámina: use una lámina mayor")
    return items, warnings


def presentation_items(arch: Architecture, m, free: Tuple[float, float, float, float], d_scale: int) -> Tuple[List[object], List[str]]:
    """Everything the presentation adds to the plan: dimension chains, tags and the panel of tables."""
    panel, warnings = panel_items(arch, free, d_scale)
    return dimension_items(arch, m) + tag_items(arch, m) + panel, warnings
