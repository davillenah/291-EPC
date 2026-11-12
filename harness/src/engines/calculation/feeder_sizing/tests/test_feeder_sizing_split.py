"""MIG-37b: `epc_feeder_sizing` is the home of its modules; the old `epc_aea90364` names are shims that give the very same objects. Expected values are read from the shim, never typed."""
import importlib
import unittest

PACKAGE = 'epc_feeder_sizing'
MODULES = ['aea_conductors', 'aea_ampacity', 'conductor_selection', 'cable_thermal', 'aea_route']
PUBLIC = {'aea_conductors': ['current_corrected', 'iz_admisible', 'k_adiabatico_771'], 'aea_ampacity': ['factores', 'iz', 'iz_base', 'parametros'], 'conductor_selection': ['cargar_tabla', 'main', 'seleccionar_conductor'], 'cable_thermal': ['k_material', 'seccion_comercial_superior', 'seccion_minima_mm2', 'tiempo_maximo_s', 'verificar_i2t'], 'aea_route': ['iz_ruta', 'route_warnings', 'segment_params', 'total_length', 'validate']}

def _load(name):
    return importlib.import_module(f"{PACKAGE}.{name}")


class Test_feeder_sizing(unittest.TestCase):
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
            ('cable_thermal', 'k_material', ('Cu', 'XLPE'), {}),
            ('cable_thermal', 'seccion_minima_mm2', (10000, 0.5, 143), {}),
            ('cable_thermal', 'verificar_i2t', (10000, 0.5, 143, 50), {}),
            ('cable_thermal', 'seccion_comercial_superior', (49.45, [35, 50, 70]), {}),
        ]
        for module, function, args, kwargs in calls:
            with self.subTest(function=function, args=args):
                new = getattr(_load(module), function)(*args, **kwargs)
                old = getattr(importlib.import_module(f"epc_aea90364.{module}"), function)(*args, **kwargs)
                self.assertEqual(new, old)
                self.assertIsNotNone(new)


if __name__ == "__main__":
    unittest.main()
