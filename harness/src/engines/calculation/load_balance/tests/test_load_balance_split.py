"""MIG-37b: `epc_load_balance` is the home of its modules; the old `epc_aea90364` names are shims that give the very same objects. Expected values are read from the shim, never typed."""
import importlib
import unittest

PACKAGE = 'epc_load_balance'
MODULES = ['aea_demand', 'current_and_loads', 'system_voltage']
PUBLIC = {'aea_demand': ['coef_simultaneidad_conjunto', 'current_msd', 'dpms_total', 'factor_demanda_sistema'], 'current_and_loads': ['balance_cargas', 'corriente_monofasica', 'corriente_trifasica', 'reserve_breaker', 'split_phases'], 'system_voltage': ['board_u0', 'board_un_v', 'board_use_v', 'board_voltages', 'default_un_v', 'system_u0', 'systems']}

def _load(name):
    return importlib.import_module(f"{PACKAGE}.{name}")


class Test_load_balance(unittest.TestCase):
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
            ('current_and_loads', 'corriente_trifasica', (10000, 400, 0.8), {}),
            ('current_and_loads', 'corriente_monofasica', (2300, 230, 0.8, 0.5), {}),
            ('system_voltage', 'system_u0', (400,), {}),
            ('system_voltage', 'systems', (), {}),
            ('system_voltage', 'board_voltages', ({'TENSION_V': 380},), {}),
            ('system_voltage', 'default_un_v', (), {}),
        ]
        for module, function, args, kwargs in calls:
            with self.subTest(function=function, args=args):
                new = getattr(_load(module), function)(*args, **kwargs)
                old = getattr(importlib.import_module(f"epc_aea90364.{module}"), function)(*args, **kwargs)
                self.assertEqual(new, old)
                self.assertIsNotNone(new)


if __name__ == "__main__":
    unittest.main()
