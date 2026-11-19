"""A house asked in words becomes (1) a proposal of rooms in metres, (2) the plan description `epc_arch.author` draws and (3) the inputs of the pipeline.

Nothing here calculates: the rooms, doors and windows are only a layout PROPOSAL (sizes in `house_defaults.json`, all pending review) that the page shows in an editable
table; the plans, lighting, receptacles, circuits and documents are made by the engines. Layout rule: a public band to the south (living, kitchen, garage) and a private band to the north (bedrooms, bathrooms, laundry), touching.
There is no hall on purpose: the plan reader splits a hall into phantom rooms when the walls of the two sides do not line up (BACKLOG), so the bedrooms open into the living room. Both bands get the same total width (the rooms of the shorter one grow in proportion), so every wall lines up with the hall.
"""
import json
import re
from pathlib import Path

DEFAULTS = json.loads((Path(__file__).with_name("house_defaults.json")).read_text(encoding="utf-8"))
ORDER = {"public": ("living", "kitchen", "garage"), "private": ("bedroom", "bathroom", "laundry")}
SIDES = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}


def _name(kind, lang, n, total):
    base = DEFAULTS["rooms"][kind]["name"][lang if lang in ("es", "en") else "es"]
    return f"{base} {n}" if total > 1 else base


def _band(kinds, spec, lang):
    """[(kind, name, width)] of one band in order; the usual dwelling (one living, one kitchen) is added when the request names no public room."""
    out = []
    for kind in kinds:
        total = spec.get(kind, 0)
        out += [(kind, _name(kind, lang, n + 1, total), DEFAULTS["rooms"][kind]["width_m"]) for n in range(total)]
    return out


def _fit(band, width):
    """The rooms of a band share the width it lacks in proportion to their own (the last one takes the rounding)."""
    if not band:
        return band
    k = width / sum(w for _, _, w in band)
    widths = [round(w * k, 2) for _, _, w in band]
    widths[-1] = round(width - sum(widths[:-1]), 3)
    return [(kind, name, w) for (kind, name, _), w in zip(band, widths)]


def _cuts(band):
    """x of the walls between the rooms of a band (not its two ends)."""
    out, x = [], 0.0
    for _, _, w in band[:-1]:
        x += w
        out.append(round(x, 3))
    return out


def _snap(cuts, fixed):
    """`cuts` moved onto the nearest wall of `fixed` (each used once, order kept): walls that line up are read as one wall by `epc_arch`; a wall stub that ends in the middle of a room splits it."""
    used, out = set(), []
    for c in cuts:
        free = [f for f in fixed if f not in used and (not out or f > out[-1] + 1.0)]
        pick = min(free, key=lambda f: abs(f - c)) if free else c
        used.add(pick)
        out.append(pick)
    return out


def _regroup(band, edges):
    return [(k, n, round(edges[i + 1] - edges[i], 3)) for i, (k, n, _) in enumerate(band)]


def _align(public, private):
    """The two bands with their inner walls lined up. The private band is as wide as a wall of the public one (so no public wall ends in the middle of a private room) and the public
    walls under it move onto the private walls; when the private band has as many walls as the public one it spans the whole width."""
    if not public or not private:
        return public, private
    edges = [0.0] + [round(sum(w for _, _, w in public[:i + 1]), 3) for i in range(len(public))]
    inside = len(private) - 1
    natural = sum(w for _, _, w in private)
    reach = [i for i in range(1, len(edges)) if i - 1 <= inside]
    pick = min(reach, key=lambda i: abs(edges[i] - natural))
    width = edges[pick]
    private = _fit(private, width)
    snapped = _snap(edges[1:pick], _cuts(private))
    edges = [0.0] + snapped + edges[pick:]
    return _regroup(public, edges), private


def _boxes(band, south, depth):
    x, out = 0.0, []
    for kind, name, width in band:
        out.append((kind, name, [round(x, 3), south, round(x + width, 3), round(south + depth, 3)]))
        x += width
    return out


def _bands(spec, lang):
    """(public, private) bands of [(kind, name, width)] sharing one total width, their inner walls lined up."""
    public, private = _band(ORDER["public"], spec, lang), _band(ORDER["private"], spec, lang)
    width = max(sum(w for _, _, w in b) for b in (public, private) if b) if (public or private) else 0
    return _align(_fit(public, width), _fit(private, width))


