"""D11: Ra is rounded to two decimals, conservatively (limit down, measured value up), never to an integer."""
import unittest

from epc_aea90364 import aea_earthing as E
from epc_aea90364 import aea_protection as PR
from epc_aea90364 import aea_rounding as RND
from epc_aea90364 import board_memo as BM
from epc_aea90364 import fmt


def memo_diferencial(idn_ma):
    tag = "T1"
    circ = {tag: {"description": "receptacles", "parent_tag": ""}}
    dat = {"In": 16, "Ib": 10.0, "S": 2.5, "icu": 10, "disp": "MCB"}
    det = {tag: {"tipo": "tomacorrientes", "kind": "rcbo", "topologia": "single", "cumple": True, "iz_a": 24.0, "icc_min_a": 500.0,
                 "s_termica_mm2": 2.5, "largo_m": 10.0, "ruta": [], "padre": ""}}
    return BM._circuit(tag, circ, dat, det, {}, idn_ma, "TT", 6000.0)["diferencial"]


class Helper(unittest.TestCase):
    def test_exact_two_decimals_are_kept(self):
        for x in (12.6, 12.0, 0.29, 0.57, 1.15, 40.0, 17.14):
            with self.subTest(x=x):
                self.assertEqual(RND.round_down_2(x), x)
                self.assertEqual(RND.round_up_2(x), x)

    def test_direction(self):
        self.assertEqual(RND.round_down_2(12.605), 12.60)
        self.assertEqual(RND.round_up_2(12.605), 12.61)
        self.assertEqual(RND.round_down_2(17.142857), 17.14)
        self.assertEqual(RND.round_up_2(17.142857), 17.15)
        self.assertEqual(RND.round_down_2(12.999), 12.99)
        self.assertEqual(RND.round_up_2(12.001), 12.01)

    def test_float_noise_never_moves_a_value_a_cent(self):
        self.assertEqual(RND.round_down_2(0.29 + 1e-15), 0.29)
        self.assertEqual(RND.round_up_2(0.29 + 1e-15), 0.29)
        self.assertEqual(RND.round_down_2(0.29 - 1e-15), 0.29)
        self.assertEqual(RND.round_up_2(40.00000000000001), 40.0)
        self.assertEqual(RND.round_down_2(12 / 0.3), 40.0)


class RaOutputs(unittest.TestCase):
    def test_adopted_limit_floors_to_two_decimals(self):
        self.assertEqual(E.ra_maxima(0.7)["adoptada"], 17.14)
        self.assertEqual(PR.ra_maxima_tt(0.7), 17.14)
        self.assertEqual(E.ra_maxima(1.0)["adoptada"], 12.0)
        self.assertEqual(E.ra_maxima(0.03)["adoptada"], 40.0)

    def test_the_other_columns_stay_exact(self):
        self.assertEqual(E.ra_maxima(0.7)["col2_24v"], 24.0 / 0.7)

    def test_measured_value_rounds_up_before_comparing(self):
        self.assertTrue(PR.verifica_tt(17.14, 0.7)["cumple"])
        self.assertFalse(PR.verifica_tt(17.141, 0.7)["cumple"])
        self.assertTrue(E.verifica_ra(17.14, 0.7))
        self.assertFalse(E.verifica_ra(17.141, 0.7))

    def test_memo_gives_two_decimals_not_an_integer(self):
        self.assertEqual(memo_diferencial(700.0)["ra_max_tt_ohm"], 17.14)
        self.assertEqual(memo_diferencial(1000.0)["ra_max_tt_ohm"], 12.0)

    def test_format_shows_two_decimals(self):
        self.assertEqual(fmt.d2(12.6), "12,60")
        self.assertEqual(fmt.d2(40.0), "40,00")
        self.assertEqual(BM.dec2(None), "Pendiente")
        self.assertEqual(BM.dec2(17.14), "17,14")
