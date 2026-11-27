"""The two charts of a PV project as figure blocks of a report (PV-17): the irradiation disk and the shading abacus, drawn from what `epc_pv` returns in `result["charts"]`.

A figure is a list of shapes (see `epc_report.core.report_pdf`), so it prints in the PDF and in the Word file alike. Nothing is calculated: every cell takes the value the engine gave.
"""
import math

from epc_report.pv.texts import tr

STEPS = 4                                                   # points per arc of a sector
RAMP = ((0.0, (255, 247, 200)), (0.5, (250, 170, 60)), (1.0, (150, 20, 20)))      # low to high share of the best plane


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(int(round(c)) for c in rgb)


def _colour(t):
    t = min(max(t, 0.0), 1.0)
    for (t0, c0), (t1, c1) in zip(RAMP, RAMP[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return _hex(tuple(a + (b - a) * f for a, b in zip(c0, c1)))
    return _hex(RAMP[-1][1])


def _at(tilt, az, top=90.0):
    r, a = tilt / top, math.radians(az)
    return [r * math.sin(a), -r * math.cos(a)]


def _sector(t0, t1, a0, a1):
    arc = [a0 + (a1 - a0) * k / STEPS for k in range(STEPS + 1)]
    return [_at(t1, a) for a in arc] + [_at(t0, a) for a in reversed(arc)]


def _edges(values):
    mid = [(a + b) / 2.0 for a, b in zip(values, values[1:])]
    return [values[0]] + mid + [values[-1]]


def _disk_cells(disk, lo, span):
    tilts, azs, pct = disk["tilt_deg"], disk["azimuth_deg"], disk["pct"]
    te, half = _edges(tilts), (azs[1] - azs[0]) / 2.0 if len(azs) > 1 else 180.0
    return [{"s": "poly", "points": _sector(te[i], te[i + 1], a - half, a + half), "fill": _colour((pct[i][j] - lo) / span), "stroke": None, "lw": 0.2} for i in range(len(tilts)) for j, a in enumerate(azs)]


def _disk_frame(lang, disk):
    shapes = [{"s": "circle", "x": 0, "y": 0, "r": t / 90.0, "fill": None, "stroke": "#444444", "lw": 0.4} for t in disk["tilt_deg"][1:]]
    shapes += [{"s": "line", "points": [[0, 0], _at(90, a)], "stroke": "#444444", "lw": 0.3} for a in range(0, 360, 45)]
    for name, a in (("north", 0), ("east", 90), ("south", 180), ("west", 270)):
        x, y = _at(103, a)
        shapes.append({"s": "text", "x": x - 0.04, "y": y + 0.04, "text": tr(lang, "dir_" + name), "size": 7, "bold": True})
    bx, by = _at(disk["best"]["tilt_deg"], disk["best"]["azimuth_deg"])
    return shapes + [{"s": "circle", "x": bx, "y": by, "r": 0.03, "fill": "#ffffff", "stroke": "#000000", "lw": 1.2}]


def _disk_bar(lo, span):
    """The colour bar: five steps from the lowest to the highest share."""
    shapes = []
    for k in range(5):
        t = k / 4.0
        shapes += [{"s": "rect", "x": 1.35, "y": 0.8 - k * 0.3, "w": 0.18, "h": 0.28, "fill": _colour(t)},
                   {"s": "text", "x": 1.57, "y": 0.8 - k * 0.3 + 0.2, "text": f"{lo + span * t:.0f} %", "size": 6}]
    return shapes


def disk_figure(lang, disk):
    """The irradiation disk: tilt as radius (0 at the centre, 90 at the edge), orientation as angle (north up), colour by the share of the best plane."""
    pct = disk["pct"]
    lo, hi = min(min(r) for r in pct), max(max(r) for r in pct)
    span = (hi - lo) or 1.0
    shapes = _disk_cells(disk, lo, span) + _disk_frame(lang, disk) + _disk_bar(lo, span)
    return {"type": "figure", "title": tr(lang, "fig_disk"), "caption": tr(lang, "fig_disk_cap", tilt=disk["best"]["tilt_deg"], az=disk["best"]["azimuth_deg"]),
            "bounds": [-1.2, -1.2, 1.95, 1.2], "max_height": 300, "shapes": shapes}


def abacus_figure(lang, abacus):
    """The shading abacus: the cells of the sun path (azimuth against elevation), grey by the share the horizon hides, and the horizon profile when one was given."""
    cells = abacus["cells"]
    shapes = []
    xs, ys = [], []
    for c in cells:
        pts = [[x, -el] for x, el in c["outline"]]
        xs += [p[0] for p in pts]
        ys += [p[1] for p in pts]
        grey = 235 - 180 * float(c["cover"])
        shapes.append({"s": "poly", "points": pts, "fill": _hex((grey, grey, grey)), "stroke": "#555555", "lw": 0.4})
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        shapes.append({"s": "text", "x": cx - 2.5, "y": cy + 1.2, "text": c["id"], "size": 4.5})
    profile = abacus.get("profile") or []
    shapes += [{"s": "line", "points": [[a[0], -a[1]], [b[0], -b[1]]], "stroke": "#0050c8", "lw": 1.4} for a, b in zip(profile, profile[1:])]
    cap = tr(lang, "fig_abacus_cap", loss=abacus["loss_pct"]) + ("" if profile else " " + tr(lang, "no_horizon"))
    return {"type": "figure", "title": tr(lang, "fig_abacus"), "caption": cap, "bounds": [min(xs) - 5, min(ys) - 5, max(xs) + 5, max(ys) + 5], "max_height": 260, "shapes": shapes}
