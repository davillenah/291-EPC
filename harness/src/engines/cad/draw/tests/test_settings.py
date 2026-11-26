"""The DXF settings are handed in as data and are local to the call (ADR-0042): no environment, and two calls with different settings can run at the same time."""
import json
import tempfile
import threading
import unittest
from pathlib import Path

from epc_draw.core import layers, settings, textstyle


def write(folder, name, data):
    path = Path(folder) / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


class Settings(unittest.TestCase):
    def test_without_a_block_there_is_no_override(self):
        self.assertEqual(settings.current(), settings.DxfSettings())
        self.assertEqual(layers.load(), layers.defaults())

    def test_the_settings_apply_inside_the_block_only(self):
        with tempfile.TemporaryDirectory() as t:
            f = write(t, "l.json", {"layers": {"sld.diagram": {"name": "OTHER"}}})
            with settings.use(settings.DxfSettings(layer_files=(f,))):
                self.assertEqual(layers.load()["sld.diagram"]["name"], "OTHER")
            self.assertNotEqual(layers.load()["sld.diagram"]["name"], "OTHER")

    def test_the_text_files_and_the_folder_apply(self):
        with tempfile.TemporaryDirectory() as t:
            f = write(t, "t.json", {"font": {"regular": "one.ttf"}})
            with settings.use(settings.DxfSettings(config_dir="", text_files=(f,))):
                self.assertEqual(textstyle.load()["font"]["regular"], "one.ttf")
            write(t, "text.json", {"font": {"regular": "two.ttf"}})
            with settings.use(settings.DxfSettings(config_dir=t)):
                self.assertEqual(textstyle.load()["font"]["regular"], "two.ttf")

    def test_from_environment_reads_only_the_mapping_it_is_given(self):
        s = settings.from_environment({"EPC_DXF_CONFIG_DIR": "/a", "EPC_LAYERS_JSON": "/b:/c", "EPC_DXF_TEXT_JSON": ""}, ":")
        self.assertEqual(s, settings.DxfSettings(config_dir="/a", layer_files=("/b", "/c"), text_files=()))
        self.assertEqual(settings.from_environment({}, ":"), settings.DxfSettings(config_dir=None))

    def test_two_threads_with_different_settings_do_not_meet(self):
        with tempfile.TemporaryDirectory() as t:
            files = [write(t, f"{n}.json", {"layers": {"sld.diagram": {"name": n}}}) for n in ("A", "B")]
            seen, ready, go = {}, threading.Barrier(2), threading.Barrier(2)

            def work(name, file):
                with settings.use(settings.DxfSettings(layer_files=(file,))):
                    ready.wait()
                    go.wait()
                    seen[name] = layers.load()["sld.diagram"]["name"]

            threads = [threading.Thread(target=work, args=(n, f)) for n, f in zip("AB", files)]
            [x.start() for x in threads]
            [x.join() for x in threads]
        self.assertEqual(seen, {"A": "A", "B": "B"})


if __name__ == "__main__":
    unittest.main()
