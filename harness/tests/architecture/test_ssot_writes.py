"""MIG-31 / MIG-32: nothing under harness/src/disciplines writes files except the project store (AST scan).

Allowed: `electrical_lv/store.py` only (the project folder, deliverable manifests included). The drawing engine writes stage 14's files itself, so
`stages/output_stages.py` has no write call of its own; `manifest.py`, `norm_records.py` and `stages/package_stage.py` (stage 16) are pure.
Also: only `pipeline.py` opens a store write session (`pipeline_session`), only `store.py` builds a `PipelineToken`, and only the run recorder
(with the pipeline's token) calls `write_manifest` / `update_manifest`.

MIG-33a: the platform layer (`harness/src/platform/epc_platform`) may write files in ONE module only: `events/log.py` (the append-only event
log). Every other platform module has no write call; the workflow state is written through `ProjectStore.write_workflow`, and only
`workflow/machine.py` opens a store session there. All other rules above stay as they are.

  python -m unittest harness/tests/architecture/test_ssot_writes.py
"""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "disciplines"
WRITERS = {"electrical_lv/store.py"}
SESSION_USERS = {"electrical_lv/pipeline.py", "electrical_lv/store.py"}
TOKEN_BUILDERS = {"electrical_lv/store.py"}
MANIFEST_WRITERS = {"electrical_lv/store.py", "electrical_lv/recorder.py"}
WRITE_METHODS = {"write_text", "write_bytes"}
MODULE_FUNCTIONS = {"shutil": {"copy", "copy2", "copyfile", "copytree", "move"}, "os": {"replace", "rename"}}
MODE = re.compile(r"[rbtU+wax]{1,4}")


def _is_write_mode(node):
    """A constant string such as 'w', 'wb', 'a', 'x', 'r+' (a mode that can change a file)."""
    value = node.value if isinstance(node, ast.Constant) else None
    return isinstance(value, str) and bool(MODE.fullmatch(value)) and any(c in value for c in "wax+")


def _call_name(node):
    func = node.func
    if isinstance(func, ast.Name):
        return None, func.id
    if isinstance(func, ast.Attribute):
        owner = func.value.id if isinstance(func.value, ast.Name) else None
        return owner, func.attr
    return None, None


def _is_open_for_write(node, name):
    if name != "open":
        return False
    args = list(node.args) + [k.value for k in node.keywords if k.arg == "mode"]
    return any(_is_write_mode(a) for a in args)


def _is_write_call(node):
    owner, name = _call_name(node)
    return name in WRITE_METHODS or name in MODULE_FUNCTIONS.get(owner, ()) or _is_open_for_write(node, name)


def _imports_write_function(node):
    if not isinstance(node, ast.ImportFrom):
        return False
    return node.module in MODULE_FUNCTIONS and any(a.name in MODULE_FUNCTIONS[node.module] for a in node.names)


def write_sites(source):
    """Line numbers of calls that write or copy files: open(..., 'w'/'a'/'x'/'+'), write_text, write_bytes, shutil.copy*/move, os.replace/rename."""
    sites = []
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call) and _is_write_call(node)) or _imports_write_function(node):
            sites.append(node.lineno)
    return sorted(sites)


def calls_of(source, wanted):
    """Line numbers where a function or method called `wanted` is called."""
    return sorted(n.lineno for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call) and _call_name(n)[1] == wanted)


def modules_calling(wanted):
    """Relative paths of the discipline modules that call `wanted`."""
    found = set()
    for path in ROOT.rglob("*.py"):
        if calls_of(path.read_text(encoding="utf-8"), wanted):
            found.add(path.relative_to(ROOT).as_posix())
    return found


class WriteScanner(unittest.TestCase):
    def test_it_finds_every_kind_of_write(self):
        cases = [
            "open(p, 'w')", "open(p, 'wb')", "open(p, mode='a')", "open(p, 'x')", "open(p, 'r+')", "p.open('w')", "p.write_text('x')", "p.write_bytes(b'')",
            "shutil.copy(a, b)", "shutil.copy2(a, b)", "shutil.copyfile(a, b)", "shutil.copytree(a, b)", "shutil.move(a, b)", "os.replace(a, b)",
            "os.rename(a, b)", "from shutil import copy", "from os import replace"]
        for src in cases:
            with self.subTest(src=src):
                self.assertEqual(write_sites(src), [1], src)

    def test_it_ignores_reads_and_unrelated_calls(self):
        cases = ["open(p)", "open(p, 'r')", "open(p, 'rb')", "p.read_text()", "p.mkdir()", "json.dumps(x)", "d.get('w')", "print('w')",
                 "foo.copy(x)", "x.replace('a', 'b')", "from os import path", "from shutil import which"]
        for src in cases:
            with self.subTest(src=src):
                self.assertEqual(write_sites(src), [], src)

    def test_it_reports_each_line(self):
        self.assertEqual(write_sites("a = 1\nopen(p, 'w')\n\np.write_text('x')\n"), [2, 4])

    def test_calls_of_finds_methods_and_functions(self):
        self.assertEqual(calls_of("a.b.pipeline_session(1)\npipeline_session(2)\nx = pipeline_session", "pipeline_session"), [1, 2])


