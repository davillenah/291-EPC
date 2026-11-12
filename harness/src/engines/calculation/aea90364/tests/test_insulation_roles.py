"""D6: insulation by the role of the circuit; no global default for the roles it covers."""
import unittest

from epc_aea90364 import aea_pipeline as P
from epc_aea90364 import insulation_roles as IR

BOARD = {"TENSION_V": 380, "ICC_KA": 25, "FP_DEFAULT": 0.85}


def rows(**extra):
    base = [
        {"TAG": "C-01", "DESCRIPCION": "ALIMENTADOR TD-1", "CARGA": 100, "UNIDAD_CARGA": "A", "TOPOLOGY": "single", "FASE": "3F", "LONGITUD_m": 60, "KIND": "mccb"},
        {"TAG": "ACOMETIDA-1", "DESCRIPCION": "ACOMETIDA - TABLERO TG", "CARGA": 100, "UNIDAD_CARGA": "A", "TOPOLOGY": "single", "FASE": "3F", "LONGITUD_m": 30},
        {"TAG": "S-01", "DESCRIPCION": "LINEA SECCIONAL", "CARGA": 40, "UNIDAD_CARGA": "A", "TOPOLOGY": "single", "FASE": "3F", "LONGITUD_m": 25, "KIND": "mccb"},
        {"TAG": "S-01-A", "DESCRIPCION": "Tomas", "CARGA": 1.5, "UNIDAD_CARGA": "kW", "PARENT_TAG": "S-01", "TOPOLOGY": "single", "FASE": "1F", "LONGITUD_m": 12, "FP": 0.9},
        {"TAG": "L-01", "DESCRIPCION": "ILUMINACION NAVE", "CARGA": 2, "UNIDAD_CARGA": "kW", "TOPOLOGY": "single", "FASE": "1F", "LONGITUD_m": 20, "FP": 0.9},
        {"TAG": "T-01", "DESCRIPCION": "TOMAS OFICINA", "CARGA": 2, "UNIDAD_CARGA": "kW", "TOPOLOGY": "single", "FASE": "1F", "LONGITUD_m": 15, "FP": 0.9},
        {"TAG": "M-01", "DESCRIPCION": "BOMBA", "CARGA": 15, "UNIDAD_CARGA": "kW", "TOPOLOGY": "dol_ol", "FASE": "3F", "LONGITUD_m": 80, "FP": 0.85, "RENDIMIENTO": 0.9},
    ]
    return [dict(r, **extra.get(r["TAG"], {})) for r in base]


def run(criterios=None, **extra):
    det = {}
    datos, _ = P.calculate(BOARD, rows(**extra), criterios=criterios, detalle=det)
    return datos, det


class TestRoleTable(unittest.TestCase):
    def test_roles_covered_by_d6(self):
        self.assertEqual([IR.insulation_for_role(r) for r in ("seccional", "iluminacion", "tomacorrientes")], ["xlpe", "pvc", "pvc"])

    def test_uncovered_roles_have_no_value(self):
        self.assertIsNone(IR.insulation_for_role("motor"))
        self.assertIsNone(IR.insulation_for_role("unknown"))


class TestPipelineUsesRole(unittest.TestCase):
    def test_roles_in_the_pipeline_without_criteria(self):
        _, det = run()
        got = {t: det[t]["aislacion"] for t in det}
        self.assertEqual((got["C-01"], got["ACOMETIDA-1"], got["S-01"]), ("xlpe", "xlpe", "xlpe"))
        self.assertEqual((got["L-01"], got["T-01"], got["S-01-A"]), ("pvc", "pvc", "pvc"))

    def test_criteria_do_not_override_a_covered_role(self):
        _, det = run({"insulation": "XLPE"})
        self.assertEqual((det["L-01"]["aislacion"], det["T-01"]["aislacion"]), ("pvc", "pvc"))
        _, det = run({"insulation": "PVC"})
        self.assertEqual(det["C-01"]["aislacion"], "xlpe")

    def test_uncovered_role_keeps_criteria_or_current_default(self):
        self.assertEqual(run()[1]["M-01"]["aislacion"], "pvc")                       # today's engine fallback
        self.assertEqual(run({"insulation": "XLPE"})[1]["M-01"]["aislacion"], "xlpe")

    def test_special_terminal_circuit_states_its_own(self):
        _, det = run(**{"L-01": {"AISLACION": "xlpe"}, "C-01": {"AISLACION": "pvc"}})
        self.assertEqual((det["L-01"]["aislacion"], det["C-01"]["aislacion"]), ("xlpe", "pvc"))

    def test_iz_uses_the_role_insulation(self):
        from epc_aea90364 import aea_ampacity as AMP
        _, det = run()
        s = det["C-01"]["seccion_min_mm2"] or 25
        xl = AMP.iz(AMP.parametros({"AISLACION": "xlpe", "METODO": "B2"}), s, 3)
        pv = AMP.iz(AMP.parametros({"AISLACION": "pvc", "METODO": "B2"}), s, 3)
        self.assertNotEqual(xl, pv)
        self.assertEqual(det["C-01"]["aislacion"], "xlpe")
        _, forced = run(**{"C-01": {"AISLACION": "pvc"}})
        self.assertEqual(forced["C-01"]["aislacion"], "pvc")


if __name__ == "__main__":
    unittest.main()
