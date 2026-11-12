"""D14: simultaneity on the current of parent circuits; terminal circuits at full load; the type of installation is always explicit."""
import unittest

from epc_aea90364 import aea_demand as DEM
from epc_aea90364 import aea_pipeline as P
from epc_aea90364 import board_feeders as BF
from epc_aea90364 import board_memo
from epc_aea90364 import simultaneity as SIM

BOARD = {"TENSION_V": 380, "ICC_KA": 10, "FP_DEFAULT": 0.85}
DWELLING_MEDIO = {"installation_type": "dwelling", "electrification_grade": "medio"}


def rows(n=3, parent_load=None):
    """A feeder (no load of its own unless given) with n terminal circuits of 10 A."""
    feeder = {"TAG": "F-01", "DESCRIPCION": "ALIMENTADOR TD", "TOPOLOGY": "single", "FASE": "3F", "LONGITUD_m": 20, "KIND": "mccb"}
    if parent_load is not None:
        feeder.update(CARGA=parent_load, UNIDAD_CARGA="A")
    kids = [{"TAG": f"T-{i:02d}", "DESCRIPCION": "Tomas", "CARGA": 10, "UNIDAD_CARGA": "A", "PARENT_TAG": "F-01", "TOPOLOGY": "single", "FASE": "3F", "LONGITUD_m": 10}
            for i in range(1, n + 1)]
    return [feeder] + kids


def run(criterios=None, n=3, parent_load=None):
    det = {}
    datos, avisos = P.calculate(BOARD, rows(n, parent_load), criterios=criterios, detalle=det)
    return datos, det, avisos


class TestDwelling(unittest.TestCase):
    def test_table_771_9_II_by_grade(self):
        for grade in ("minimo", "medio", "elevado", "superior"):
            datos, det, _ = run({"installation_type": "dwelling", "electrification_grade": grade})
            f = DEM.coef_simultaneity_771(grade)                                  # the factor comes from the engine table, never typed here
            self.assertAlmostEqual(datos["F-01"]["Ib"], 30 * f, places=3)
            self.assertEqual(det["F-01"]["simultaneity"]["table"], "771.9.II")
            self.assertEqual(det["F-01"]["simultaneity"]["factor"], f)

    def test_n_circuits_do_not_change_the_dwelling_factor(self):
        f = DEM.coef_simultaneity_771("medio")
        for n in (2, 5, 8):
            datos, _, _ = run(DWELLING_MEDIO, n=n)
            self.assertAlmostEqual(datos["F-01"]["Ib"], 10 * n * f, places=3)

    def test_terminal_circuits_stay_at_full_load(self):
        datos, det, _ = run({"installation_type": "dwelling", "electrification_grade": "superior"})
        for tag in ("T-01", "T-02", "T-03"):
            self.assertEqual(datos[tag]["Ib"], 10)
            self.assertNotIn("simultaneity", det[tag])

    def test_dwelling_without_grade_keeps_the_plain_sum_and_warns(self):
        datos, det, avisos = run({"installation_type": "dwelling"})
        self.assertEqual(datos["F-01"]["Ib"], 30)
        self.assertNotIn("simultaneity", det["F-01"])
        self.assertTrue(any("electrification_grade" in a for a in avisos))

    def test_invalid_grade_is_refused(self):
        with self.assertRaises(ValueError):
            run({"installation_type": "dwelling", "electrification_grade": "huge"})


class TestOtherInstallations(unittest.TestCase):
    def test_explicit_factor_of_the_project(self):
        datos, det, _ = run({"installation_type": "office", "simultaneity_factor": 0.65})
        self.assertAlmostEqual(datos["F-01"]["Ib"], 30 * 0.65, places=3)
        self.assertEqual(det["F-01"]["simultaneity"]["table"], "project")

    def test_default_is_table_771_9_III_by_units_and_grade(self):
        for n, grade in ((3, "medio"), (6, "elevado"), (2, "minimo")):
            datos, det, _ = run({"installation_type": "shop", "electrification_grade": grade}, n=n)
            f = DEM.coef_simultaneidad_conjunto(n, grade)
            self.assertAlmostEqual(datos["F-01"]["Ib"], 10 * n * f, places=3)
            self.assertEqual(det["F-01"]["simultaneity"]["table"], "771.9.III")
            self.assertEqual(det["F-01"]["simultaneity"]["units"], n)

    def test_without_factor_and_without_grade_keeps_the_plain_sum_and_warns(self):
        datos, det, avisos = run({"installation_type": "industry"})
        self.assertEqual(datos["F-01"]["Ib"], 30)
        self.assertNotIn("simultaneity", det["F-01"])
        self.assertTrue(any("771.9.III" in a for a in avisos))

    def test_factor_out_of_range_is_refused(self):
        for bad in (0, 1.2, -0.5):
            with self.assertRaises(ValueError):
                run({"installation_type": "office", "simultaneity_factor": bad})


