"""Drawing engines give the same bytes in threads and in processes as in a sequential run (ADR-0042, rule 3).

The single-line diagram is drawn from the example board with a fixed stamp date: one run alone, then the same job on four threads and on three processes.
Every file of every parallel run must have the same hash as the sequential one. Run: python -m unittest discover -s harness/tests/architecture
"""
import concurrent.futures as cf
import contextlib
import hashlib
import io
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EXAMPLE = REPO / "harness" / "src" / "engines" / "cad" / "draw" / "examples" / "sld" / "input_for_sld_V1.xlsx"
STAMP = "2026-01-01"
_STATE = {}


def _prepare(root: Path) -> dict:
    """The calculation files the diagram reads, made once with the board design (the same step the gate smoke check runs)."""
    from epc_drawing import board_design
    with contextlib.redirect_stdout(io.StringIO()):
        board_design.main(["--xlsx", str(EXAMPLE), "--out", str(root), "--name", "SLD_V1"])
    out = root / "out"
    return {"calc_json": str(out / "SLD_V1_sizing.json"), "detail_json": str(out / "SLD_V1_sizing_detail.json"), "figures_json": str(out / "SLD_V1_figures.json"),
            "xlsx": str(EXAMPLE), "titleblock_json": str(root / "titleblock-request.json")}


def draw_hashes(files: dict) -> dict:
    """Draws the diagram into a folder of its own and returns {file name: sha256}."""
    from epc_draw.sld import SldInput, draw
    with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
        draw(SldInput(**files), d, "SLD_V1", stamp_date=STAMP)
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(d).iterdir())}


def files_hashes(files: dict) -> dict:
    """The same drawing through the function that returns bytes and writes no folder: {file name: sha256}."""
    from epc_draw.sld import SldInput, draw_files
    with contextlib.redirect_stdout(io.StringIO()):
        made = draw_files(SldInput(**files), "SLD_V1", stamp_date=STAMP)
    return {name: hashlib.sha256(data).hexdigest() for name, data in sorted(made.items())}


class DrawingParallel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.files = _prepare(Path(cls.tmp.name))
        cls.sequential = draw_hashes(cls.files)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_sequential_run_is_repeatable(self):
        self.assertTrue(self.sequential)
        self.assertEqual(draw_hashes(self.files), self.sequential)

    def test_the_bytes_function_gives_the_files_the_folder_function_writes(self):
        self.assertEqual(files_hashes(self.files), self.sequential)

    def test_threads_give_the_sequential_bytes(self):
        with cf.ThreadPoolExecutor(4) as pool:
            runs = list(pool.map(draw_hashes, [self.files] * 4))
        self.assertEqual(runs, [self.sequential] * 4)

    def test_threads_on_the_bytes_function_give_the_sequential_bytes(self):
        with cf.ThreadPoolExecutor(4) as pool:
            runs = list(pool.map(files_hashes, [self.files] * 4))
        self.assertEqual(runs, [self.sequential] * 4)

    def test_processes_on_the_bytes_function_give_the_sequential_bytes(self):
        with cf.ProcessPoolExecutor(3) as pool:
            runs = list(pool.map(files_hashes, [self.files] * 4))
        self.assertEqual(runs, [self.sequential] * 4)

    def test_processes_give_the_sequential_bytes(self):
        with cf.ProcessPoolExecutor(3) as pool:
            runs = list(pool.map(draw_hashes, [self.files] * 4))
        self.assertEqual(runs, [self.sequential] * 4)


if __name__ == "__main__":
    unittest.main()
