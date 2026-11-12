"""MIG-37b: `epc_calc_common` is the home of its modules; the old `epc_aea90364` names are shims that give the very same objects. Expected values are read from the shim, never typed."""
import importlib
import unittest

PACKAGE = 'epc_calc_common'
MODULES = ['norm_data', 'aea_tables', 'policy', '_validate', 'fmt', 'aea_rounding']
PUBLIC = {'norm_data': ['clear_cache', 'criteria_file', 'load_json', 'normative_dir', 'path', 'read_json', 'rules_dir'], 'aea_tables': ['cargar', 'constante', 'derived', 'limpiar_cache_tablas'], 'policy': ['k1_no_disparo', 'k2_convencional', 'k_max_i2_iz'], '_validate': ['frac', 'nonneg', 'num', 'pos'], 'fmt': ['d2', 'mm', 'p1', 'sig2'], 'aea_rounding': ['round_down_2', 'round_up_2']}

def _load(name):
    return importlib.import_module(f"{PACKAGE}.{name}")


class Test_calc_common(unittest.TestCase):
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
            ('aea_rounding', 'round_down_2', (1.239,), {}),
            ('aea_rounding', 'round_up_2', (1.231,), {}),
            ('fmt', 'd2', (1.5,), {}),
            ('policy', 'k_max_i2_iz', (), {}),
            ('policy', 'k2_convencional', (), {}),
            ('aea_tables', 'cargar', (), {}),
            ('fmt', 'p1', (2.345,), {}),
        ]
        for module, function, args, kwargs in calls:
            with self.subTest(function=function, args=args):
                new = getattr(_load(module), function)(*args, **kwargs)
                old = getattr(importlib.import_module(f"epc_aea90364.{module}"), function)(*args, **kwargs)
                self.assertEqual(new, old)
                self.assertIsNotNone(new)


if __name__ == "__main__":
    unittest.main()
