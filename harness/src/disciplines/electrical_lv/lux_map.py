"""The lux map of the lighting study, in the style of the false colours of DIALux: a smooth colour scale over the room, lines of equal level with their lux and a colour bar.

The discipline calculates nothing here: the lux of each cell and the level the room requires (its target) come from the engine result (`points.grid` and `target.value`, with the option
`return_grid`). What this module adds is the look: the grid of the engine is interpolated into finer cells, each gets the colour the scale gives to its lux as a fraction of the REQUIRED level
(blue: far under it, green: close, yellow: at it, orange and red: above it), and the lines of equal level are the marching-squares contours of the same grid at the fractions the look file lists
(the line of the required level is the thick one). The scale and the lines are in `harness/config/dxf/luxmap.json` (one source, no copy here): they are fractions, not norm values.

The light is the direct component of the luminaires only (inter-reflections are not included), as the engine says: it is a lower bound of the lumen-method average.
Frames: `room_map` gives everything in the frame of the room (x along `length_m`, y along `width_m`); `floor_map` puts it on the plan with the transform of the routing (`to_plan`).
"""
import copy
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


LOOK_FILE = "luxmap.json"
RETURN_GRID = {"return_grid": True}                      # the option of epc_lighting that gives the lux of every cell (what the map is drawn from)

TEXT = {
    "heading": {"en": "Lux map", "es": "Mapa de lux"},
    "intro": {"en": "Illuminance on the work plane, direct light of the luminaires only (inter-reflections are not included, so it is a lower bound of the average of the lumen method). The colour bar of each figure gives the lux; the thick line is the level the room requires, the thin ones join points of equal level and carry their lux.",
              "es": "Iluminancia en el plano de trabajo, solo luz directa de las luminarias (no incluye las inter-reflexiones, por eso es una cota inferior del promedio del método de los lúmenes). La barra de color de cada figura da los lux; la línea gruesa es el nivel que exige el ambiente y las finas unen puntos de igual nivel y llevan su valor en lux."},
    "bar": {"en": "lx", "es": "lx"},
    "bar_dxf": {"en": "% of the required level", "es": "% del nivel exigido"},
    "reading": {"en": "Required {target} lx. Lumen method: average {average} lx, {verdict}. Point by point (direct light): minimum {low} lx, average {avg} lx, maximum {high} lx; minimum / average {uniformity}.",
                "es": "Exigido {target} lx. Método de los lúmenes: promedio {average} lx, {verdict}. Punto por punto (luz directa): mínimo {low} lx, promedio {avg} lx, máximo {high} lx; mínimo / promedio {uniformity}."},
    "complies": {"en": "complies", "es": "cumple"},
    "fails": {"en": "does not comply", "es": "no cumple"},
    "lines": {"en": "Lines at {levels} lx ({ratios} of the required level).", "es": "Líneas a {levels} lx ({ratios} del nivel exigido)."},
    "no_grid": {"en": "No lux map: the luminaire of {rooms} has no photometry (intensity table), which the point-by-point calculation needs.",
                "es": "Sin mapa de lux: la luminaria de {rooms} no tiene fotometría (tabla de intensidades), que el cálculo punto a punto necesita."},
    "columns": {"en": ["room", "required (lx)", "average, lumen method (lx)", "min / avg / max, direct (lx)", "min / avg", "complies"],
                "es": ["ambiente", "exigido (lx)", "promedio, método de los lúmenes (lx)", "mín / prom / máx, directa (lx)", "mín / prom", "cumple"]},
    "sheet": {"en": "Lux map", "es": "Mapa de lux"},
    "yes": {"en": "yes", "es": "sí"},
    "no": {"en": "no", "es": "no"},
}


def say(key: str, language: str = "en", **fields: Any) -> str:
    """The text `key` in the language (`es`, else English) with its fields filled in."""
    return TEXT[key]["es" if language == "es" else "en"].format(**fields) if fields else TEXT[key]["es" if language == "es" else "en"]


def look() -> Dict[str, Any]:
    """The look of the map: `scale`, `contours`, `ticks`, `smooth_pdf`, `smooth_dxf` (harness/config/dxf/luxmap.json, read again every time)."""
    from epc_dxf import textstyle                                   # inside: the engines are not on the path of the permission hook that imports the stages
    return textstyle.load_file(LOOK_FILE)


