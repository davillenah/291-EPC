"""Wall brackets: found on the wall beside the tray, within the reach, at the height of the tray."""
import pytest

from epc_draw.plan import core, wall_bracket

TRAY = {"id": "t1", "tag": "BN1", "kind": "BN", "discipline": "electrica_BT", "level": "L0", "layer": "ELEC-BANDEJA", "shape": "run", "section": "rect", "width_m": 0.3, "height_m": 0.1,
        "path": [[0, 0, 2.5], [4, 0, 2.5]]}


def wall(y0, y1, z0=0.0, z1=3.0):
    return {"id": "w", "tag": "w", "kind": "wall", "discipline": "arquitectura", "level": "L0", "layer": "A",
            "mesh": {"vertices": [[x, y, z] for x in (-1, 5) for y in (y0, y1) for z in (z0, z1)], "faces": [[0, 1, 3, 2]]}}


SPEC = {"spacing_m": 2.0, "reach_m": 0.5}


def test_a_bracket_sits_on_the_wall_beside_the_tray():
    made = wall_bracket.brackets([TRAY], [wall(0.4, 0.6)], SPEC)
    assert [m["support"] for m in made] == ["wall_bracket"] * 2                # two places along 4 m at 2 m
    ys = [v[1] for v in made[0]["mesh"]["vertices"]]
    assert max(ys) == pytest.approx(0.4)                                        # the plate is against the face of the wall
    assert min(ys) == pytest.approx(-0.15)                                      # the arm runs under all the width of the tray
    assert made[0]["layer"] == "MEC-SOPORTE" and made[0]["run"] == "t1"


def test_the_nearer_wall_of_the_two_sides_wins_and_a_far_wall_gets_nothing():
    both = wall_bracket.brackets([TRAY], [wall(0.4, 0.6), wall(-1.0, -0.8)], SPEC)
    assert all(max(v[1] for v in m["mesh"]["vertices"]) > 0 for m in both)       # the wall at +0.4 (edge gap 0.25), not the one at -0.8 (gap 0.65)
    assert wall_bracket.brackets([TRAY], [wall(2.0, 2.2)], SPEC) == []            # beyond the reach
    assert wall_bracket.brackets([TRAY], [wall(0.4, 0.6, 3.5, 6.0)], SPEC) == []  # not at the height of the tray


def test_the_spec_needs_both_values():
    with pytest.raises(core.PlanError):
        wall_bracket.brackets([TRAY], [], {"spacing_m": 2.0})


def test_a_tray_wider_than_the_given_width_gets_the_heavy_bracket_on_the_wall():
    made = wall_bracket.brackets([TRAY], [wall(0.4, 0.6)], dict(SPEC, heavy_over_m=0.25))
    assert [m["support"] for m in made] == ["wall_bracket_heavy"] * 2
    ys = [v[1] for v in made[0]["mesh"]["vertices"]]
    assert max(ys) == pytest.approx(0.4)                                        # the plate is still against the wall
    assert wall_bracket.brackets([TRAY], [wall(0.4, 0.6)], dict(SPEC, heavy_over_m=0.5))[0]["support"] == "wall_bracket"
    with pytest.raises(core.PlanError):
        wall_bracket.brackets([TRAY], [wall(0.4, 0.6)], dict(SPEC, heavy_over_m=-1))
