"""MIG-37b: `epc_short_circuit` is the home of its modules; the old `epc_aea90364` names are shims that give the very same objects. Expected values are read from the shim, never typed."""
import importlib
import unittest

PACKAGE = 'epc_short_circuit'
MODULES = ['short_circuit', 'aea_icc_decay', 'aea_icc_factors']
PUBLIC = {'short_circuit': ['aporte_motor', 'calcular_ik', 'corriente_asignada_trafo', 'corriente_pico', 'factor_c', 'factor_kappa', 'factor_kt', 'ik_aguas_abajo'], 'aea_icc_decay': ['constante_aperiodica_s', 'constantes_tiempo', 'corriente_alterna_t'], 'aea_icc_factors': ['c_max_desde_tension', 'ik_generador', 'k_g', 'k_gs']}

def _load(name):
    return importlib.import_module(f"{PACKAGE}.{name}")


class Test_short_circuit(unittest.TestCase):
    def test_the_package_imports_and_exposes_its_public_names(self):
        for name in MODULES:
            module = _load(name)
            for attr in PUBLIC[name]:
                with self.subTest(module=name, attr=attr):
                    self.assertTrue(callable(getattr(module, attr)), attr)

    def test_each_old_module_name_of_epc_aea90364_is_the_same_module_object(self):
        for name in MODULES:
            with self.subTest(module=name):
                shim = importlib.import_module(f"epc_aea90364.{name}")
                self.assertIs(shim, _load(name))
                for attr in PUBLIC[name]:
                    self.assertIs(getattr(shim, attr), getattr(_load(name), attr))

    def test_a_value_the_engine_computes_equals_the_value_through_the_shim(self):
        calls = [
            ('short_circuit', 'factor_c', (6,), {}),
            ('short_circuit', 'corriente_asignada_trafo', (1000000.0, 400.0), {}),
            ('short_circuit', 'calcular_ik', (400.0, 1.05), {'red': None, 'trafo': {'sn_va': 1000000.0, 'uk_pct': 6}}),
        ]
        for module, function, args, kwargs in calls:
            with self.subTest(function=function, args=args):
                new = getattr(_load(module), function)(*args, **kwargs)
                old = getattr(importlib.import_module(f"epc_aea90364.{module}"), function)(*args, **kwargs)
                self.assertEqual(new, old)
                self.assertIsNotNone(new)


if __name__ == "__main__":
    unittest.main()
