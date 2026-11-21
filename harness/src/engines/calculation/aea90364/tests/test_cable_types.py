"""The cable type of a circuit is decided before any section: material, insulation, cores, method."""
import unittest

from epc_aea90364 import cable_types as CT


class CableType(unittest.TestCase):
    def test_row_wins(self):
        t = CT.cable_type({"MATERIAL": "al", "AISLACION": "pvc", "METODO": "C"}, None, "cu", "xlpe")
        self.assertEqual(t, {"material": "al", "insulation": "pvc", "method": "C", "cores": "multi"})

    def test_defaults_and_xlpe_method(self):
        t = CT.cable_type({}, None, "cu", "xlpe")
        self.assertEqual((t["material"], t["insulation"], t["method"]), ("cu", "xlpe", CT.XLPE_DEFAULT_METHOD))

    def test_pvc_has_no_forced_method(self):
        self.assertIsNone(CT.cable_type({}, None, "cu", "pvc")["method"])

    def test_single_core(self):
        self.assertEqual(CT.cable_type({"CABLE_TIPO": "Unifilar"}, None, "cu", "pvc")["cores"], "single")

    def test_estimate_is_in_tag_order_and_has_no_section(self):
        out = CT.estimate({"B": {}, "A": {}}, {}, "cu", "pvc")
        self.assertEqual(list(out), ["A", "B"])
        self.assertNotIn("section", out["A"])


if __name__ == "__main__":
    unittest.main()
