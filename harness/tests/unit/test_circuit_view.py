"""One view of the circuits: the cable list, terminal list and BOQ inputs derive from it."""
import unittest

from disciplines.electrical_lv.stages import output_stages as O
from disciplines.electrical_lv.stages.cable_list import cable_rows
from disciplines.electrical_lv.stages.circuit_view import circuit_view

CH = {"form": {"board": {"name": "TS1"}},
      "calc": {"datos": {"C1": {"S": 2.5, "In": 16, "dU": 1.2, "icu": 6, "disp": "MCB 2P 16 A"}},
               "detalle": {"C1": {"fases": "1F", "material": "cu", "aislacion": "pvc", "metodo": "B1", "neutro_mm2": 2.5, "pe_mm2": 2.5, "largo_m": 20, "ib_a": 12.0,
                                  "cumple": True, "descripcion": "Lights", "padre": None, "cadena": [{"short": "MCB 2P 16 A", "poles": 2}]}}}}


class CircuitView(unittest.TestCase):
    def test_one_row_per_circuit_with_every_field(self):
        v = circuit_view(CH)["C1"]
        self.assertEqual((v["s_mm2"], v["in_a"], v["icu_ka"], v["poles"], v["device_kind"]), (2.5, 16, 6, 2, "MCB 2P 16 A"))

    def test_the_documents_read_the_same_values(self):
        row = cable_rows(CH, [])[0]
        boq = O.boq_circuits(CH)[0]
        term = O.terminal_circuits(CH)[0]
        self.assertEqual((row["s_mm2"], boq["s_mm2"], term["s_mm2"]), (2.5, 2.5, 2.5))
        self.assertEqual((row["from"], boq["breaking_capacity_ka"], term["device"]), ("TS1", 6, "MCB 2P 16 A"))


if __name__ == "__main__":
    unittest.main()
