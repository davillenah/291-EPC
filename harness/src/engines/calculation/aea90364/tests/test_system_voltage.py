"""MIG-36f (decision D16): one electrical system per project and one U0 for every safety check.

230/400 V -> U0 = 230 V; 220/380 V -> U0 = 220 V. The mapping is data (data/system_voltages.json); `system_voltage.system_u0` is the only function that turns a line
voltage into U0. Pinned here: the mapping, the TN / IT checks, the minimum Icc, the memo (Zs max and its sentence), the optional two-level keys (defaults change nothing) and a
scan of the engine for stray nominal-voltage literals.
"""
import ast
import copy
import json
import math
import os
import engine_sources
import sys
import unittest
from unittest import mock

from epc_aea90364 import aea_earthing as EA
from epc_aea90364 import aea_pipeline as P
from epc_aea90364 import aea_protection as PR
from epc_aea90364 import system_voltage as SV

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import characterization_memo as C   # noqa: E402

SRC = os.path.dirname(os.path.abspath(SV.__file__))
DATA = str(SV.norm_data.path("system_voltages.json"))
ROW = {"TAG": "C-01", "DESCRIPCION": "TOMAS", "CARGA": 2.2, "UNIDAD_CARGA": "kW", "FASE": "1F", "FP": 0.9, "LONGITUD_m": 20}


