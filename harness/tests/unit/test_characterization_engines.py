"""Every engine gives what it gave when the characterization was recorded (COD-13): the numeric functions, the document engines, the engines that take a whole
document, the rules and plan engines and, for the rest, the SHA-256 of what the pinned synthetic project delivers (sld, mld, dxf, symbols, titleblock, documents).

Golden file: harness/tests/characterization/golden/engines.json. A difference here means behaviour changed: either it is a bug, or the owner asked for it and
the golden file is recorded again with `python harness/tests/characterization/engine_cases.py --write` (golden files are never edited by hand).
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "characterization"
sys.path.insert(0, str(HERE))
import engine_cases as C   # noqa: E402

GOLDEN = json.loads(C.GOLDEN.read_text(encoding="utf-8")) if C.GOLDEN.is_file() else {}
ENGINES = C.REPO / "harness" / "src" / "engines"


def engine_packages():
    return sorted(p.name for pyproject in ENGINES.glob("*/*/pyproject.toml") for p in (pyproject.parent / "src").glob("epc_*") if p.is_dir())


class EngineCharacterization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.now = C.everything()

    def test_every_engine_is_pinned_somewhere(self):
        pinned = set(GOLDEN) | set(C.ALREADY_PINNED) | {e for engines in C.STAGES.values() for e in engines}
        self.assertEqual([e for e in engine_packages() if e not in pinned], [], "add the engine to the characterization (COD-13)")

    def test_the_numeric_functions(self):
        for engine, cases in C.numeric().items():
            with self.subTest(engine=engine):
                for key, value in cases.items():
                    self.assertEqual(value, GOLDEN[engine][key], key)

    def test_each_engine_matches_its_golden_record(self):
        for engine in sorted(self.now):
            if engine == "pipeline":
                continue
            with self.subTest(engine=engine):
                self.assertEqual(self.now[engine], GOLDEN[engine])

    def test_the_synthetic_project_delivers_the_same_files(self):
        now, then = self.now["pipeline"], GOLDEN["pipeline"]
        self.assertEqual(now["exit_code"], then["exit_code"])
        for name in sorted(then["stage_files"]):
            with self.subTest(stage_file=name):
                self.assertEqual(now["stage_files"].get(name), then["stage_files"][name])
        self.assertEqual(now["delivered"], then["delivered"])

    def test_the_record_has_no_machine_paths(self):
        text = json.dumps(GOLDEN)
        for fragment in ("/home/", "/tmp/", "C:\\\\", "E:\\\\"):
            self.assertNotIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
