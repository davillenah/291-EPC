"""MIG-37b: `epc_grounding` is the home of its modules; the old `epc_aea90364` names are shims that give the very same objects. Expected values are read from the shim, never typed."""
import importlib
import unittest

PACKAGE = 'epc_grounding'
MODULES = ['aea_earthing']
PUBLIC = {'aea_earthing': ['ra_maxima', 'resistance_rod', 'resistance_parallel', 'resistencia_malla', 'seccion_equipotencial_principal_mm2', 'seccion_pe_mm2']}

def _load(name):
    return importlib.import_module(f"{PACKAGE}.{name}")


class Test_grounding(unittest.TestCase):
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
            ('aea_earthing', 'ra_maxima', (0.03,), {}),
            ('aea_earthing', 'ra_maxima', (0.5,), {}),
            ('aea_earthing', 'seccion_pe_mm2', (50,), {}),
        ]
        for module, function, args, kwargs in calls:
            with self.subTest(function=function, args=args):
                new = getattr(_load(module), function)(*args, **kwargs)
                old = getattr(importlib.import_module(f"epc_aea90364.{module}"), function)(*args, **kwargs)
                self.assertEqual(new, old)
                self.assertIsNotNone(new)


if __name__ == "__main__":
    unittest.main()