def _mix(c1: str, c2: str, t: float) -> str:
    rgb = [round(int(c1[k:k + 2], 16) * (1 - t) + int(c2[k:k + 2], 16) * t) for k in (1, 3, 5)]
    return "#" + "".join(f"{v:02x}" for v in rgb)


def colour_at(ratio: float, stops: Sequence[Dict[str, Any]]) -> str:
    """The colour of the scale at a lux / required ratio (linear between the stops, the end colours beyond them)."""
    if ratio <= stops[0]["ratio"]:
        return stops[0]["color"]
    for lo, hi in zip(stops, stops[1:]):
        if ratio <= hi["ratio"]:
            return _mix(lo["color"], hi["color"], (ratio - lo["ratio"]) / (hi["ratio"] - lo["ratio"]))
    return stops[-1]["color"]


def refine(grid: Dict[str, Any], k: int) -> Dict[str, Any]:
    """The grid of the engine split into k x k parts per cell, bilinear between the centres of the cells (the edge values are kept at the walls): a grid in the same form, with `nx * k` by `ny * k` cells."""
    nx, ny, lux = grid["nx"], grid["ny"], grid["maintained_lux"]
    if k <= 1:
        return grid

    def at(x: float, y: float) -> float:                                       # x, y in cells, 0 at the centre of the first one
        x, y = min(max(x, 0.0), nx - 1.0), min(max(y, 0.0), ny - 1.0)
        i, j = min(int(x), max(nx - 2, 0)), min(int(y), max(ny - 2, 0))
        i2, j2, tx, ty = min(i + 1, nx - 1), min(j + 1, ny - 1), x - i, y - j
        top = lux[j * nx + i] * (1 - tx) + lux[j * nx + i2] * tx
        bottom = lux[j2 * nx + i] * (1 - tx) + lux[j2 * nx + i2] * tx
        return top * (1 - ty) + bottom * ty

    values = [round(at((i + 0.5) / k - 0.5, (j + 0.5) / k - 0.5), 1) for j in range(ny * k) for i in range(nx * k)]
    return {"nx": nx * k, "ny": ny * k, "maintained_lux": values}


def _edge(p1: Tuple[float, float], p2: Tuple[float, float], v1: float, v2: float, level: float) -> Tuple[float, float]:
    t = 0.0 if v2 == v1 else (level - v1) / (v2 - v1)
    return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))


SEGMENTS = {1: [("L", "B")], 2: [("B", "R")], 3: [("L", "R")], 4: [("R", "T")], 6: [("B", "T")], 7: [("L", "T")], 8: [("L", "T")], 9: [("B", "T")], 11: [("R", "T")], 12: [("L", "R")],
            13: [("B", "R")], 14: [("L", "B")]}
SADDLE = {5: ({True: [("L", "T"), ("B", "R")], False: [("L", "B"), ("R", "T")]}), 10: ({True: [("L", "B"), ("R", "T")], False: [("B", "R"), ("L", "T")]})}


def _cell_segments(xs: Sequence[float], ys: Sequence[float], z: Sequence[Sequence[float]], level: float) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """The pieces of the line of `level` over the samples z[j][i] at (xs[i], ys[j]) (marching squares, linear along each side)."""
    out = []
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            a, b, c, d = z[j][i], z[j][i + 1], z[j + 1][i + 1], z[j + 1][i]
            case = (a >= level) | ((b >= level) << 1) | ((c >= level) << 2) | ((d >= level) << 3)
            pa, pb, pc, pd = (xs[i], ys[j]), (xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1])
            sides = {"B": (pa, pb, a, b), "R": (pb, pc, b, c), "T": (pd, pc, d, c), "L": (pa, pd, a, d)}
            pairs = SADDLE[case][(a + b + c + d) / 4 >= level] if case in SADDLE else SEGMENTS.get(case, [])
            for s1, s2 in pairs:
                out.append((_edge(*sides[s1], level), _edge(*sides[s2], level)))
    return out


