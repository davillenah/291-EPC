"""OPT-13: invariants of the commercial-section choice over many generated inputs (seeded, standard library only)."""
import random
import unittest

from epc_feeder_sizing import FeederSizingError, seccion_comercial_superior

SAMPLES = 300


def _lists(seed):
    rng = random.Random(seed)
    for _ in range(SAMPLES):
        sections = sorted({round(rng.uniform(0.5, 400.0), 1) for _ in range(rng.randint(1, 12))})
        rng.shuffle(sections)
        yield rng.uniform(0.1, max(sections)), sections


class SectionProperties(unittest.TestCase):
    def test_the_choice_is_in_the_list_and_not_below_the_minimum(self):
        for s_min, sections in _lists(1):
            with self.subTest(s_min=s_min):
                chosen = seccion_comercial_superior(s_min, sections)
                self.assertIn(chosen, sections)
                self.assertGreaterEqual(chosen, s_min)

    def test_no_smaller_listed_section_would_have_done(self):
        for s_min, sections in _lists(2):
            chosen = seccion_comercial_superior(s_min, sections)
            with self.subTest(s_min=s_min):
                self.assertFalse([s for s in sections if s_min <= s < chosen])

    def test_a_larger_minimum_never_gives_a_smaller_section(self):
        for s_min, sections in _lists(3):
            bigger = min(max(sections), s_min * 1.7)
            with self.subTest(s_min=s_min):
                self.assertGreaterEqual(seccion_comercial_superior(bigger, sections), seccion_comercial_superior(s_min, sections))

    def test_the_order_of_the_list_does_not_matter(self):
        for s_min, sections in _lists(4):
            with self.subTest(s_min=s_min):
                self.assertEqual(seccion_comercial_superior(s_min, sections), seccion_comercial_superior(s_min, sorted(sections)))

    def test_a_minimum_above_every_section_is_refused(self):
        for _s_min, sections in _lists(5):
            with self.subTest(sections=sections):
                with self.assertRaises(FeederSizingError):
                    seccion_comercial_superior(max(sections) * 1.01, sections)


if __name__ == "__main__":
    unittest.main()
