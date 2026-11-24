"""Every layer of a DXF produced by the drawing pipelines carries a description (owner rule: NCS layer naming)."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import characterization as C  # noqa: E402

import ezdxf  # noqa: E402


class LayerDescriptionTests(unittest.TestCase):
    def test_sld_and_mld_layers_have_a_description(self):
        work = Path(tempfile.mkdtemp(prefix="layerdesc_"))
        try:
            C.B.design(json.loads(json.dumps(C.SMALL)), work, "T1", None, None, 18, ("sld", "mld"))
            dxfs = sorted((work / "out").rglob("*.dxf"))
            self.assertTrue(dxfs)
            for p in dxfs:
                doc = ezdxf.readfile(str(p))
                missing = [lay.dxf.name for lay in doc.layers if lay.dxf.name not in ("0", "Defpoints") and not lay.description]
                self.assertEqual(missing, [], p.name)
        finally:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