def _chain(segments: Sequence[Tuple[Tuple[float, float], Tuple[float, float]]]) -> List[List[Tuple[float, float]]]:
    """The pieces joined end to end into polylines (a closed line comes back with its first point at the end)."""
    key = lambda p: (round(p[0], 6), round(p[1], 6))                                       # noqa: E731
    at: Dict[Tuple[float, float], List[int]] = {}
    for n, (p, q) in enumerate(segments):
        at.setdefault(key(p), []).append(n)
        at.setdefault(key(q), []).append(n)
    used, lines = set(), []
    for n, (p, q) in enumerate(segments):
        if n in used:
            continue
        used.add(n)
        line = [p, q]
        for end in (1, 0):
            while True:
                tip = line[-1] if end else line[0]
                nxt = next((m for m in at.get(key(tip), []) if m not in used), None)
                if nxt is None:
                    break
                used.add(nxt)
                a, b = segments[nxt]
                other = b if key(a) == key(tip) else a
                line = line + [other] if end else [other] + line
        lines.append(line)
    return lines


def contours(grid: Dict[str, Any], width_m: float, length_m: float, level: float) -> List[List[Tuple[float, float]]]:
    """Lines of equal illuminance `level` over the grid of the engine: the samples sit at the centre of each cell and the edge samples are repeated at the walls, so a line reaches them."""
    nx, ny, lux = grid["nx"], grid["ny"], grid["maintained_lux"]
    dx, dy = length_m / nx, width_m / ny
    xs = [0.0] + [(i + 0.5) * dx for i in range(nx)] + [length_m]
    ys = [0.0] + [(j + 0.5) * dy for j in range(ny)] + [width_m]
    rows = [lux[j * nx:(j + 1) * nx] for j in range(ny)]
    rows = [rows[0]] + rows + [rows[-1]]
    z = [[r[0]] + list(r) + [r[-1]] for r in rows]
    return _chain(_cell_segments(xs, ys, z, level))


