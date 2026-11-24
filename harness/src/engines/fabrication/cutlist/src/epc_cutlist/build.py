"""Cutting plan (cut list) of one set of parts: pure functions, no I/O, no data tables.

The engine places the parts into stock bars (best fit decreasing), keeps the saw kerf of every cut, groups equal parts into lines and marks the cut angles
whose reliability the person must check. It holds no norm value, no catalog and no price: stock lengths, kerf, lengths and angles are inputs.
"""
from epc_cutlist import inputs
from epc_cutlist.errors import CutlistError
from epc_cutlist.messages import ASSUMPTIONS, MARKS_LEGEND

EPS = 1e-9
ROUND = 6


def _marks(part):
    """The confidence marks of a part's cut angles: '?' unknown, '~' derived, '-' both ends cut in the same direction."""
    if part["angle_source"] == "unknown":
        return ["?"]
    marks = ["~"] if part["angle_source"] == "derived" else []
    a1, a2 = part["angle_1_deg"], part["angle_2_deg"]
    if a1 and a2 and (a1 > 0) == (a2 > 0):
        marks.append("-")
    return marks


def _pieces(parts, kerf):
    """One piece per unit of each part, with its cut size (length plus kerf)."""
    pieces = []
    for p in parts:
        marks = _marks(p)
        for index in range(1, p["quantity"] + 1):
            pieces.append({"part": p, "index": index, "length_mm": p["length_mm"], "cut_mm": round(p["length_mm"] + kerf, ROUND), "marks": marks})
    return sorted(pieces, key=lambda x: (-x["cut_mm"], x["part"]["id"], x["index"]))


def _best_bar(bars, cut):
    """The open bar that leaves the least space after the piece (the earliest one on a tie), or None."""
    fits = [b for b in bars if b["left_mm"] + EPS >= cut]
    return min(fits, key=lambda b: (round(b["left_mm"] - cut, ROUND), b["number"])) if fits else None


def _open_bar(bars, entries, piece, material):
    """A new bar of the shortest stock length that holds the piece and is still available; raises when there is none."""
    fitting = [e for e in entries if e["length_mm"] + EPS >= piece["cut_mm"]]
    pid = piece["part"]["id"]
    if not fitting:
        raise CutlistError("err_part_too_long", part=pid, length=piece["length_mm"], cut=piece["cut_mm"], material=material, longest=entries[-1]["length_mm"])
    for e in fitting:
        if e["count"] is None or e["count"] > 0:
            if e["count"] is not None:
                e["count"] -= 1
            bar = {"number": len(bars) + 1, "bar_id": f"{material}-{len(bars) + 1:03d}", "material": material, "stock_length_mm": e["length_mm"], "parts": [],
                   "used_mm": 0.0, "left_mm": e["length_mm"]}
            bars.append(bar)
            return bar
    raise CutlistError("err_stock_exhausted", part=pid, material=material)


def _place(bar, piece):
    bar["parts"].append({"part_id": piece["part"]["id"], "index": piece["index"], "length_mm": piece["length_mm"], "cut_mm": piece["cut_mm"],
                         "angle_1_deg": piece["part"]["angle_1_deg"], "angle_2_deg": piece["part"]["angle_2_deg"], "marks": piece["marks"]})
    bar["used_mm"] = round(bar["used_mm"] + piece["cut_mm"], ROUND)
    bar["left_mm"] = round(bar["stock_length_mm"] - bar["used_mm"], ROUND)


def _plan_material(material, pieces, entries):
    """The bars of one material. Counts of limited stock are consumed from a private copy."""
    available = [dict(e) for e in entries]
    bars = []
    for piece in pieces:
        bar = _best_bar(bars, piece["cut_mm"]) or _open_bar(bars, available, piece, material)
        _place(bar, piece)
    return bars


def _finish(bar):
    out = {k: v for k, v in bar.items() if k != "number"}
    out["utilisation_pct"] = round(100 * bar["used_mm"] / bar["stock_length_mm"], 2)
    return out


