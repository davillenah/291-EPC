"""MIG-37b: `epc_selectivity` is the home of its modules; the old `epc_aea90364` names are shims that give the very same objects. Expected values are read from the shim, never typed."""
import importlib
import unittest

PACKAGE = 'epc_selectivity'
MODULES = ['aea_protection']
PUBLIC = {'aea_protection': ['corriente_falla_tt', 'i2_convencional', 'in_max_por_iz', 'ra_maxima_tt', 'verifica_it_segunda_falla', 'verifica_tn', 'verifica_tt']}

def _load(name):
    return importlib.import_module(f"{PACKAGE}.{name}")


class Test_selectivity(unittest.TestCase):
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
            ('aea_protection', 'in_max_por_iz', (100, 'mcb'), {}),
            ('aea_protection', 'i2_convencional', (16, 'mcb'), {}),
            ('aea_protection', 'verifica_tn', (0.5, 400), {'un_v': 400.0}),
            ('aea_protection', 'ra_maxima_tt', (0.03,), {}),
        ]
        for module, function, args, kwargs in calls:
            with self.subTest(function=function, args=args):
                new = getattr(_load(module), function)(*args, **kwargs)
                old = getattr(importlib.import_module(f"epc_aea90364.{module}"), function)(*args, **kwargs)
                self.assertEqual(new, old)
                self.assertIsNotNone(new)


if __name__ == "__main__":
    unittest.main()
