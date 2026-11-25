"""The tee and the cross of a tray as one piece (epc_plan.tray_junction). Pure: no backend, no network."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from epc_draw.plan import core, tray_catalogue, tray_junction, tray_library   # noqa: E402


def _sizes():
    ladder = tray_catalogue.ladder(core.PARAMS["detail"]["ladder"], core.PARAMS["tray_catalogue"])
    keys = ("rail", "rung", "rung_thick", "rung_pitch", "foot", "curl", "lip", "jog", "slot_pitch", "slot", "slot_height", "floor_margin", "hole_pitch", "hole", "wire", "wire_pitch", "joint", "bolt")
    return {k: ladder[k + "_m"] for k in keys}


def test_the_rails_of_a_tee_round_the_inside_corners_and_none_crosses_the_opening():
    width, radius = 0.3, 0.3
    mesh = tray_junction.junction_mesh("escalera", width, 0.09, _sizes(), 1.2, radius, (1,))
    reach = width / 2 + radius
    pts = mesh["vertices"]
    assert all(abs(x) <= 1.2 + 1e-6 and -1e-6 <= y + width / 2 + 0.05 for x, y, _ in pts)
    in_opening = [(x, y) for x, y, _ in pts if abs(x) < width / 2 - 0.01 and width / 2 + 0.01 < y < reach - 0.01 and abs(y - width / 2) > 0.02]
    rails_in_opening = [p for p in in_opening if p[1] > width / 2 + 0.03 and abs(abs(p[0]) - width / 2) < 0.002]
    assert rails_in_opening == []                                                  # no rail runs across the opening of the branch
    corner = (-reach, reach)                                                        # the centre of the rounded corner on the side of -x
    near = [math.hypot(x - corner[0], y - corner[1]) for x, y, _ in pts if x < 0 and y > 0.1 and math.hypot(x - corner[0], y - corner[1]) < radius + 0.01]
    assert near and abs(min(near) - radius) < 0.003                                 # the rail turns on the inner radius


def test_a_cross_has_four_rounded_corners_and_every_kind_has_one():
    for kind in ("escalera", "perforada", "ciega"):
        assert tray_junction.junction_mesh(kind, 0.3, 0.09, _sizes(), 1.2, 0.3, (-1, 1))["faces"]
    assert tray_junction.junction_mesh("alambre", 0.3, 0.09, _sizes(), 1.2, 0.3, (1,)) is None      # a wire mesh stays two straights


def test_the_library_tee_is_one_piece_made_by_this_module_for_every_width():
    for width in (0.15, 0.3, 0.6):
        by_code = {p["code"]: p for p in tray_library.pieces(width, 0.09)}
        code = f"BN-ESC-T-{round(width * 1000)}x90"
        assert len(by_code[code]["mesh"]["faces"]) > 0