class TestNoTypeNoChange(unittest.TestCase):
    def test_missing_type_is_the_plain_sum_without_warning(self):
        datos, det, avisos = run({"electrification_grade": "superior", "simultaneity_factor": 0.5})
        self.assertEqual(datos["F-01"]["Ib"], 30)
        self.assertNotIn("simultaneity", det["F-01"])
        self.assertFalse(any("installation_type" in a for a in avisos))

    def test_no_criteria_is_the_plain_sum(self):
        datos, _, _ = run(None)
        self.assertEqual(datos["F-01"]["Ib"], 30)

    def test_unknown_type_is_never_guessed(self):
        datos, det, avisos = run({"installation_type": "spaceship", "electrification_grade": "medio", "simultaneity_factor": 0.5})
        self.assertEqual(datos["F-01"]["Ib"], 30)
        self.assertNotIn("simultaneity", det["F-01"])
        self.assertTrue(any("spaceship" in a for a in avisos))

    def test_parent_with_its_own_load_is_not_touched(self):
        datos, det, _ = run({"installation_type": "dwelling", "electrification_grade": "superior"}, parent_load=50)
        self.assertEqual(datos["F-01"]["Ib"], 50)
        self.assertNotIn("simultaneity", det["F-01"])

    def test_a_parent_with_one_child_has_nothing_to_be_simultaneous_with(self):
        datos, det, _ = run({"installation_type": "dwelling", "electrification_grade": "superior"}, n=1)
        self.assertEqual(datos["F-01"]["Ib"], 10)
        self.assertNotIn("simultaneity", det["F-01"])


class TestVocabulary(unittest.TestCase):
    def test_controlled_values(self):
        self.assertEqual(SIM.installation_kind(" Dwelling "), "dwelling")
        self.assertEqual(SIM.installation_kind("office"), "other")
        self.assertIsNone(SIM.installation_kind("casa"))
        self.assertIsNone(SIM.installation_kind(None))


class TestHeadAndMemo(unittest.TestCase):
    def test_incoming_supply_head_gets_the_factor(self):
        data = {"A": {"Ib": 10.0}, "B": {"Ib": 20.0}}
        det = {"A": {}, "B": {}}
        value, rec = BF.head(data, det, DWELLING_MEDIO)
        self.assertAlmostEqual(value, 30 * DEM.coef_simultaneity_771("medio"), places=3)
        self.assertEqual(rec["table"], "771.9.II")
        self.assertEqual(BF.head_current(data, det), 30.0)                       # no criteria: the plain sum, as before

    def test_head_with_one_root_is_not_reduced_twice_by_the_same_load(self):
        datos, det, _ = run(DWELLING_MEDIO)
        value, rec = BF.head(datos, det, DWELLING_MEDIO)
        self.assertAlmostEqual(value, datos["F-01"]["Ib"], places=3)
        self.assertIsNone(rec)

    def test_sentence_is_generated_from_the_values(self):
        rec = {"F-01": {"factor": 0.9, "table": "771.9.II", "grade": "medio", "units": 3, "installation_type": "dwelling", "plain_a": 30.0}}
        text = SIM.describe(rec)
        self.assertIn("F-01", text)
        self.assertIn("Table 771.9.II", text)
        self.assertIn("factor 0.9", text)
        self.assertEqual(SIM.describe({}), "")

    def _memo(self, crit):
        kids = rows(3)
        det = {}
        datos, _ = P.calculate(BOARD, kids, criterios=crit, detalle=det)
        board = {"name": "TD", "voltage_v": 380, "system": "TN-S", "icc_ka": 10, "fp_default": 0.85}
        circuits = [{"tag": c["TAG"], "parent_tag": c.get("PARENT_TAG") or "", "description": c["DESCRIPCION"]} for c in kids]
        limits = {"seccional": 1.0, "terminal": 3.0, "motor": 5.0}
        return board_memo.build(board, circuits, datos, det, limits, {"material": "cu", "aislacion": "pvc"}, 30.0)

    def test_memo_states_simultaneity_when_applied(self):
        f = DEM.coef_simultaneity_771("medio")
        notes = [s for s in self._memo(DWELLING_MEDIO)["supuestos"] if "Simultaneity (D14)" in s]
        self.assertEqual(len(notes), 1)
        self.assertIn("Table 771.9.II", notes[0])
        self.assertIn(f"factor {f:g}", notes[0])

    def test_memo_is_silent_when_not_applied(self):
        self.assertFalse(any("Simultaneity" in s for s in self._memo(None)["supuestos"]))


if __name__ == "__main__":
    unittest.main()
