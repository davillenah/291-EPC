"""Projects live in a client folder: `projects/<CLIENT>/<AAAA-PROV-CLI-CODE>_<DESCRIPTION>/`; the project code is the part before the first `_`."""
import io
import json
import tempfile
import unittest
from pathlib import Path

import test_ssot_wired_pipeline as S

from epc_platform import api
from epc_platform.cli.main import main

CLOCK = lambda: "2026-01-01T00:00:00Z"  # noqa: E731
ORC = {"role": "orchestrator", "id": "o1"}
CODE = "2026-ES-HNDA-3085"
FOLDER = "2026-ES-HNDA-3085_ILUMINACION_PERIMETRAL_CARPOOL"
ANSWERS = dict(S.ANSWERS, project_code=CODE)


class FolderTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def init(self, code=CODE, client="HONDA", description="ILUMINACION_PERIMETRAL_CARPOOL", answers=None):
        return api.init_project(self.root, code, answers or dict(ANSWERS, project_code=code), clock=CLOCK, actor=ORC, client=client, description=description)

    def test_the_project_is_created_inside_its_client_folder(self):
        result = self.init()
        self.assertTrue(result["ok"], result)
        folder = self.root / "HONDA" / FOLDER
        self.assertTrue((folder / ".epc" / "audit").is_dir() and (folder / "inputs").is_dir() and (folder / "deliverables").is_dir())
        self.assertEqual(Path(result["data"]["path"]), folder.resolve())

    def test_a_project_is_found_by_its_code_and_two_clients_do_not_clash(self):
        self.init()
        self.init("2026-ES-FORD-2036", "FORD_ARGENTINA", "ALIMENTACION_ELECTRICA_ENFARDADORA")
        self.assertEqual(api.project_path(self.root, CODE), (self.root / "HONDA" / FOLDER).resolve())
        self.assertEqual(api.project_path(self.root, "2026-ES-FORD-2036").parent.name, "FORD_ARGENTINA")
        with self.assertRaises(api.ApiError) as cm:
            api.project_path(self.root, "2026-ES-HNDA-9999")
        self.assertEqual(cm.exception.code, "project_not_found")

    def test_the_same_code_cannot_be_created_twice(self):
        self.init()
        again = self.init(client="OTRO", description="OTRA_COSA")
        self.assertFalse(again["ok"])
        self.assertEqual(again["error"]["code"], "project_exists")

    def test_two_folders_with_one_code_are_ambiguous(self):
        self.init()
        (self.root / "OTRO" / (CODE + "_COPIA")).mkdir(parents=True)
        with self.assertRaises(api.ApiError) as cm:
            api.project_path(self.root, CODE)
        self.assertEqual(cm.exception.code, "ambiguous_project")

    def test_a_bad_code_client_or_description_is_refused_and_nothing_is_created(self):
        for kwargs in ({"code": "HNDA-3085"}, {"code": "2026-ES-HNDA-3085-X"}, {"client": "honda"}, {"client": "HONDA/X"}, {"description": "con espacios y ñ"},
                       {"description": "_X"}, {"description": ""}):
            with self.subTest(kwargs=kwargs):
                result = self.init(**kwargs)
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], "invalid_project")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_client_and_description_go_together(self):
        result = api.init_project(self.root, CODE, ANSWERS, clock=CLOCK, actor=ORC, client="HONDA")
        self.assertEqual((result["ok"], result["error"]["code"]), (False, "invalid_project"))

    def test_a_flat_project_still_works_and_is_found_first(self):
        result = api.init_project(self.root, "FLAT-1", dict(S.ANSWERS, project_code="FLAT-1"), clock=CLOCK, actor=ORC)
        self.assertTrue(result["ok"], result)
        self.assertEqual(api.project_path(self.root, "FLAT-1"), (self.root / "FLAT-1").resolve())

    def test_the_cli_creates_and_finds_the_nested_project(self):
        answers = self.root / "a.json"
        answers.write_text(json.dumps(ANSWERS), encoding="utf-8")
        out = io.StringIO()
        code = main(["--projects-root", str(self.root), "init", CODE, "--answers", str(answers), "--client", "HONDA", "--description", "ILUMINACION_PERIMETRAL_CARPOOL", "--json"],
                    stdout=out, stderr=io.StringIO(), clock=CLOCK, env={})
        self.assertEqual(code, 0, out.getvalue())
        out = io.StringIO()
        code = main(["--projects-root", str(self.root), "status", CODE, "--json"], stdout=out, stderr=io.StringIO(), clock=CLOCK, env={})
        self.assertEqual(code, 0, out.getvalue())
        self.assertEqual(json.loads(out.getvalue())["data"]["project"], FOLDER)


if __name__ == "__main__":
    unittest.main()