def _grid_of(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return (item.get("points") or {}).get("grid") or None


def room_map(item: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None, smooth: int = 1) -> Optional[Dict[str, Any]]:
    """The map of one room of the lighting result in the frame of the room, or None when it has no grid or no required level (no photometry, or the points were not asked for).
    `smooth`: parts per side each cell of the engine grid is split into (interpolated). {id, name, width_m, length_m, target_lux, average_lux, complies, stats, cells: [{rect, lux, color}],
    curves: [{ratio, level_lux, color, weight, points}], luminaires: [[x, y]]}."""
    grid, target = _grid_of(item), (item.get("target") or {}).get("value")
    if not grid or not target:
        return None
    cfg = cfg or look()
    geo = item["geometry"]
    width, length = geo["width_m"], geo["length_m"]
    fine = refine(grid, smooth)
    nx, ny, lux = fine["nx"], fine["ny"], fine["maintained_lux"]
    dx, dy = length / nx, width / ny
    cells = [{"rect": [round(i * dx, 4), round(j * dy, 4), round((i + 1) * dx, 4), round((j + 1) * dy, 4)], "lux": lux[j * nx + i], "color": colour_at(lux[j * nx + i] / target, cfg["scale"])}
             for j in range(ny) for i in range(nx)]
    curves = [{"ratio": c["ratio"], "level_lux": round(c["ratio"] * target, 1), "color": c["color"], "weight": c.get("weight", 0.5),
               "points": [[round(x, 4), round(y, 4)] for x, y in line]} for c in cfg["contours"] for line in contours(fine, width, length, c["ratio"] * target)]
    points = item["points"]
    return {"id": item["id"], "name": item.get("name"), "width_m": width, "length_m": length, "target_lux": target,
            "average_lux": (item.get("verification") or {}).get("average_lux"), "complies": (item.get("verification") or {}).get("complies"),
            "stats": {k: points.get(k) for k in ("min_lux", "avg_lux", "max_lux", "min_over_avg")}, "cells": cells, "curves": curves,
            "luminaires": [[p["x_m"], p["y_m"]] for p in (item.get("layout") or {}).get("positions", [])]}


def rooms_without_map(result: Dict[str, Any]) -> List[str]:
    """Ids of the rooms of a lighting result that have no map."""
    return [r["id"] for r in result.get("rooms", []) if _grid_of(r) is None or not (r.get("target") or {}).get("value")]


def _bar(cfg: Dict[str, Any], x: float, y: float, w: float, h: float, tick_text: Callable[[float], str], steps: int = 24) -> Dict[str, Any]:
    """A colour bar (the scale from its top, the highest ratio, to its bottom) in metres with the text of each tick: {cells: [{rect, color}], ticks: [{at, text}]}."""
    top = cfg["scale"][-1]["ratio"]
    cells = [{"rect": [round(x, 4), round(y + h * k / steps, 4), round(x + w, 4), round(y + h * (k + 1) / steps, 4)], "color": colour_at(top * (1 - (k + 0.5) / steps), cfg["scale"])} for k in range(steps)]
    ticks = [{"at": [round(x + w, 4), round(y + h * (1 - r / top), 4)], "text": tick_text(r)} for r in cfg["ticks"] if 0 <= r <= top]
    return {"cells": cells, "ticks": ticks}


def floor_map(items: Sequence[Dict[str, Any]], boxes: Dict[str, Sequence[float]], rooms: Dict[str, Dict[str, Any]], to_plan: Callable[..., Tuple[float, float]]) -> Optional[Dict[str, Any]]:
    """The map of the lit rooms of a floor on its plan (metres, the frame of the architecture): each room of `items` (lighting result) laid in its box with `to_plan(box, room, x, y)`, with a colour bar
    beside the plan. None when no room has a map. {"rooms": [{id, name, box, target_lux, average_lux, complies, stats, cells, curves}], "bar": {cells, ticks, caption, at}}."""
    cfg = look()
    out = []
    for item in items:
        local = room_map(item, cfg, int(cfg.get("smooth_dxf", 1)))
        if local is None:
            continue
        box, room = boxes[item["id"]], rooms[item["id"]]
        place = lambda x, y, box=box, room=room: list(to_plan(box, room, x, y))                       # noqa: E731
        cells = []
        for c in local["cells"]:
            (x0, y0), (x1, y1) = place(c["rect"][0], c["rect"][1]), place(c["rect"][2], c["rect"][3])
            cells.append({"rect": [round(min(x0, x1), 4), round(min(y0, y1), 4), round(max(x0, x1), 4), round(max(y0, y1), 4)], "lux": c["lux"], "color": c["color"]})
        curves = [dict(c, points=[place(x, y) for x, y in c["points"]]) for c in local["curves"]]
        out.append({"id": local["id"], "name": local["name"], "box": list(box), "target_lux": local["target_lux"], "average_lux": local["average_lux"], "complies": local["complies"],
                    "stats": local["stats"], "cells": cells, "curves": curves})
    if not out:
        return None
    right, top, bottom = max(r["box"][2] for r in out), min(r["box"][1] for r in out), max(r["box"][3] for r in out)
    height = min(max((bottom - top) * 0.5, 3.0), 8.0)
    bar = _bar(cfg, right + 1.0, top, 0.6, height, lambda r: f"{round(r * 100):g} %")
    return {"rooms": out, "bar": dict(bar, caption={"en": say("bar_dxf", "en"), "es": say("bar_dxf", "es")}, at=[round(right + 1.0, 4), round(top - 0.5, 4)])}


def _fmt(value: Any) -> str:
    return "" if value is None else (f"{value:g}" if isinstance(value, (int, float)) else str(value))


def _rect_shape(c: Dict[str, Any]) -> Dict[str, Any]:
    x0, y0, x1, y1 = c["rect"]
    return {"s": "poly", "points": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], "fill": c["color"], "stroke": c["color"], "lw": 0.3}