class SystemMapping(unittest.TestCase):
    def test_the_two_systems_of_d16(self):
        self.assertEqual(SV.system_u0(400), 230.0)
        self.assertEqual(SV.system_u0(380.0), 220.0)

    def test_the_mapping_is_data(self):
        with open(DATA, encoding="utf-8") as fh:
            rows = json.load(fh)["systems"]
        self.assertEqual({r["un_v"]: r["u0_v"] for r in rows}, {400.0: 230.0, 380.0: 220.0})
        self.assertEqual(SV.systems(), {400.0: 230.0, 380.0: 220.0})

    def test_a_voltage_that_is_not_a_project_system_is_refused(self):
        for bad in (415, 230, 0, None, "x"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                SV.system_u0(bad)

    def test_the_default_system_is_the_engine_default(self):
        self.assertEqual(SV.default_un_v(), 380.0)
        self.assertEqual(SV.board_u0({}), 220.0)

    def test_board_keys_in_both_spellings(self):
        self.assertEqual(SV.board_u0({"TENSION_V": 400}), 230.0)
        self.assertEqual(SV.board_u0({"voltage_v": 400.0}), 230.0)
        self.assertEqual(SV.board_u0({"voltage_v": None}), 220.0)


class ProtectionChecksUseTheProjectSystem(unittest.TestCase):
    def test_tn_with_a_380_v_board_uses_220(self):
        r = PR.verifica_tn(1.0, 160.0, un_v=380.0)
        self.assertAlmostEqual(r["limite_v"], 0.95 * 220.0)
        self.assertEqual(r["zs_max_ohm"], EA.zs_maxima(220.0, 160.0))

    def test_tn_with_a_400_v_board_uses_230(self):
        self.assertAlmostEqual(PR.verifica_tn(1.0, 160.0, un_v=400.0)["limite_v"], 0.95 * 230.0)

    def test_tn_default_is_the_default_system(self):
        self.assertEqual(PR.verifica_tn(1.0, 160.0), PR.verifica_tn(1.0, 160.0, un_v=380.0))

    def test_an_explicit_u0_still_wins(self):
        self.assertAlmostEqual(PR.verifica_tn(1.0, 160.0, u0_v=230.0)["limite_v"], 0.95 * 230.0)

    def test_it_second_fault_limits(self):
        self.assertEqual(PR.verifica_it_segunda_falla(0.5, 300)["limite_v"], 380.0)
        self.assertEqual(PR.verifica_it_segunda_falla(0.5, 300, neutro_distribuido=True)["limite_v"], 220.0)
        self.assertEqual(PR.verifica_it_segunda_falla(0.5, 300, u_v=400.0)["limite_v"], 400.0)
        self.assertEqual(PR.verifica_it_segunda_falla(0.5, 300, u_v=400.0, neutro_distribuido=True)["limite_v"], 230.0)

    def test_minimum_icc_uses_u0_of_the_system(self):
        c, cmax = P.C_MIN_BT, P.C_MAX_BT
        for un, u0 in ((380.0, 220.0), (400.0, 230.0)):
            with self.subTest(un=un):
                z = math.hypot(cmax * u0 / 10e3 + 0.01, 0.02)
                self.assertAlmostEqual(P.current_sc_min(un, 10, 0.01, 0.02, 1), c * u0 / (2.0 * z))
                self.assertAlmostEqual(P.current_sc_min(un, 10, 0.01, 0.02, 3), c * un / (2.0 * z))


class MemoUsesTheProjectSystem(unittest.TestCase):
    def _memo(self, voltage):
        spec = copy.deepcopy(C.CASES["groups_tns"])
        spec["board"]["voltage_v"] = voltage
        with mock.patch.dict(C.CASES, {"v": spec}):
            return C.run("v")

    @staticmethod
    def _differentials(out):
        return [c["diferencial"] for c in out["memo"]["circuits"] if c["diferencial"] and c["diferencial"]["zs_max_ohm"]]

    def test_380_v_board_gives_u0_220_in_zs_max_and_in_the_text(self):
        out = self._memo(380.0)
        difs = self._differentials(out)
        self.assertTrue(difs)
        self.assertTrue(all(d["zs_max_ohm"] == round(EA.zs_maxima(220.0, d["idn_ma"] / 1000), 0) for d in difs))
        self.assertIn("U0 = 220 V", out["mc_md"])
        self.assertNotIn("U0 = 230 V", out["mc_md"])

    def test_400_v_board_gives_u0_230(self):
        out = self._memo(400.0)
        difs = self._differentials(out)
        self.assertTrue(difs)
        self.assertTrue(all(d["zs_max_ohm"] == round(EA.zs_maxima(230.0, d["idn_ma"] / 1000), 0) for d in difs))
        self.assertIn("U0 = 230 V", out["mc_md"])
        self.assertNotIn("U0 = 220 V", out["mc_md"])


class OptionalTwoLevelKeys(unittest.TestCase):
    def test_defaults_are_the_nominal_voltage(self):
        self.assertEqual(SV.board_voltages({"TENSION_V": 400}), {"nominal_v": 400.0, "secondary_v": 400.0, "use_v": 400.0})
        self.assertEqual(SV.board_voltages({}), {"nominal_v": 380.0, "secondary_v": 380.0, "use_v": 380.0})

    def test_a_project_can_state_both_levels(self):
        b = {"TENSION_V": 400, "TENSION_SECUNDARIO_V": 400, "TENSION_USO_V": 380}
        self.assertEqual(SV.board_voltages(b), {"nominal_v": 400.0, "secondary_v": 400.0, "use_v": 380.0})
        self.assertEqual(SV.board_u0(b), 230.0)      # U0 follows the system defined for the project (TENSION_V)

    def test_stating_the_levels_equal_to_the_nominal_changes_nothing(self):
        base = {"TENSION_V": 380, "ICC_KA": 10, "FP_DEFAULT": 0.85}
        with_keys = dict(base, TENSION_SECUNDARIO_V=380, TENSION_USO_V=380)
        self.assertEqual(P.calculate(base, [dict(ROW)]), P.calculate(with_keys, [dict(ROW)]))

    def test_the_use_voltage_sets_the_load_current(self):
        base = {"TENSION_V": 400, "ICC_KA": 10, "FP_DEFAULT": 0.85}
        d400, _ = P.calculate(base, [dict(ROW)])
        d380, _ = P.calculate(dict(base, TENSION_USO_V=380), [dict(ROW)])
        self.assertGreater(d380["C-01"]["Ib"], d400["C-01"]["Ib"])


class NoStrayVoltageLiterals(unittest.TestCase):
    VALUES = (220, 230, 380, 400)
    # (file, value): reason. The series and the demonstration blocks are not nominal voltages of a project.
    ALLOWED = {
        ("aea_export.py", 400): "conductor section series [mm2]",
        ("aea_pipeline.py", 400): "circuit-breaker rating series [A]",
        ("current_and_loads.py", 400): "demonstration in __main__",
        ("current_and_loads.py", 230): "demonstration in __main__",
        ("short_circuit.py", 400): "demonstration in __main__",
        ("voltage_drop.py", 400): "demonstration in __main__",
        ("voltage_drop.py", 230): "demonstration in __main__",
    }

    @staticmethod
    def _literals(source):
        out = []
        for n in ast.walk(ast.parse(source)):
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool) and n.value in NoStrayVoltageLiterals.VALUES:
                out.append((n.lineno, int(n.value)))
        return out

    def _scan(self):
        found = []
        for f in engine_sources.listdir():
            if f.endswith(".py"):
                with open(engine_sources.join(f), encoding="utf-8") as fh:
                    found += [(f, line, v) for line, v in self._literals(fh.read())]
        return found

    def test_no_module_keeps_its_own_voltage_literal(self):
        stray = [(f, line, v) for f, line, v in self._scan() if (f, v) not in self.ALLOWED]
        self.assertEqual(stray, [], "nominal voltages and U0 come from system_voltage / aea_tables.json (D16)")

    def test_the_allowlist_is_not_stale(self):
        present = {(f, v) for f, _, v in self._scan()}
        self.assertEqual(sorted(set(self.ALLOWED) - present), [])

    def test_scanner_detects_literals(self):
        self.assertEqual(self._literals("U0 = 230.0\ndef f(u=380): pass\nx = 12"), [(1, 230), (2, 380)])


if __name__ == "__main__":
    unittest.main()
