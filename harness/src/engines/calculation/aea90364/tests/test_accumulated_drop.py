"""MIG-36g (decision D17): the voltage-drop limit of each type is compared with the drop ACCUMULATED from the origin of the installation.

Lighting 3 %, receptacles 3 %, sectional lines 1 % (the sectional chain), motors in steady state 5 %; motor starting is a separate check (15 %). The 2 % recommended for
terminal circuits is only an observation and never decides. Examples of the decision: sectional 1 % + lighting 2 % = 3 % passes; sectional 1 % + lighting 3 % = 4 % fails;
sectional 1 % + motor 4 % = 5 % passes.
"""
import os
import sys
import unittest

from epc_aea90364 import aea_motor as MO
from epc_aea90364 import aea_pipeline as P
from epc_aea90364 import aea_voltage_drop as VD

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import characterization_memo as C   # noqa: E402

BOARD = {"TENSION_V": 380, "ICC_KA": 25, "FP_DEFAULT": 0.85}
LIGHT = {"TAG": "L-01", "DESCRIPCION": "ILUMINACION", "CARGA": 2, "UNIDAD_CARGA": "kW", "TOPOLOGY": "single", "FASE": "1F", "FP": 0.9}


def feeder(length_m):
    return {"TAG": "F-01", "DESCRIPCION": "ALIMENTADOR", "CARGA": 60, "UNIDAD_CARGA": "A", "TOPOLOGY": "single", "FASE": "3F", "LONGITUD_m": length_m, "KIND": "mccb"}


def light(length_m, parent="F-01"):
    return dict(LIGHT, LONGITUD_m=length_m, **({"PARENT_TAG": parent} if parent else {}))


def motor(length_m):
    return {"TAG": "M-01", "DESCRIPCION": "BOMBA", "PARENT_TAG": "F-01", "CARGA": 11, "UNIDAD_CARGA": "kW", "TOPOLOGY": "dol_ol", "FASE": "3F", "LONGITUD_m": length_m,
            "FP": 0.85, "RENDIMIENTO": 0.9}


def run(circuits, criterios=None):
    det = {}
    datos, avisos = P.calculate(BOARD, circuits, criterios=criterios, detalle=det)
    return datos, det, avisos


class TheRuleOfTheDecision(unittest.TestCase):
    def test_the_three_examples(self):
        light_lim, motor_lim = VD.limite_caida_pct("iluminacion"), VD.limite_caida_pct("motor_regimen")
        sect = VD.limite_caida_pct("seccional")
        self.assertTrue(P.within_accumulated_limit(sect, 2.0, light_lim))        # 1 % + 2 % = 3 % passes
        self.assertFalse(P.within_accumulated_limit(sect, 3.0, light_lim))       # 1 % + 3 % = 4 % fails
        self.assertTrue(P.within_accumulated_limit(sect, 4.0, motor_lim))        # 1 % + 4 % = 5 % passes

    def test_the_limits_are_the_data_of_the_decision(self):
        self.assertEqual([VD.limite_caida_pct(k) for k in ("iluminacion", "tomacorrientes", "seccional", "motor_regimen", "motor_arranque")], [3.0, 3.0, 1.0, 5.0, 15.0])