def _curve_shapes(curve: Dict[str, Any]) -> List[Dict[str, Any]]:
    pts = curve["points"]
    mid = pts[len(pts) // 2]
    return [{"s": "line", "points": [pts[k], pts[k + 1]], "stroke": curve["color"], "lw": curve["weight"]} for k in range(len(pts) - 1)] + [
        {"s": "text", "x": mid[0], "y": mid[1], "text": _fmt(curve["level_lux"]), "size": 6, "color": curve["color"], "bold": True, "align": "center"}]


def _bar_shapes(rm: Dict[str, Any], cfg: Dict[str, Any], size: float, language: str) -> List[Dict[str, Any]]:
    """The colour bar of a room figure to the right of the room, with the lux of each tick and its unit."""
    x, y = rm["length_m"] + size * 0.05, rm["width_m"] * 0.08
    bar = _bar(cfg, x, y, size * 0.045, rm["width_m"] * 0.84, lambda r: _fmt(round(r * rm["target_lux"])))
    return ([_rect_shape(c) for c in bar["cells"]]
            + [{"s": "text", "x": t["at"][0] + size * 0.012, "y": t["at"][1] + size * 0.012, "text": t["text"], "size": 6.5, "color": "#111111"} for t in bar["ticks"]]
            + [{"s": "text", "x": x, "y": y - size * 0.02, "text": say("bar", language), "size": 6.5, "color": "#111111", "bold": True}])


def room_figure(rm: Dict[str, Any], language: str = "en", cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The figure block of a report (`epc_drawing.export.report_pdf`) of one room map: the smooth colour field, the lines with their lux, the room outline, the luminaires and, on the right, the colour bar
    with the lux of each tick, y growing downwards."""
    cfg = cfg or look()
    size = max(rm["length_m"], rm["width_m"])
    shapes: List[Dict[str, Any]] = [_rect_shape(c) for c in rm["cells"]]
    shapes += [s for curve in rm["curves"] for s in _curve_shapes(curve)]
    shapes.append({"s": "poly", "points": [[0, 0], [rm["length_m"], 0], [rm["length_m"], rm["width_m"]], [0, rm["width_m"]]], "fill": None, "stroke": "#222222", "lw": 1.6})
    shapes += [{"s": "circle", "x": x, "y": y, "r": size * 0.014, "fill": "#ffffff", "stroke": "#111111", "lw": 0.9} for x, y in rm["luminaires"]]
    shapes += _bar_shapes(rm, cfg, size, language)
    pad = size * 0.04
    return {"type": "figure", "title": f"{say('heading', language)}: {rm['name'] or rm['id']}", "bounds": [-pad, -pad, rm["length_m"] + size * 0.2, rm["width_m"] + pad], "max_height": 260,
            "caption": "", "shapes": shapes}


def reading(rm: Dict[str, Any], language: str = "en") -> str:
    """The reading of a room map: what it requires and what the engine found (lumen method and point by point)."""
    s = rm["stats"]
    return say("reading", language, target=_fmt(rm["target_lux"]), average=_fmt(rm["average_lux"]), verdict=say("complies" if rm["complies"] else "fails", language),
               low=_fmt(s["min_lux"]), avg=_fmt(s["avg_lux"]), high=_fmt(s["max_lux"]), uniformity=_fmt(s["min_over_avg"]))


def lines_note(rm: Dict[str, Any], language: str = "en") -> str:
    """The sentence that says which lines the figure of a room carries."""
    seen = sorted({(c["ratio"], c["level_lux"]) for c in rm["curves"]})
    if not seen:
        return ""
    return say("lines", language, levels=", ".join(_fmt(lx) for _, lx in seen), ratios=", ".join(f"{round(r * 100):g} %" for r, _ in seen))


def study_blocks(result: Dict[str, Any], language: str = "en") -> List[Dict[str, Any]]:
    """The blocks of the lighting study report for the maps: the intro and, per room, the reading and the figure with its lines; a note for the rooms without a map. Empty without any map."""
    cfg = look()
    maps = [m for m in (room_map(r, cfg, int(cfg.get("smooth_pdf", 1))) for r in result.get("rooms", [])) if m]
    blocks: List[Dict[str, Any]] = []
    missing = rooms_without_map(result)
    if maps:
        blocks += [{"type": "h", "text": say("heading", language)}, {"type": "p", "text": say("intro", language)}]
        for m in maps:
            fig = room_figure(m, language, cfg)
            fig["caption"] = lines_note(m, language)
            blocks += [{"type": "p", "text": f"{m['name'] or m['id']}. {reading(m, language)}"}, fig]
    if missing:
        blocks.append({"type": "p", "text": say("no_grid", language, rooms=", ".join(missing))})
    return blocks