def _stack(spec, lang):
    """Rows of a two-floor house: the public rooms on the ground floor (PB), the private ones upstairs (P1), the same width, a stair at the east end of both (same box)."""
    groups = [("PB", _band(ORDER["public"], spec, lang), DEFAULTS["bands"]["public_depth_m"]), ("P1", _band(ORDER["private"], spec, lang), DEFAULTS["bands"]["private_depth_m"])]
    width = max(sum(w for _, _, w in b) for _, b, _ in groups if b)
    rows = []
    for prefix, band, depth in groups:
        if not band:
            continue
        stair = ("stair", _name("stair", lang, 1, 1), DEFAULTS["rooms"]["stair"]["width_m"])
        boxes = _boxes(_fit(band, width) + [stair], 0.0, depth)
        rows += [{"code": f"{prefix}-{i:02d}", "name": name, "kind": kind, "west": b[0], "south": b[1], "east": b[2], "north": b[3]} for i, (kind, name, b) in enumerate(boxes, 1)]
    return rows


def _spec(rooms):
    """(counts of the kinds to draw, kinds added): the usual dwelling (one living room, one kitchen) is added when rooms were named without them."""
    spec = {k: int(v) for k, v in rooms.items() if k in DEFAULTS["rooms"] and v and k != "stair"}
    added = [k for k in ("living", "kitchen") if not spec.get(k)] if any(spec.values()) else []
    spec.update({k: 1 for k in added})
    return spec, added


def _rows(boxes):
    return [{"code": f"PB-{i:02d}", "name": name, "kind": kind, "west": b[0], "south": b[1], "east": b[2], "north": b[3]} for i, (kind, name, b) in enumerate(boxes, 1)]


def propose(rooms, lang="es", floors=1):
    """The rooms as rows [{code, name, kind, west, south, east, north}] for the counts the request named (`brief.interpret(...)["rooms"]`): one floor (codes PB-nn), or two (PB-nn, P1-nn, with a stair).

    Returns (rows, added): `added` lists the room kinds the request did not name and the proposal put in (living and kitchen)."""
    spec, added = _spec(rooms)
    if floors == 2 and any(spec.get(k) for k in ORDER["private"]):
        return _stack(spec, lang), added
    public, private = _bands(spec, lang)
    pub, prv = DEFAULTS["bands"]["public_depth_m"], DEFAULTS["bands"]["private_depth_m"]
    return _rows(_boxes(public, 0.0, pub) + _boxes(private, pub if public else 0.0, prv)), added


def box_of(row):
    return [float(row[k]) for k in ("west", "south", "east", "north")]


def _shared(a, b, side):
    """(start, end) along the side of box `a` it shares with box `b` on that side, or None."""
    if side in "EW":
        wall = a[2] if side == "E" else a[0]
        touches = abs(wall - (b[0] if side == "E" else b[2])) < 1e-6
        lo, hi = max(a[1], b[1]), min(a[3], b[3])
    else:
        wall = a[3] if side == "N" else a[1]
        touches = abs(wall - (b[1] if side == "N" else b[3])) < 1e-6
        lo, hi = max(a[0], b[0]), min(a[2], b[2])
    return (lo, hi) if touches and hi - lo > 1e-6 else None


def _sides(rows):
    """{code: {side: [(neighbour code, lo, hi)]}} from the boxes."""
    out = {r["code"]: {s: [] for s in SIDES} for r in rows}
    for a in rows:
        for b in rows:
            if a is b:
                continue
            for s in SIDES:
                seg = _shared(box_of(a), box_of(b), s)
                if seg:
                    out[a["code"]][s].append((b["code"], *seg))
    return out


def kind_word(row):
    """`living` for a room whose name says living, dining or sitting room (es / en), else an empty string."""
    return "living" if re.search(r"living|sala|estar|comedor", row["name"].lower()) else ""


def _public(row):
    return bool(re.search(r"cocina|kitchen|cochera|garage", row["name"].lower()))


def _is_hall(row):
    return bool(re.search(r"pasillo|hall|corredor|corridor", row["name"].lower()))


def _door(row, side, lo, hi, width):
    box = box_of(row)
    start = box[0] if side in "NS" else box[1]
    return {"room": row["code"], "side": side, "width_m": width, "offset_m": round((lo + hi) / 2 - start, 3), "opens": "in"}


def _door_target(row, mine, by_code):
    """(side, neighbour, lo, hi) the door of a room opens onto: a hall, else the living room, else the longest shared wall; only walls that take the door (width + 0.3 m)."""
    width = 0.7 if _area(row) < 8 else 0.8
    options = [(s, c, lo, hi) for s, segs in mine.items() for c, lo, hi in segs if hi - lo >= width + 0.3]
    rank = lambda o: (0 if _is_hall(by_code[o[1]]) else 1 if kind_word(by_code[o[1]]) else 2 if _public(by_code[o[1]]) else 3, -(o[3] - o[2]))    # noqa: E731
    return sorted(options, key=rank)[0] if options else None


