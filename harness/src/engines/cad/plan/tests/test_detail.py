"""The parts a run is built from, its supports and the take-off (epc_plan.detail): the fabrication model. Pure: no backend, no network."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_plan import core, detail, scene3d, solid   # noqa: E402
import test_solid as S                                # noqa: E402

SPEC = {"spacing_m": 2.0, "slab_underside_m": {"L0": 3.0}}


def solids(*lines, nodes=(), discipline="electrica_BT"):
    return solid.solids(S.sheet(discipline=discipline, lines=list(lines), nodes=list(nodes)), "E1")


def tray():
    return solids(S.TRAY)                                  # 10 m east, a bend, 5 m north; 0.3 x 0.1 m at 2.6 m


def of(items, part):
    return [p for p in items if p["part"] == part]


class Parts(unittest.TestCase):
    def test_a_run_with_a_bend_is_two_straights_and_an_elbow(self):
        items = detail.parts(tray())
        self.assertEqual([p["part"] for p in items], ["straight", "straight", "elbow"])
        self.assertEqual([p["length_m"] for p in of(items, "straight")], [9.7, 4.7])                # each cut by the leg of the elbow: one width (0.3 m)
        elbow = of(items, "elbow")[0]
        self.assertEqual((elbow["angle_deg"], elbow["size"], elbow["layer"]), (90.0, "300x100", "ELEC-BANDEJA"))
        self.assertEqual(elbow["path"], [[9.7, 0.0, 2.6], [10.0, 0.0, 2.6], [10.0, 0.3, 2.6]])

    def test_the_elbow_closes_the_corner_the_two_stretches_left_open(self):
        elbow = of(detail.parts(tray()), "elbow")[0]
        xs = [v[0] for v in elbow["mesh"]["vertices"]]
        ys = [v[1] for v in elbow["mesh"]["vertices"]]
        self.assertEqual((min(xs), max(xs), min(ys), max(ys)), (9.7, 10.15, -0.15, 0.3))             # out to the outer corner of the bend
        self.assertTrue(all(0 <= i < len(elbow["mesh"]["vertices"]) for f in elbow["mesh"]["faces"] for i in f))

    def test_the_straights_of_a_tray_layer_are_ladders_when_asked_and_boxes_otherwise(self):
        box = detail.parts(tray())
        layer = of(box, "straight")[0]["layer"]
        ladder = detail.parts(tray(), {"ladder_trays": {"layers": [layer]}})
        self.assertGreater(len(of(ladder, "straight")[0]["mesh"]["faces"]), len(of(box, "straight")[0]["mesh"]["faces"]))
        self.assertEqual(len(of(detail.parts(tray(), {"ladder_trays": {"layers": ["OTHER"]}}), "straight")[0]["mesh"]["faces"]), len(of(box, "straight")[0]["mesh"]["faces"]))
        with self.assertRaises(core.PlanError):
            detail.parts(tray(), {"ladder_trays": {"layers": []}})

    def test_the_elbows_of_a_tray_layer_follow_the_kind_of_tray(self):
        box = detail.parts(tray())
        layer = of(box, "elbow")[0]["layer"]
        for kind in ("escalera", "perforada", "ciega", "alambre"):
            parts = detail.parts(tray(), {"ladder_trays": {"layers": [layer], "kinds": {layer: kind}}})
            self.assertGreater(len(of(parts, "elbow")[0]["mesh"]["faces"]), 0)
        with self.assertRaises(core.PlanError):
            detail.parts(tray(), {"ladder_trays": {"layers": [layer], "kinds": {layer: "nope"}}})

    def test_a_straight_run_has_no_fitting(self):
        items = detail.parts(solids(S.CONDUIT))
        self.assertEqual([(p["part"], p["length_m"], p["size"]) for p in items], [("straight", 10.0, "D50")])

    def test_two_bends_closer_than_two_legs_share_the_stretch(self):
        z = S.line("z", "BN", [0, 0], [50, 0], [50, -4], [100, -4])                # a 0.4 m offset: less than two legs of 0.3 m
        items = detail.parts(solids(z))
        self.assertEqual(len(of(items, "elbow")), 2)
        self.assertEqual(sorted(p["length_m"] for p in of(items, "straight")), [4.8, 4.8])           # each elbow takes half of the 0.4 m between them (0.2 m, not its 0.3 m leg): the middle stretch is all elbow

    def test_the_tee_of_a_tray_layer_is_a_tray_of_its_kind(self):
        branch = S.line("b", "BN", [50, 0], [50, -30])
        layer = of(detail.parts(solids(S.TRAY, branch)), "tee")[0]["layer"]
        box = of(detail.parts(solids(S.TRAY, branch)), "tee")[0]["mesh"]["faces"]
        ladder = of(detail.parts(solids(S.TRAY, branch), {"ladder_trays": {"layers": [layer]}}), "tee")[0]["mesh"]["faces"]
        self.assertGreater(len(ladder), len(box))

    def test_a_run_that_ends_on_another_makes_a_tee(self):
        branch = S.line("b", "BN", [50, 0], [50, -30])                                 # leaves the first stretch of the tray at its middle
        items = detail.parts(solids(S.TRAY, branch))
        tee = of(items, "tee")
        self.assertEqual(len(tee), 1)
        self.assertEqual((tee[0]["run"], tee[0]["branch"], tee[0]["size"], tee[0]["branch_size"], tee[0]["at"]), ("l1", "b", "300x100", "300x100", [5.0, 0.0, 2.6]))
        self.assertEqual(tee[0]["path"], [[4.55, 0.0, 2.6], [5.45, 0.0, 2.6]])        # the branch is 0.3 m wide, plus a leg each way

    def test_two_runs_of_different_size_end_to_end_make_a_reducer(self):
        wide = S.line("w", "BN", [0, 0], [50, 0])
        narrow = S.line("n", "BN", [50, 0], [100, 0], ancho_m=0.15)
        red = of(detail.parts(solids(wide, narrow)), "reducer")
        self.assertEqual([(r["run"], r["to"], r["size"], r["to_size"]) for r in red], [("w", "n", "300x100", "150x100")])
        ys = sorted({abs(v[1]) for v in red[0]["mesh"]["vertices"]})
        self.assertEqual(ys, [0.0, 0.075, 0.15])                                      # from 300 to 150 mm wide

    def test_runs_of_another_discipline_do_not_join(self):
        pipe = solid.solids(S.sheet(discipline="sanitaria_cloacas", lines=[S.line("p", "CC", [50, 0], [50, -30], z_m=2.6)]), "S1")
        self.assertEqual(of(detail.parts(tray() + pipe), "tee"), [])

    def test_equipment_is_not_a_part(self):
        self.assertEqual(detail.parts(solids(nodes=[S.BOARD])), [])


class Supports(unittest.TestCase):
    def test_a_tray_hangs_from_trapezes_no_further_apart_than_the_spacing(self):
        sup = detail.supports(tray(), SPEC)
        self.assertEqual((len(sup), {s["support"] for s in sup}), (8, {"trapeze"}))                  # 10 m: 5 of them 2 m apart; 5 m: 3
        self.assertEqual([s["at"] for s in sup[:2]], [[1.0, 0.0, 2.6], [3.0, 0.0, 2.6]])
        zs = [v[2] for v in sup[0]["mesh"]["vertices"]]
        self.assertEqual(max(zs), 3.0)                                                 # the rods reach the underside of the slab
        self.assertLess(min(zs), 2.55)                                                 # the channel is under the tray
        self.assertEqual(sup[0]["rod_m"], round(2 * (3.0 - (2.55 - 0.0205)), 3))

    def test_a_pipe_hangs_from_a_rod(self):
        sup = detail.supports(solids(S.CONDUIT), SPEC)
        self.assertEqual((len(sup), sup[0]["support"], sup[0]["rod_m"]), (5, "rod", 0.375))          # from the top of the conduit (2.625 m) to the slab

    def test_the_spacing_and_the_slab_are_inputs(self):
        for bad in ({}, {"spacing_m": 2.0}, {"slab_underside_m": {"L0": 3.0}}, {"spacing_m": 0, "slab_underside_m": {"L0": 3.0}}):
            with self.assertRaises(core.PlanError):
                detail.supports(tray(), bad)

    def test_a_run_with_no_slab_over_it_gets_none(self):
        self.assertEqual(detail.supports(tray(), {"spacing_m": 2.0, "slab_underside_m": {"L1": 6.0}}), [])
        self.assertEqual(detail.supports(tray(), {"spacing_m": 2.0, "slab_underside_m": {"L0": 2.5}}), [])     # a slab under the tray is not what it hangs from
        buried = solid.solids(S.sheet(discipline="sanitaria_cloacas", lines=[S.line("p", "CC", [0, 0], [100, 0])]), "S1")
        self.assertEqual(len(detail.supports(buried, SPEC)), 5)                         # under the slab it hangs like any other; the person leaves buried runs out


class TakeOff(unittest.TestCase):
    def test_lengths_fittings_and_supports_add_up(self):
        items = solids(S.TRAY, S.CONDUIT, S.line("b", "BN", [50, 0], [50, -30]))
        t = detail.takeoff(detail.parts(items) + detail.supports(items, SPEC))
        tray_row = next(r for r in t["straights"] if r["size"] == "300x100")
        self.assertEqual((tray_row["count"], tray_row["length_m"]), (3, 17.4))         # 9.7 + 4.7 + 3.0
        self.assertEqual(next(r for r in t["straights"] if r["size"] == "D50")["length_m"], 10.0)
        self.assertEqual(sorted((r["type"], r["count"]) for r in t["fittings"]), [("elbow", 1), ("tee", 1)])
        self.assertEqual({r["type"]: r["count"] for r in t["supports"]}, {"rod": 5, "trapeze": 10})
        self.assertEqual(t, detail.takeoff(detail.parts(items) + detail.supports(items, SPEC)))      # the same model gives the same list


class Scene(unittest.TestCase):
    def test_the_fabrication_scene_has_the_parts_the_supports_and_the_equipment(self):
        items = solids(S.TRAY, nodes=[S.BOARD])
        sc = detail.scene(items, hangers=SPEC)
        kinds = [s.get("part", "equipment") for s in sc["solids"]]
        self.assertEqual((kinds.count("equipment"), kinds.count("straight"), kinds.count("elbow"), kinds.count("support")), (1, 2, 1, 8))
        scene3d.check(sc)

    def test_a_section_shows_the_support_and_writes_size_levels_and_dimensions(self):
        import ezdxf
        items = solids(S.TRAY, S.CONDUIT)
        sec = scene3d.cut(detail.scene(items, hangers=SPEC), "x", 1.0, "+")              # through the first trapeze of the tray and the first rod of the conduit
        tray_cut = next(c for c in sec["cut"] if c["layer"] == "ELEC-BANDEJA")
        self.assertEqual((tray_cut["size"], tray_cut["bottom_m"], tray_cut["top_m"]), ("300x100", 2.55, 2.65))
        self.assertEqual(next(c for c in sec["cut"] if c["layer"] == "ELEC-CANAL")["size"], "D50")
        self.assertTrue([c for c in sec["cut"] if c["layer"] == detail.SUPPORT_LAYER])
        self.assertEqual(scene3d.dimension_points({"cut": [c for c in sec["cut"] if c["layer"] != detail.SUPPORT_LAYER]}), [0.0, 2.0])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "detail.dxf"
            n = scene3d.write_section_dxf(sec, path)
            msp = list(ezdxf.readfile(str(path)).modelspace())
            texts = [e.dxf.text for e in msp if e.dxftype() == "TEXT"]
            self.assertIn("BN-001 300x100 +2.60 (BOT +2.55)", texts)
            self.assertEqual(sum(1 for e in msp if e.dxftype() == "DIMENSION"), n["dimensions"])
            self.assertGreaterEqual(n["dimensions"], 1)


if __name__ == "__main__":
    unittest.main()