class DisciplinesWriteOnlyThroughTheStore(unittest.TestCase):
    def test_only_the_store_and_the_drawing_stage_may_write_files(self):
        for path in sorted(ROOT.rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            if rel in WRITERS:
                continue
            with self.subTest(module=rel):
                self.assertEqual(write_sites(path.read_text(encoding="utf-8")), [], f"{rel} writes a file outside the store")

    def test_the_store_is_the_only_module_with_a_write_call(self):
        found = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*.py") if write_sites(p.read_text(encoding="utf-8"))}
        self.assertEqual(found, {"electrical_lv/store.py"})

    def test_the_manifest_modules_and_stage_16_do_not_write(self):
        for rel in ("electrical_lv/manifest.py", "electrical_lv/norm_records.py", "electrical_lv/stages/package_stage.py"):
            with self.subTest(module=rel):
                self.assertTrue((ROOT / rel).is_file())
                self.assertNotIn(rel, WRITERS)
                self.assertEqual(write_sites((ROOT / rel).read_text(encoding="utf-8")), [])

    def test_only_the_recorder_writes_manifests_through_the_store(self):
        for name in ("write_manifest", "update_manifest"):
            with self.subTest(method=name):
                self.assertEqual(modules_calling(name) - MANIFEST_WRITERS, set())
        self.assertIn("electrical_lv/recorder.py", modules_calling("write_manifest"))

    def test_the_store_is_a_writer(self):
        self.assertTrue(write_sites((ROOT / "electrical_lv" / "store.py").read_text(encoding="utf-8")))

    def test_the_writer_list_names_files_that_exist(self):
        for rel in WRITERS:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_only_the_pipeline_opens_a_write_session(self):
        self.assertEqual(modules_calling("pipeline_session") - SESSION_USERS, set())
        self.assertIn("electrical_lv/pipeline.py", modules_calling("pipeline_session"))

    def test_only_the_store_builds_a_token(self):
        self.assertEqual(modules_calling("PipelineToken") - TOKEN_BUILDERS, set())


PLATFORM = Path(__file__).resolve().parents[2] / "src" / "platform" / "epc_platform"
PLATFORM_WRITERS = {"events/log.py"}
PLATFORM_SESSION_USERS = {"workflow/machine.py"}


def platform_modules_calling(wanted):
    return {p.relative_to(PLATFORM).as_posix() for p in PLATFORM.rglob("*.py") if calls_of(p.read_text(encoding="utf-8"), wanted)}


class PlatformWritesOnlyInTheEventLog(unittest.TestCase):
    def test_only_the_event_log_writes_files(self):
        found = {p.relative_to(PLATFORM).as_posix() for p in PLATFORM.rglob("*.py") if write_sites(p.read_text(encoding="utf-8"))}
        self.assertEqual(found, PLATFORM_WRITERS)

    def test_the_event_log_opens_files_for_append_only(self):
        src = (PLATFORM / "events" / "log.py").read_text(encoding="utf-8")
        modes = [n.args[1].value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call) and _call_name(n)[1] == "open" and len(n.args) > 1]
        self.assertEqual(modes, ["ab"])

    def test_only_the_workflow_opens_a_store_session_and_nothing_builds_a_token(self):
        self.assertEqual(platform_modules_calling("pipeline_session"), PLATFORM_SESSION_USERS)
        self.assertEqual(platform_modules_calling("PipelineToken"), set())

    def test_the_platform_never_calls_the_pipeline_or_the_manifest_writers(self):
        for name in ("write_manifest", "update_manifest", "write_ssot", "write_state", "write_profile", "freeze_inputs", "write_input"):
            with self.subTest(method=name):
                self.assertEqual(platform_modules_calling(name), set())

    def test_the_store_writes_the_workflow_only_below_reviews(self):
        src = (ROOT / "electrical_lv" / "store.py").read_text(encoding="utf-8")
        self.assertIn('self._write_json(WORKFLOW, data, "reviews")', src)


if __name__ == "__main__":
    unittest.main()
