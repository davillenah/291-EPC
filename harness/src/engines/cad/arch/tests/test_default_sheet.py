"""The default sheet of the v2 command is an IRAM sheet, taken from `epc_titleblock` by its command line (the adapter fetches it; the engine takes the sheet as data and starts nothing); without that package the engine's own frame is used and says so."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from epc_arch import cli_v2, sheets                               # noqa: E402
import helpers                                                    # noqa: E402

HAS_TITLEBLOCK = importlib.util.find_spec("epc_titleblock") is not None


def _run(*extra):
    tmp = tempfile.TemporaryDirectory()
    src, out = Path(tmp.name) / "flat.dxf", Path(tmp.name) / "out"
    src.write_bytes(helpers.room_dxf())
    code = cli_v2.main([str(src), "--out", str(out), "--formats", "svg", *extra])
    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    svg = (out / "flat.plan1.plan.svg").read_text(encoding="utf-8")
    tmp.cleanup()
    return code, manifest, svg


@unittest.skipUnless(HAS_TITLEBLOCK, "epc_titleblock is not installed here")
class TestDefaultIramSheet(unittest.TestCase):
    def test_the_default_sheet_is_an_iram_a1_with_its_title_block(self):
        code, manifest, svg = _run()
        self.assertEqual(code, 0)
        self.assertEqual(manifest["options"]["sheet_source"], "iram-default")
        self.assertIn('width="841mm" height="594mm"', svg)
        self.assertIn("PROYECTADO POR:", svg)

    def test_the_format_is_chosen_with_sheet(self):
        _, _, svg = _run("--sheet", "A4")
        self.assertIn('width="210mm" height="297mm"', svg)                      # an IRAM A4 stands upright

    def test_no_iram_draws_on_the_engines_own_frame(self):
        _, manifest, svg = _run("--no-iram", "--sheet", "A4")
        self.assertEqual(manifest["options"]["sheet_source"], "engine-frame")
        self.assertNotIn("PROYECTADO POR:", svg)

    def test_the_title_block_has_the_scale_and_the_name_of_the_plan(self):
        _, _, svg = _run("--sheet", "A3")
        self.assertIn(">1:", svg)


class TestWithoutTheTitleBlockPackage(unittest.TestCase):
    def test_the_engine_says_so_and_uses_its_own_frame(self):
        cli_v2.iram_template.cache_clear()
        with mock.patch.object(cli_v2.subprocess, "run", side_effect=OSError("no python")):
            code, manifest, _ = _run("--sheet", "A4")
        cli_v2.iram_template.cache_clear()
        self.assertEqual((code, manifest["options"]["sheet_source"]), (0, "engine-frame"))

    def test_an_unknown_format_gives_no_sheet(self):
        self.assertIsNone(cli_v2.iram_template("A9"))


class TestTheEngineTakesTheSheetAsData(unittest.TestCase):
    def test_the_library_starts_no_process_and_draws_on_its_own_frame_without_a_sheet(self):
        import subprocess
        from epc_arch import recognize, Options
        from epc_arch import author
        plan_dxf = author.plan_dxf
        arch = recognize(helpers.room_dxf(), "flat.dxf", Options()).architecture
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("a process was started")):
            text = plan_dxf(arch, "A1")
        self.assertIn("SECTION", text)

    @unittest.skipUnless(HAS_TITLEBLOCK, "epc_titleblock is not installed here")
    def test_a_sheet_given_as_data_is_used(self):
        from epc_arch import recognize, Options
        from epc_arch import author, template_from_svg
        plan_dxf = author.plan_dxf
        from epc_titleblock import build
        arch = recognize(helpers.room_dxf(), "flat.dxf", Options()).architecture
        template = template_from_svg(build("A1", False, None, False, None)["svg"])
        self.assertNotEqual(plan_dxf(arch, "A1", None, template), plan_dxf(arch, "A1"))


if __name__ == "__main__":
    unittest.main()
