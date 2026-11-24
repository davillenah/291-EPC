"""SYM-00: the SLD and the MLD DXF carry their symbols as `INSERT` blocks defined once, with no audit error."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import ezdxf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import characterization as C  # noqa: E402


class SymbolBlockTests(unittest.TestCase):
    def test_the_diagrams_place_their_symbols_as_blocks(self):
        work = Path(tempfile.mkdtemp(prefix="symblocks_"))
        try:
            C.B.design(json.loads(json.dumps(C.SMALL)), work, "T1", None, None, 18, ("sld", "mld"))
            for name in ("SLD_T1.dxf", "MLD_T1.dxf"):
                doc = ezdxf.readfile(str(work / "out" / name))
                inserts = list(doc.modelspace().query("INSERT"))
                blocks = {b.name for b in doc.blocks if not b.name.startswith("*")}
                self.assertTrue(inserts, name)
                self.assertTrue({i.dxf.name for i in inserts} <= blocks, name)
                self.assertLessEqual(len(blocks), len(inserts), name)             # a block is defined once, however many times it is inserted
                self.assertEqual([e.message for e in doc.audit().errors], [], name)
        finally:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
