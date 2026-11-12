"""MIG-34: `harness/.claude/settings.json`, the hook and CODEOWNERS agree with the permission matrix (PRD 14.4).

* every deny pattern of settings.json corresponds to a protected path class, and the classes it covers are exactly the ones the matrix protects
  (rules D-04, D-07, D-08, D-09, D-10) minus the two the hook leaves out on purpose (`EXEMPT_CLASSES`: runs, harness_code);
* the hook command is wired; there are no `allow` rules that widen anything;
* `.github/CODEOWNERS` parses, every pattern's base folder exists and every protected class of the matrix has an owner entry.

  python -m pytest harness/tests/architecture/test_settings_consistency.py
"""
import importlib.util
import json
import re
import unittest
from pathlib import Path

from epc_platform.permissions import rules as R

REPO = Path(__file__).resolve().parents[3]
SETTINGS = REPO / "harness" / ".claude" / "settings.json"
HOOK = REPO / "harness" / ".claude" / "hooks" / "guard_paths.py"
CODEOWNERS = REPO / ".github" / "CODEOWNERS"
_SPEC = importlib.util.spec_from_file_location("guard_paths_for_settings", HOOK)
G = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(G)

MATRIX_PROTECTION_RULES = ("D-04", "D-07", "D-08", "D-09", "D-10")
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
SHELL_TOOLS = ("Bash", "PowerShell")
EXTRA_CLASS = "knowledge_normative"  # hook rule H-01, not in the matrix
OWNER_RULE_PREFIXES = ("git ", "rm ", "del ", "Remove-Item")
# Fragments of a path pattern -> the class they protect (first match wins).
FRAGMENTS = (("master_project_state.json", R.SSOT), ("project_profile.json", R.SSOT), ("ssot/", R.SSOT), ("deliverables/", R.DELIVERABLES),
             ("inputs/", R.INPUTS), ("audit/", R.AUDIT), ("knowledge/normative", EXTRA_CLASS), ("config/normative", R.CONFIG_NORMATIVE),
             ("harness/schemas", R.SCHEMAS), ("/ssot/**", R.SSOT))
SHELL_VERBS = (">", ">>", "tee", "Set-Content", "Add-Content", "Out-File", "cp", "mv", "Copy-Item", "Move-Item", "New-Item", "sed -i")


def settings():
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


def rules_of(tool):
    out = []
    for entry in settings()["permissions"]["deny"]:
        match = re.fullmatch(r"(\w+)\((.*)\)", entry)
        if match and match.group(1) == tool:
            out.append(match.group(2))
    return out


def class_of(pattern):
    for fragment, cls in FRAGMENTS:
        if fragment in pattern:
            return cls
    return None


def derived_classes():
    return {c for rule_id, _why, _roles, _actions, classes, _frozen in R.DENY if rule_id in MATRIX_PROTECTION_RULES for c in classes}


