"""D18: grouping outside the normative tables and buried D2 without its installation data are rejected (no interpolation, no repeated last factor, no cap, no default column)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from epc_aea90364 import aea_ampacity as A  # noqa: E402
from epc_aea90364 import aea_pipeline as P  # noqa: E402
from epc_aea90364 import aea_tables as T  # noqa: E402

BOARD = {"NOMBRE": "T", "TENSION_V": 380, "ICC_KA": 10, "FP_DEFAULT": 0.85}
FEEDER = {"TAG": "C-01", "DESCRIPCION": "ALIMENTADOR", "CARGA": 100, "UNIDAD_CARGA": "A", "TOPOLOGY": "single", "FASE": "3F", "KIND": "mccb", "LONGITUD_m": 30}


def air_row(item):
    return next(r for r in T.cargar()["factores_correccion"]["771.16.IV"]["filas"] if r["item"] == item)


class AirGroupingTests(unittest.TestCase):
    def test_every_tabulated_count_gives_its_table_factor(self):
        for item in "12345":
            row = air_row(item)
            for n, f in zip(row["numero_de_circuitos"][1:], row["factores"][1:]):
                with self.subTest(item=item, n=n):
                    self.assertEqual(T.factor_agrupamiento_aire(item, n), f)

    def test_a_count_between_tabulated_points_is_rejected_not_interpolated(self):
        self.assertEqual(air_row("1")["numero_de_circuitos"][9:11], [12, 16])
        for n in (10, 11, 13, 14, 15, 17, 19):
            with self.subTest(n=n), self.assertRaises(T.MissingNormDataError) as cm:
                T.factor_agrupamiento_aire("1", n)
            self.assertIn("Tabla 771.16.IV", str(cm.exception))
            self.assertIn("AGRUP_CIRCUITOS", str(cm.exception))
            self.assertIn("no se interpola", str(cm.exception))

    def test_a_count_beyond_the_table_is_rejected_not_the_last_factor(self):
        for item, n in (("1", 21), ("1", 25), ("2", 10), ("4", 20)):
            with self.subTest(item=item, n=n), self.assertRaises(T.MissingNormDataError):
                T.factor_agrupamiento_aire(item, n)

    def test_the_message_lists_the_counts_the_table_has(self):
        with self.assertRaises(T.MissingNormDataError) as cm:
            T.factor_agrupamiento_aire("1", 10)
        for n in air_row("1")["numero_de_circuitos"][1:]:
            self.assertIn(str(n), str(cm.exception))

    def test_one_circuit_needs_no_factor(self):
        self.assertEqual(T.factor_agrupamiento_aire("1", 1), 1.0)

    def test_the_error_is_a_value_error(self):
        self.assertTrue(issubclass(T.MissingNormDataError, ValueError))

    def test_ampacity_factors_reject_through_the_parameters(self):
        for n in (10, 25):
            with self.subTest(n=n), self.assertRaises(T.MissingNormDataError):
                A.factores(A.parametros({"METODO": "B1", "AGRUP_CIRCUITOS": n}), True)
        self.assertEqual(A.factores(A.parametros({"METODO": "B1", "AGRUP_CIRCUITOS": 12}), True)["f_agrup"], 0.45)

    def test_pipes_of_more_than_three_circuits_use_the_air_table_as_before(self):
        self.assertEqual(A.factores(A.parametros({"METODO": "B1", "AGRUP_CIRCUITOS": 4}), True)["f_agrup"], 0.65)


class BuriedGroupingTests(unittest.TestCase):
    def test_two_to_six_circuits_give_the_table_factor(self):
        for tabla in ("c", "d1", "d2"):
            f = T.cargar()["factores_correccion"]["771.16.VII." + tabla]
            filas = f[[k for k in f if k.startswith("numero_de")][0]]
            for n, valores in filas.items():
                self.assertEqual(T.factor_agrupamiento_enterrado(tabla, int(n), 0), valores[0])

    def test_more_than_six_circuits_are_rejected_not_capped(self):
        for tabla in ("c", "d1", "d2"):
            for n in (7, 8, 20):
                with self.subTest(tabla=tabla, n=n), self.assertRaises(T.MissingNormDataError) as cm:
                    T.factor_agrupamiento_enterrado(tabla, n, 0)
                self.assertIn(f"Tabla 771.16.VII.{tabla}", str(cm.exception))
                self.assertIn("2, 3, 4, 5, 6", str(cm.exception))

    def test_a_buried_conduit_method_is_also_limited_to_the_table(self):
        with self.assertRaises(T.MissingNormDataError):
            A.factores(A.parametros({"METODO": "D1", "AGRUP_CIRCUITOS": 7}), True)
        self.assertEqual(A.factores(A.parametros({"METODO": "D1", "AGRUP_CIRCUITOS": 6}), True)["f_agrup"], 0.6)


class D2DataTests(unittest.TestCase):
    def test_grouped_d2_without_separation_is_rejected_and_asks_for_it(self):
        with self.assertRaises(T.MissingNormDataError) as cm:
            A.factores(A.parametros({"METODO": "D2", "AGRUP_CIRCUITOS": 2}), True)
        self.assertIn("SEPARACION_CABLES", str(cm.exception))
        self.assertIn("en contacto", str(cm.exception))
        self.assertIn("no hay columna por defecto", str(cm.exception))

    def test_grouped_d2_with_each_separation_reads_its_column(self):
        columns = T.cargar()["factores_correccion"]["771.16.VII.c"]
        for idx, text in enumerate(("en contacto", "1 diámetro", "0,125 m", "0,25 m", "0,5 m")):
            with self.subTest(separation=text):
                p = A.parametros({"METODO": "D2", "AGRUP_CIRCUITOS": 3, "SEPARACION_CABLES": text})
                self.assertEqual(A.factores(p, True)["f_agrup"], columns["numero_de_circuitos"]["3"][idx])

    def test_the_separation_text_is_read_without_accents_case_or_decimal_comma(self):
        p = A.parametros({"METODO": "D2", "AGRUP_CIRCUITOS": 2, "SEPARACION_CABLES": "1 DIAMETRO"})
        self.assertEqual(A.factores(p, True)["f_agrup"], 0.8)
        p = A.parametros({"METODO": "D2", "AGRUP_CIRCUITOS": 2, "SEPARACION_CABLES": "0.25 m"})
        self.assertEqual(A.factores(p, True)["f_agrup"], 0.9)

    def test_an_unknown_separation_is_rejected(self):
        with self.assertRaises(T.MissingNormDataError):
            A.factores(A.parametros({"METODO": "D2", "AGRUP_CIRCUITOS": 2, "SEPARACION_CABLES": "2 m"}), True)

    def test_a_single_d2_circuit_needs_no_separation(self):
        self.assertEqual(A.factores(A.parametros({"METODO": "D2"}), True)["f_agrup"], 1.0)

    def test_d2_without_column_is_rejected_and_names_the_columns(self):
        p = A.parametros({"METODO": "D2"})
        with self.assertRaises(T.MissingNormDataError) as cm:
            A.iz(p, 2.5, 3)
        text = str(cm.exception)
        self.assertIn("COLUMNA_D2", text)
        self.assertIn("Tabla 771.16.VI", text)
        for column in ("c1_1x", "c4_3x", "c5_3x"):
            self.assertIn(column, text)
        self.assertNotIn("c2_2x", text)                                   # two-conductor columns do not apply to three loaded conductors

    def test_d2_with_a_column_takes_that_table_column(self):
        block = T._bloque("771.16.VI", "pvc")
        keys = [c["clave"] for c in block["columnas"]]
        for cargados, column in ((3, "c1_1x"), (3, "c4_3x"), (3, "c5_3x"), (2, "c2_2x"), (2, "c3_2x")):
            with self.subTest(column=column):
                p = A.parametros({"METODO": "D2", "COLUMNA_D2": column})
                self.assertEqual(A.iz_base(p, 2.5, cargados), float(block["filas"]["cu"]["2.5"][keys.index(column)]))

    def test_a_column_that_does_not_fit_the_conductor_count_is_rejected(self):
        with self.assertRaises(T.MissingNormDataError):
            A.iz(A.parametros({"METODO": "D2", "COLUMNA_D2": "c2_2x"}), 2.5, 3)
        with self.assertRaises(T.MissingNormDataError):
            A.iz(A.parametros({"METODO": "D2", "COLUMNA_D2": "c9"}), 2.5, 2)

    def test_an_explicit_iz_needs_no_column(self):
        self.assertEqual(A.iz(A.parametros({"METODO": "D2", "IZ_A": 100}), 2.5, 3), 100.0)

    def test_other_methods_ignore_the_d2_keys(self):
        p = A.parametros({"METODO": "C", "COLUMNA_D2": "c5_3x", "SEPARACION_CABLES": "x"})
        self.assertEqual(A.iz_base(p, 2.5, 3), A.iz_base(A.parametros({"METODO": "C"}), 2.5, 3))


class PipelineRejectionTests(unittest.TestCase):
    def calc(self, **changes):
        return P.calculate(BOARD, [{**FEEDER, **changes}])

    def test_a_grouping_outside_the_table_rejects_the_whole_calculation(self):
        with self.assertRaises(T.MissingNormDataError) as cm:
            self.calc(AGRUP_CIRCUITOS=10)
        self.assertTrue(str(cm.exception).startswith("C-01: "))
        self.assertIn("Tabla 771.16.IV", str(cm.exception))

    def test_it_is_not_worked_around_with_a_bigger_section_and_a_warning(self):
        with self.assertRaises(ValueError):
            self.calc(AGRUP_CIRCUITOS=25)

    def test_buried_grouping_beyond_six_rejects(self):
        with self.assertRaises(T.MissingNormDataError):
            self.calc(METODO="D1", AGRUP_CIRCUITOS=7)

    def test_buried_d2_without_column_rejects_and_with_it_calculates(self):
        with self.assertRaises(T.MissingNormDataError) as cm:
            self.calc(METODO="D2")
        self.assertIn("COLUMNA_D2", str(cm.exception))
        data, _ = self.calc(METODO="D2", COLUMNA_D2="c4_3x")
        self.assertIn("C-01", data)

    def test_grouped_buried_d2_needs_the_separation_too(self):
        with self.assertRaises(T.MissingNormDataError) as cm:
            self.calc(METODO="D2", COLUMNA_D2="c4_3x", AGRUP_CIRCUITOS=3)
        self.assertIn("SEPARACION_CABLES", str(cm.exception))
        data, _ = self.calc(METODO="D2", COLUMNA_D2="c4_3x", AGRUP_CIRCUITOS=3, SEPARACION_CABLES="0,25 m")
        self.assertIn("C-01", data)

    def test_a_tabulated_count_still_calculates(self):
        data, _ = self.calc(AGRUP_CIRCUITOS=9)
        self.assertIn("C-01", data)

    def test_a_buried_stretch_of_a_route_needs_the_column(self):
        route = [{"kind": "tray_perforated", "length_m": 5}, {"kind": "buried_direct", "length_m": 10}]
        with self.assertRaises(T.MissingNormDataError):
            self.calc(RUTA=route)
        data, _ = self.calc(RUTA=route, COLUMNA_D2="c4_3x")
        self.assertIn("C-01", data)

    def test_a_stretch_grouped_beyond_the_table_rejects(self):
        route = [{"kind": "tray_solid", "length_m": 5, "circuits": 25}]
        with self.assertRaises(T.MissingNormDataError):
            self.calc(RUTA=route)


if __name__ == "__main__":
    unittest.main()