class TerminalCircuitsAreSizedByTheAccumulatedDrop(unittest.TestCase):
    def test_a_lighting_circuit_under_a_feeder_is_enlarged_until_the_accumulated_drop_meets_3_percent(self):
        alone, det_alone, _ = run([light(80, parent="")])
        under, det, _ = run([feeder(20), light(80)])
        self.assertLessEqual(det_alone["L-01"]["du_propia_pct"], 3.0)             # on its own the old and the new rule choose the same section
        self.assertGreater(det_alone["L-01"]["du_propia_pct"] + det["F-01"]["du_acum_pct"], 3.0)   # the section it would have had does not meet 3 % accumulated
        self.assertGreater(under["L-01"]["S"], alone["L-01"]["S"])
        d = det["L-01"]
        self.assertLessEqual(d["du_acum_pct"], d["limite_pct"])
        self.assertAlmostEqual(d["du_acum_pct"], det["F-01"]["du_acum_pct"] + d["du_propia_pct"], places=2)
        self.assertTrue(d["cumple"])

    def test_the_motor_in_steady_state_is_held_to_5_percent_accumulated(self):
        near, det_near, _ = run([feeder(20), motor(150)])
        far, det, _ = run([feeder(40), motor(150)])
        d = det["M-01"]
        self.assertGreater(far["M-01"]["S"], near["M-01"]["S"])                    # the longer the feeder, the less is left for the motor
        self.assertEqual(d["limite_pct"], VD.limite_caida_pct("motor_regimen"))
        self.assertLessEqual(d["du_acum_pct"], 5.0)
        self.assertGreater(det["F-01"]["du_acum_pct"] + det_near["M-01"]["du_propia_pct"], 5.0)   # the section that was enough under the shorter feeder is not any more
        self.assertTrue(d["cumple"])

    def test_detail_reports_limit_own_accumulated_and_a_verdict_from_the_accumulated_rule(self):
        _, det, _ = run([feeder(40), light(80), motor(150)])
        for tag, d in det.items():
            with self.subTest(tag=tag):
                for key in ("limite_pct", "du_propia_pct", "du_acum_pct", "cumple"):
                    self.assertIn(key, d)
                self.assertEqual(d["cumple"], d["du_acum_pct"] <= d["limite_pct"] and d["iz_a"] is not None)

    def test_the_two_percent_observation_never_decides(self):
        _, det, _ = run([light(80, parent="")])
        d = det["L-01"]
        self.assertGreater(d["du_propia_pct"], 2.0)                               # above the 2 % recommended for terminal circuits
        self.assertTrue(d["cumple"])                                              # and still compliant: only the 3 % of the type decides


class SectionalChain(unittest.TestCase):
    def test_the_sectional_chain_is_held_to_1_percent(self):
        sub = {"TAG": "F-02", "DESCRIPCION": "SUBTABLERO", "PARENT_TAG": "F-01", "CARGA": 30, "UNIDAD_CARGA": "A", "TOPOLOGY": "single", "FASE": "3F", "LONGITUD_m": 30, "KIND": "mccb"}
        leaf = dict(light(20, parent="F-02"), TAG="L-02")
        _, det, _ = run([feeder(40), sub, leaf])
        self.assertEqual(det["F-02"]["tipo"], "seccional")
        self.assertAlmostEqual(det["F-02"]["du_acum_pct"], det["F-01"]["du_acum_pct"] + det["F-02"]["du_propia_pct"], places=2)
        self.assertLessEqual(det["F-02"]["du_acum_pct"], VD.limite_caida_pct("seccional"))
        self.assertTrue(det["F-02"]["cumple"])
        self.assertLessEqual(det["L-02"]["du_acum_pct"], 3.0)


class MotorStartingStaysSeparate(unittest.TestCase):
    def test_starting_limit_is_15_percent_and_not_part_of_the_steady_state_search(self):
        self.assertEqual(MO.limite_arranque_pct(), 15.0)
        out = MO.caida_arranque(20.0, "dol_ol", 50.0, 16.0)
        self.assertEqual(out["limite_pct"], 15.0)
        self.assertEqual(out["cumple"], out["caida_pct"] <= 15.0 + 1e-9)


class MemoDescribesTheAccumulatedRule(unittest.TestCase):
    def test_memo_text_is_generated_from_the_limits(self):
        out = C.run("groups_tns")
        md = out["mc_md"]
        self.assertIn("acumulada desde el origen", md)
        lim = out["memo"]["criteria"]["limits_pct"]
        for key in ("seccional", "terminal", "motor"):
            self.assertIn(f"{lim[key]:.1f}".replace(".", ",") + " %", md)
        self.assertIn("el arranque de motores se verifica aparte", md)


if __name__ == "__main__":
    unittest.main()