def _summary(bars):
    stock = round(sum(b["stock_length_mm"] for b in bars), ROUND)
    used = round(sum(b["used_mm"] for b in bars), ROUND)
    net = round(sum(p["length_mm"] for b in bars for p in b["parts"]), ROUND)
    return {"bars": len(bars), "parts": sum(len(b["parts"]) for b in bars), "stock_mm": stock, "used_mm": used, "net_mm": net,
            "kerf_mm_total": round(used - net, ROUND), "waste_mm": round(stock - used, ROUND), "utilisation_pct": round(100 * used / stock, 2) if stock else 0.0}


def _groups(parts):
    """Equal parts grouped into lines by (material, size, length rounded to 0.1 mm, both angles, angle source)."""
    groups = {}
    for p in parts:
        key = (p["material"], p["size"] or "", round(p["length_mm"], 1), p["angle_1_deg"], p["angle_2_deg"], p["angle_source"])
        groups.setdefault(key, []).append(p)
    lines = []
    for key in sorted(groups, key=lambda k: (k[0], k[1], -k[2], str(k[3]), str(k[4]), k[5])):
        members = groups[key]
        lines.append({"material": key[0], "size": key[1] or None, "length_mm": key[2], "angle_1_deg": key[3], "angle_2_deg": key[4], "angle_source": key[5],
                      "quantity": sum(m["quantity"] for m in members), "ids": [m["id"] for m in members], "marks": _marks(members[0])})
    return lines


def _issues(parts):
    return [f"{p['id']}: angle unknown (define it before cutting)" for p in parts if p["angle_source"] == "unknown"]


def _check_materials(parts, stock):
    for p in parts:
        if p["material"] not in stock:
            raise CutlistError("err_stock_missing_material", part=p["id"], material=p["material"])


def _all_bars(parts, stock, kerf):
    """The finished bars of every material, materials in alphabetical order."""
    bars = []
    for material in sorted({p["material"] for p in parts}):
        mine = [p for p in parts if p["material"] == material]
        bars += _plan_material(material, _pieces(mine, kerf), stock[material])
    return [_finish(b) for b in bars]


def _summaries(bars):
    by_material = {}
    for bar in bars:
        by_material.setdefault(bar["material"], []).append(bar)
    return {m: _summary(b) for m, b in sorted(by_material.items())}


def build_cutlist(stock, parts, *, kerf_mm=None):
    """The cutting plan: `{kerf_mm, bars, summary, totals, groups, marks_legend, assumptions, issues}`.

    `stock` is `{material: [length_mm | {length_mm, count}, ...]}`; `parts` a list of `{id, material, length_mm, quantity?, size?, label?, angle_1_deg?,
    angle_2_deg?, angle_source?}`; `kerf_mm` is required (0 allowed). Deterministic: the same input gives the same plan.
    """
    kerf = inputs.kerf(kerf_mm)
    stock_in = inputs.stock(stock)
    parts_in = inputs.parts(parts)
    _check_materials(parts_in, stock_in)
    bars = _all_bars(parts_in, stock_in, kerf)
    marks = sorted({m for p in parts_in for m in _marks(p)})
    return {"kerf_mm": kerf, "bars": bars, "summary": _summaries(bars), "totals": _summary(bars), "groups": _groups(parts_in),
            "marks_legend": {m: MARKS_LEGEND[m] for m in marks}, "assumptions": list(ASSUMPTIONS), "issues": _issues(parts_in)}


def render_rows(plan):
    """Flat list of dicts, one per placed piece (`bar_id, material, stock_length_mm, part_id, index, length_mm, angle_1_deg, angle_2_deg, marks, bar_used_mm,
    bar_left_mm`). No file is written."""
    rows = []
    for bar in plan["bars"]:
        for p in bar["parts"]:
            rows.append({"bar_id": bar["bar_id"], "material": bar["material"], "stock_length_mm": bar["stock_length_mm"], "part_id": p["part_id"],
                         "index": p["index"], "length_mm": p["length_mm"], "angle_1_deg": p["angle_1_deg"], "angle_2_deg": p["angle_2_deg"],
                         "marks": "".join(p["marks"]), "bar_used_mm": bar["used_mm"], "bar_left_mm": bar["left_mm"]})
    return rows
