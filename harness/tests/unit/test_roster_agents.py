"""MIG-35b: the roster is valid and least-privilege, the five generated agents equal what the generator writes, the bodies carry the key rules.

The 8 remaining legacy agent files are pinned by hash (line ends normalised): they are NOT touched by the roster work, so a hash change means someone edited
one by accident. If a later task changes one on purpose, update LEGACY_SHA256 in that task.

  PYTHONPATH=<harness env> python -m pytest harness/tests/unit/test_roster_agents.py
"""
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from disciplines.electrical_lv.intake.schema_check import validate
from epc_mcp.tools import build_registry

REPO = Path(__file__).resolve().parents[3]
CLAUDE = REPO / "harness" / ".claude"
ROSTER = json.loads((CLAUDE / "roster.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((REPO / "harness" / "schemas" / "roster.schema.json").read_text(encoding="utf-8"))
_SPEC = importlib.util.spec_from_file_location("regen_agents_under_test", REPO / "harness" / "tools" / "build" / "regen_agents.py")
G = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(G)

NAMES = ["orchestrator", "electrical_lv", "calc_check", "documentation", "procurement"]
BY_NAME = {a["name"]: a for a in ROSTER["agents"]}
PREFIX = "mcp__epc__"
READ_TOOLS = {PREFIX + t for t in ("epc_stage_table", "epc_engine_list", "epc_engine_info", "epc_norm_records", "epc_project_status")}
LEGACY_SHA256 = {
    "document-writer.md": "8ee5af8a696e571f65e2161c99c30d7b4d05528d0eaf1407770088db0b1f693a",
    "senior-civil-engineer.md": "ca23910c492ed5f51dafcabe188759981ca3311b7a1165160d006ae48f810b95",
    "senior-fire-protection-engineer.md": "ffefd0567df2113057c9959a3720c0fff03f9296cbae4d09f9dc8a6fb4403e93",
    "senior-hvac-engineer.md": "fb426749652acf3ad4b327ca7134d056a87431c279fcacd976924f6039af48cf",
    "senior-instrumentation-control-engineer.md": "d093b12ff4eea00bf6bbc5d40ca54400f07c6377009dcc742287047069ff1307",
    "senior-mechanical-engineer.md": "2a0bf48ad65b9ef37732c559769caa1e9ded673a9995f79acd495079e0b1cad3",
    "senior-piping-plumbing-engineer.md": "7ced351dcdc62559adc5fba3d31705b02abbba957c9f244479a67474f2f1b6aa",
    "senior-telecommunications-engineer.md": "84ac6e36b6e7918dff35c678390fec760c11ee39cad97b5226b3ffc9699f25b9",
}


def mcp(agent):
    return {t for t in agent["tools"] if t.startswith(PREFIX)}


class RosterIsValid(unittest.TestCase):
    def test_validates_against_the_schema(self):
        self.assertEqual(validate(ROSTER, SCHEMA), [])

    def test_schema_rejects_a_bad_roster(self):
        bad = json.loads(json.dumps(ROSTER))
        bad["agents"][0]["effort"] = "extreme"
        bad["agents"][1]["tools"].append("WebFetch")
        del bad["agents"][2]["skills"]
        self.assertGreaterEqual(len(validate(bad, SCHEMA)), 3)

    def test_exactly_the_five_names(self):
        self.assertEqual([a["name"] for a in ROSTER["agents"]], NAMES)

    def test_models_and_effort(self):
        for a in ROSTER["agents"]:
            self.assertEqual((a["model"], a["effort"]), ("claude-sonnet-5-5", "medium"), a["name"])

    def test_turn_limits(self):
        self.assertEqual({n: a["max_turns"] for n, a in BY_NAME.items()},
                         {"orchestrator": 40, "electrical_lv": 30, "calc_check": 30, "documentation": 30, "procurement": 30})

    def test_skills_exist(self):
        for a in ROSTER["agents"]:
            for s in a["skills"]:
                self.assertTrue((CLAUDE / "skills" / s / "SKILL.md").is_file(), f"{a['name']}: skill {s}")


class ToolsAreLeastPrivilege(unittest.TestCase):
    def test_no_write_for_orchestrator_and_electrical_lv(self):
        for n in ("orchestrator", "electrical_lv"):
            self.assertFalse({"Write", "Edit"} & set(BY_NAME[n]["tools"]), n)

    def test_no_edit_anywhere(self):
        for a in ROSTER["agents"]:
            self.assertNotIn("Edit", a["tools"], a["name"])

    def test_every_agent_reads_and_runs_the_cli(self):
        for a in ROSTER["agents"]:
            self.assertTrue({"Read", "Grep", "Glob", "Bash"} <= set(a["tools"]), a["name"])

    def test_nobody_approves(self):
        for a in ROSTER["agents"]:
            self.assertNotIn(PREFIX + "epc_project_approve", a["tools"], a["name"])

    def test_every_agent_has_the_read_tools(self):
        for a in ROSTER["agents"]:
            self.assertTrue(READ_TOOLS <= mcp(a), a["name"])

    def test_write_tools_by_agent(self):
        names = ("epc_pipeline_run", "epc_project_issue", "epc_project_init", "epc_project_review")
        owners = {t: sorted(n for n, a in BY_NAME.items() if PREFIX + t in a["tools"]) for t in names}
        self.assertEqual(owners, {"epc_pipeline_run": ["orchestrator"], "epc_project_issue": ["orchestrator"],
                                  "epc_project_init": ["orchestrator"], "epc_project_review": ["calc_check"]})

    def test_only_calc_check_writes_files(self):
        self.assertEqual([n for n, a in BY_NAME.items() if "Write" in a["tools"]], ["calc_check"])

    def test_every_mcp_tool_exists_in_the_server(self):
        known = {PREFIX + n for n in build_registry().names("full")}
        for a in ROSTER["agents"]:
            self.assertFalse(mcp(a) - known, a["name"])


class GeneratorWorks(unittest.TestCase):
    def copy(self):
        tmp = Path(tempfile.mkdtemp(prefix="roster_test_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copy2(CLAUDE / "roster.json", tmp / "roster.json")
        (tmp / "agents").mkdir()
        shutil.copytree(CLAUDE / "agents" / "_bodies", tmp / "agents" / "_bodies")
        for n in NAMES:
            shutil.copy2(CLAUDE / "agents" / f"{n}.md", tmp / "agents" / f"{n}.md")
        return tmp

    def roster_edit(self, tmp, change):
        data = json.loads((tmp / "roster.json").read_text(encoding="utf-8"))
        change(data)
        (tmp / "roster.json").write_text(json.dumps(data), encoding="utf-8")

    def test_repository_files_are_generated_ones(self):
        self.assertEqual(G.check(CLAUDE), [])

    def test_check_passes_on_a_copy(self):
        self.assertEqual(G.main(["--check", "--claude-dir", str(self.copy())]), 0)

    def test_check_detects_a_hand_edit(self):
        tmp = self.copy()
        path = tmp / "agents" / "calc_check.md"
        path.write_bytes(path.read_bytes() + b"hand edit\n")
        self.assertEqual(G.main(["--check", "--claude-dir", str(tmp)]), 1)

    def test_check_detects_a_missing_file_and_write_repairs_it(self):
        tmp = self.copy()
        (tmp / "agents" / "procurement.md").unlink()
        self.assertEqual(G.main(["--check", "--claude-dir", str(tmp)]), 1)
        self.assertEqual(G.main(["--claude-dir", str(tmp)]), 0)
        self.assertEqual(G.main(["--check", "--claude-dir", str(tmp)]), 0)

    def test_roster_change_changes_the_file(self):
        tmp = self.copy()
        self.roster_edit(tmp, lambda d: d["agents"][0].update(max_turns=41))
        self.assertEqual(G.main(["--check", "--claude-dir", str(tmp)]), 1)

    def test_roster_with_a_wrong_name_is_refused(self):
        tmp = self.copy()
        self.roster_edit(tmp, lambda d: d["agents"][0].update(name="boss"))
        self.assertEqual(G.main(["--check", "--claude-dir", str(tmp)]), 1)

    def test_output_is_deterministic_lf_with_one_trailing_newline(self):
        for n in NAMES:
            raw = (CLAUDE / "agents" / f"{n}.md").read_bytes()
            self.assertNotIn(b"\r", raw, n)
            self.assertTrue(raw.endswith(b"\n") and not raw.endswith(b"\n\n"), n)

    def test_generated_file_shape(self):
        for n in NAMES:
            text = (CLAUDE / "agents" / f"{n}.md").read_text(encoding="utf-8")
            a = BY_NAME[n]
            self.assertTrue(text.startswith("---\nname: " + n + "\n"), n)
            self.assertIn(G.HEADER, text)
            self.assertIn("model: " + a["model"], text)
            self.assertIn("tools: " + ", ".join(a["tools"]), text)
            self.assertIn("maxTurns: " + str(a["max_turns"]), text)
            for s in a["skills"]:
                self.assertIn("  - " + s, text)


class LegacyAgentsAreUntouched(unittest.TestCase):
    def test_count_and_hashes(self):
        found = {p.name: hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in (CLAUDE / "agents").glob("*.md")
                 if p.stem not in NAMES + ["README"]}
        self.assertEqual(len(found), 8)
        self.assertEqual(found, LEGACY_SHA256)


class OneDutyPerRole(unittest.TestCase):
    """docs/prsad/ROLES-single-responsibility.md: every role owns exactly one duty and no duty has two owners (both rosters)."""
    DISCIPLINES = json.loads((CLAUDE / "roster.disciplines.json").read_text(encoding="utf-8"))
    ALL = ROSTER["agents"] + DISCIPLINES["agents"]

    def test_both_rosters_match_the_schema(self):
        for roster in (ROSTER, self.DISCIPLINES):
            self.assertEqual([], validate(roster, SCHEMA))

    def test_every_role_has_one_duty_and_no_duty_is_shared(self):
        owners = {}
        for a in self.ALL:
            self.assertIsInstance(a["duty"], str, a["name"])
            owners.setdefault(a["duty"], []).append(a["name"])
        self.assertEqual({d: n for d, n in owners.items() if len(n) > 1}, {})

    def test_there_is_one_orchestrator_and_one_auditor(self):
        by_duty = {a["duty"]: a["name"] for a in self.ALL}
        self.assertEqual("orchestrator", by_duty["sequencing"])
        self.assertEqual("calc_check", by_duty["audit"])
        self.assertEqual(1, sum(1 for a in self.ALL if "orchestrator" in a["name"]))

    def test_each_discipline_has_one_leader(self):
        leaders = [a["duty"] for a in self.ALL if a["duty"].startswith("design_intent:")]
        self.assertEqual(len(leaders), len(set(leaders)))
        self.assertIn("design_intent:electrical_lv", leaders)


if __name__ == "__main__":
    unittest.main()