def codeowners_entries():
    entries = []
    for number, line in enumerate(CODEOWNERS.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if text and not text.startswith("#"):
            parts = text.split()
            entries.append((number, parts[0], parts[1:]))
    return entries


def glob_regex(pattern):
    """A regex for a CODEOWNERS (gitignore style) pattern over POSIX paths relative to the repository root."""
    anchored = pattern.startswith("/") or "/" in pattern.rstrip("/")
    body = pattern.strip("/") if anchored else pattern.rstrip("/")
    out, index = "", 0
    while index < len(body):
        if body.startswith("**/", index):
            out, index = out + "(?:.*/)?", index + 3
        elif body.startswith("**", index):
            out, index = out + ".*", index + 2
        elif body[index] == "*":
            out, index = out + "[^/]*", index + 1
        else:
            out, index = out + re.escape(body[index]), index + 1
    return re.compile(("^" if anchored else "^(?:.*/)?") + out + "(?:/.*)?$")


def owners_of(path, entries):
    found = None
    for _number, pattern, owners in entries:
        if glob_regex(pattern).match(path):
            found = owners
    return found


def base_dir(pattern):
    literal = []
    for part in pattern.strip("/").split("/"):
        if re.search(r"[*?\[]", part):
            break
        literal.append(part)
    return REPO.joinpath(*literal)


class SettingsAgreeWithTheMatrix(unittest.TestCase):
    def test_the_derived_set_is_what_the_matrix_says(self):
        self.assertEqual(derived_classes(), {R.INPUTS, R.SSOT, R.DELIVERABLES, R.CONFIG_NORMATIVE, R.RUNS, R.AUDIT, R.SCHEMAS, R.HARNESS_CODE})

    def test_the_hook_exempts_only_classes_the_matrix_protects(self):
        self.assertEqual(set(G.EXEMPT_CLASSES), {R.RUNS, R.HARNESS_CODE})
        self.assertLessEqual(set(G.EXEMPT_CLASSES), derived_classes())

    def test_edit_rules_cover_exactly_the_protected_classes(self):
        expected = derived_classes() - set(G.EXEMPT_CLASSES)
        for tool in EDIT_TOOLS:
            with self.subTest(tool=tool):
                patterns = rules_of(tool)
                self.assertTrue(patterns)
                classes = {class_of(p) for p in patterns}
                self.assertNotIn(None, classes, [p for p in patterns if class_of(p) is None])
                self.assertEqual(classes - {EXTRA_CLASS}, expected)
                self.assertEqual(classes & {EXTRA_CLASS}, {EXTRA_CLASS})

    def test_shell_rules_cover_the_same_classes_with_every_write_verb(self):
        expected = (derived_classes() - set(G.EXEMPT_CLASSES)) | {EXTRA_CLASS}
        for tool in SHELL_TOOLS:
            with self.subTest(tool=tool):
                path_rules = [p for p in rules_of(tool) if not p.startswith(OWNER_RULE_PREFIXES)]
                self.assertEqual({class_of(p) for p in path_rules}, expected)
                for cls in expected:
                    verbs = {v for v in SHELL_VERBS if any(class_of(p) == cls and p.startswith(f"*{v}*") for p in path_rules)}
                    self.assertEqual(verbs, set(SHELL_VERBS), cls)

    def test_every_deny_entry_is_a_path_rule_or_an_owner_rule(self):
        for entry in settings()["permissions"]["deny"]:
            with self.subTest(entry=entry):
                match = re.fullmatch(r"(\w+)\((.*)\)", entry)
                self.assertTrue(match, entry)
                tool, pattern = match.groups()
                self.assertIn(tool, EDIT_TOOLS + SHELL_TOOLS)
                if tool in EDIT_TOOLS or not pattern.startswith(OWNER_RULE_PREFIXES):
                    self.assertIsNotNone(class_of(pattern))

    def test_owner_rules_deny_git_writes_and_deletes(self):
        git = {"commit", "push", "merge", "reset", "checkout", "switch", "branch", "tag", "stash", "rebase", "add"}
        for tool in SHELL_TOOLS:
            patterns = set(rules_of(tool))
            for sub in git:
                self.assertIn(f"git {sub}*", patterns, f"{tool} git {sub}")
                self.assertIn(sub, G.GIT_WRITES)
            for deleter in ("rm *", "del *", "Remove-Item*"):
                self.assertIn(deleter, patterns, f"{tool} {deleter}")

    def test_what_settings_deny_for_each_class_the_hook_blocks_for_every_agent(self):
        samples = {R.SSOT: "projects/p1/ssot/a.json", R.DELIVERABLES: "projects/p1/deliverables/a", R.INPUTS: "projects/p1/inputs/a",
                   R.AUDIT: "projects/p1/audit/a", R.CONFIG_NORMATIVE: "harness/config/normative/a", R.SCHEMAS: "harness/schemas/a",
                   EXTRA_CLASS: "harness/knowledge/normative/a"}
        covered = {class_of(p) for p in rules_of("Write")}
        self.assertEqual(covered, set(samples))
        for cls, sample in samples.items():
            for role in R.AGENTS:
                with self.subTest(cls=cls, role=role):
                    with self.assertRaises(G.Block):
                        G.judge_write(role, sample, str(REPO))

    def test_the_hook_is_wired_and_nothing_is_allowed_wider(self):
        data = settings()
        self.assertNotIn("allow", data["permissions"])
        self.assertEqual(set(data), {"permissions", "hooks"})
        pre = data["hooks"]["PreToolUse"]
        commands = [h["command"] for block in pre for h in block["hooks"]]
        self.assertEqual(commands, ["python harness/.claude/hooks/guard_paths.py"])
        self.assertTrue(all(h["type"] == "command" for block in pre for h in block["hooks"]))
        self.assertTrue((REPO / commands[0].split()[1]).is_file())

    def test_reading_the_normative_knowledge_stays_allowed(self):
        self.assertFalse([e for e in settings()["permissions"]["deny"] if e.startswith("Read(")])


class CodeownersAgreeWithTheMatrix(unittest.TestCase):
    OWNER = "@davillenah"

    def test_every_line_is_a_pattern_and_owners(self):
        entries = codeowners_entries()
        self.assertGreaterEqual(len(entries), 9)
        for number, pattern, owners in entries:
            with self.subTest(line=number, pattern=pattern):
                self.assertTrue(owners, "no owner")
                for owner in owners:
                    self.assertRegex(owner, r"^@[A-Za-z0-9][A-Za-z0-9-]*(/[A-Za-z0-9_.-]+)?$|^[^@\s]+@[^@\s]+$")
                self.assertNotIn(" ", pattern)
                self.assertFalse(pattern.startswith("!"))

    def test_the_owner_is_the_agreed_handle_and_no_placeholder_is_left(self):
        text = CODEOWNERS.read_text(encoding="utf-8")
        self.assertNotIn("OWNER_TO_BE_SET", text)
        for _number, _pattern, owners in codeowners_entries():
            self.assertEqual(owners, [self.OWNER])

    def test_every_patterns_base_folder_exists(self):
        for number, pattern, _owners in codeowners_entries():
            with self.subTest(line=number, pattern=pattern):
                self.assertTrue(base_dir(pattern).exists(), base_dir(pattern))

    def test_the_required_areas_are_listed(self):
        patterns = {p for _n, p, _o in codeowners_entries()}
        required = {"/harness/config/normative/", "/harness/src/engines/**/norm_register/", "**/data/review.json", "/harness/schemas/",
                    "/harness/src/platform/", "/harness/.claude/"}
        self.assertLessEqual(required, patterns)

    def test_every_protected_class_of_the_matrix_has_an_owner(self):
        samples = {R.INPUTS: "projects/p1/inputs/a.pdf", R.SSOT: "projects/p1/ssot/a.json", R.RUNS: "projects/p1/runs/r1/a.json",
                   R.DELIVERABLES: "projects/p1/deliverables/R0/a.dxf", R.REVIEWS: "projects/p1/reviews/a.json",
                   R.TRANSMITTALS: "projects/p1/transmittals/a.md", R.AUDIT: "projects/p1/audit/events.jsonl",
                   R.CONFIG_NORMATIVE: "harness/config/normative/AR/a.json", R.SCHEMAS: "harness/schemas/a.schema.json",
                   R.HARNESS_CODE: "harness/src/platform/epc_platform/permissions/rules.py"}
        self.assertEqual(set(samples), set(R.PATH_CLASSES))
        entries = codeowners_entries()
        for cls, path in samples.items():
            with self.subTest(cls=cls):
                self.assertEqual(owners_of(path, entries), [self.OWNER])

    def test_the_other_harness_code_folders_the_matrix_protects_have_owners(self):
        entries = codeowners_entries()
        for path in ("harness/.claude/settings.json", "harness/tools/ci/run_gate.py", "harness/tests/architecture/test_tree.py",
                     "harness/src/engines/calculation/aea90364/norm_register/x.json", "harness/src/engines/cad/sld/data/review.json",
                     ):
            with self.subTest(path=path):
                self.assertEqual(owners_of(path, entries), [self.OWNER])

    def test_the_matcher_does_not_over_match(self):
        entries = codeowners_entries()
        self.assertIsNone(owners_of("README.md", entries))
        self.assertIsNone(owners_of("harness/docs/BACKLOG.md", entries))


if __name__ == "__main__":
    unittest.main()
