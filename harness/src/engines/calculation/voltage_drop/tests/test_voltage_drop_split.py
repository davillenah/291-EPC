"""MIG-37b: `epc_voltage_drop` is the home of its modules; the old `epc_aea90364` names are shims that give the very same objects. Expected values are read from the shim, never typed."""
import importlib
import unittest

PACKAGE = 'epc_voltage_drop'
MODULES = ['aea_voltage_drop', 'voltage_drop']
PUBLIC = {'aea_voltage_drop': ['caida_gdc', 'drop_by_table', 'limite_caida_pct', 'longitud_maxima_gdc'], 'voltage_drop': ['caida_tension', 'complies_limit', 'longitud_maxima_m', 'porcentaje']}

def _load(name):
    return importlib.import_module(f"{PACKAGE}.{name}")


class Test_voltage_drop(unittest.TestCase):
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
            ('voltage_drop', 'caida_tension', (3,), {'i_a': 100, 'longitud_m': 200, 'r_ohm_km': 0.5, 'x_ohm_km': 0.1, 'fp': 0.8, 'un_v': 400}),
            ('voltage_drop', 'longitud_maxima_m', (3, 12.0, 100, 0.5, 0.1, 0.8), {}),
        ]
        for module, function, args, kwargs in calls:
            with self.subTest(function=function, args=args):
                new = getattr(_load(module), function)(*args, **kwargs)
                old = getattr(importlib.import_module(f"epc_aea90364.{module}"), function)(*args, **kwargs)
                self.assertEqual(new, old)
                self.assertIsNotNone(new)


if __name__ == "__main__":
    unittest.main()