def _entrance(row, mine):
    """The street door of the living room: on its south wall when that wall is outside, else on the first outside wall."""
    outer = [s for s, segs in mine.items() if not segs]
    if not outer:
        return None
    side = "S" if "S" in outer else outer[0]
    box = box_of(row)
    start, end = (box[0], box[2]) if side in "NS" else (box[1], box[3])
    return {"room": row["code"], "side": side, "width_m": 0.9, "offset_m": round((end - start) / 2, 3), "opens": "out"}


def _room_openings(r, mine, by_code):
    """(door or None, windows) of one room."""
    target = None if _is_hall(r) else _door_target(r, mine, by_code)
    width = 0.7 if _area(r) < 8 else 0.8
    door = _door(r, target[0], target[2], target[3], width) if target else None
    windows = [{"room": r["code"], "side": s, "width_m": 0.6 if _area(r) < 8 else 1.2} for s, segs in mine.items() if not segs and not _is_hall(r)]
    return door, windows


def openings(rows):
    """(doors, windows) of the boxes: each room a door onto a hall, the living room or its longest neighbour; the first living room a street door; a window on every outside wall."""
    sides, doors, windows = _sides(rows), [], []
    by_code = {r["code"]: r for r in rows}
    for r in rows:
        door, wins = _room_openings(r, sides[r["code"]], by_code)
        doors += [door] if door else []
        windows += wins
    living = next((r for r in rows if kind_word(r)), None)
    street = _entrance(living, sides[living["code"]]) if living else None
    return doors + ([street] if street else []), windows


def _area(row):
    b = box_of(row)
    return (b[2] - b[0]) * (b[3] - b[1])


def floors_of(rows):
    """[(prefix, rows)] grouped by the part of the room code before the dash (`PB`, `P1`), in the order they appear."""
    out = {}
    for r in rows:
        out.setdefault(r["code"].split("-")[0], []).append(r)
    return list(out.items())


def floor_index(prefix):
    """Level of a floor from its prefix: PB 0, P1 1, P2 2."""
    m = re.fullmatch(r"P(\d+)", prefix)
    return int(m.group(1)) if m else 0


def floor_name(prefix, lang="es"):
    names = DEFAULTS["floor_names"].get(prefix) or {"es": f"PLANTA {floor_index(prefix)}", "en": f"FLOOR {floor_index(prefix)}"}
    return names[lang if lang in names else "es"]


def stair_point(rows):
    """Centre of the stair room moved 5 cm (a board on the exact centre of a room reaches no luminaire), or None."""
    row = next((r for r in rows if re.search(r"escalera|stair", r["name"].lower())), None)
    if not row:
        return None
    x, y = _center(row)
    return {"x_m": round(x + 0.05, 3), "y_m": round(y + 0.05, 3)}


def floor_description(rows, name="PLANTA BAJA", index=0, wall_thickness_m=None, wall_height_m=None, elevation_m=0.0):
    """The `epc_arch.author` description of the floor (rooms as boxes, doors, windows, heights)."""
    doors, windows = openings(rows)
    desc = {"name": name, "index": int(index), "wall_thickness_m": float(wall_thickness_m or DEFAULTS["wall_thickness_m"]),
            "rooms": [{"code": r["code"], "name": r["name"], "box_m": box_of(r)} for r in rows], "doors": doors, "windows": windows}
    if wall_height_m:
        desc["heights_m"] = {"wall_height_m": float(wall_height_m), "door_head_m": 2.1, "window_sill_m": 0.9, "window_head_m": 2.1, "slab_m": 0.2, "elevation_m": float(elevation_m)}
    return desc


def _center(row):
    b = box_of(row)
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def board_point(rows):
    """Where the board goes: the middle of the hall, the laundry, the garage or the kitchen (the first that exists, else the first room), moved 5 cm: a board on the exact centre of a room reaches no luminaire (the routing fails)."""
    stair = stair_point(rows)
    if stair:
        return stair
    pick = lambda words: next((r for r in rows if re.search(words, r["name"].lower())), None)    # noqa: E731
    row = pick(r"pasillo|hall|corredor") or pick(r"lavadero|laundry|cochera|garage") or pick(r"cocina|kitchen") or rows[0]
    x, y = _center(row)
    return {"x_m": round(x + 0.05, 3), "y_m": round(y + 0.05, 3)}
