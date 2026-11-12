"""MIG-35b: the roster is valid and least-privilege, the five generated agents equal what the generator writes, the bodies carry the key rules.

The 43 legacy agent files are pinned by hash (line ends normalised): they are NOT touched by the roster work, so a hash change means someone edited
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
    "bim-clash-detection-coordinator.md": "8d12fdf5a0c1f3da8b3223c0e9e116e9fb5d7ec2b747bea942bdc5aba64943af",
    "catalog-normalizer-agent.md": "9932f0e5290875181231e6a43003d531b0fc0b3765c404c6cea06f689ad5a6ee",
    "commissioning-start-up-engineer.md": "78a40051e5d755dd730aabaf93b749d032f692dc12dd7f406f54dbca80289fac",
    "constructability-reviewer.md": "e081769644844879c95a6e6352c99d7a17c1ad61d55b49a3d9465acfed4da015",
    "contract-claims-manager.md": "56e1b26d34df4172c44048abb54a39ad77eff9e21a7d9dba87baef1253081975",
    "cost-control-estimator.md": "f3f9ea8104a0c3535889e67434820878486ec12390367a006047cab814692e24",
    "director-of-projects.md": "4b88f7045b6305133d30346c28b6f6c463ba6a01d4484a87ddf3363d6be52955",
    "document-writer.md": "8ee5af8a696e571f65e2161c99c30d7b4d05528d0eaf1407770088db0b1f693a",
    "electrical-backup-power-engineer.md": "0dd55f867c15f0c8f95a59e82116f7d725738e1b4397490f1d3a4015c794f3c5",
    "electrical-cable-sizing-engineer.md": "eb00557c1fe1ea0e8c1b4eaae9ee9c1166b6dedc4ffbbffad4ab4f2c5be51689",
    "electrical-drawing-checker.md": "de1df6cb0162237f4af3e014cef78315394d208b9da90ee895242e6dc5475e67",
    "electrical-earthing-lightning-engineer.md": "a305a4af62e0da29941eded71e475025d159db199018322b6c87929565d3ad83",
    "electrical-lighting-designer.md": "93f5c73436873e559e299d3ece44a1170d335419f9c26d058af8fd9d28c0defc",
    "electrical-load-analyst.md": "854a8e8179f4549b215c0568112d0ae0f7e7397394d72e89b23817c36431e3b7",
    "electrical-materials-takeoff.md": "588845f4a22dc050e82d61e526a59474c0ca9eb8cfe0eb70f53bedc948afb418",
    "electrical-power-motors-engineer.md": "f446c8eefd2f741098d6ee5081562ca6f08d3a2665b0a7be5c5ce7f18ff62bca",
    "electrical-protection-coordination-engineer.md": "c5b19f3f7b0378e9d6414f2847104da42c7573c489014ed5837addb23ab224c1",
    "electrical-report-writer.md": "3431779e78f09dd4e2e3343052720d6dff6a45c63df783c6ab6ca705d05028dd",
    "electrical-spec-writer.md": "523a43c1be4e8c520b2a55b9832740c62b0077cdd0330dd374cae5ad05088f49",
    "electrical-switchboard-designer.md": "68fe7fc6958a89c3a18e4090aae13e7532770b14c4e7e29ac8971ea481f5f773",
    "expediting-coordinator.md": "472a5903cc9bf0216c0ceccff095dd7dfdbff6fdc471c2d158a9e4b08db2c491",
    "handover-documentation-specialist.md": "c31be3337349bbaa4bf2e0d27cfdd3d2f7e2dd188fa498336ea28e8887f902ed",
    "hse-officer.md": "8ab9960784c4bd293bcbbe8553547236555bb5f0746ab4d3aee6b07c1f2db493",
    "interface-manager.md": "032fea163e50d5f809e025def0eab4782ab8eb51c9aa4118c789abf70f4c63e3",
    "lead-technical-coordinator.md": "bf859097fa8760c31d6ec05dea111f51499942b3aa3e4b53c3ad495e2546a8a4",
    "materials-management-agent.md": "b880a2c7b963be33f964be94b979988acafa3fa990ca72e6d3996958e5752352",
    "portfolio-manager.md": "73c3aa68090a039d92835bafa79858a07f361a9acfe61af65a0922eaa494a6a2",
    "procurement-buyer-agent.md": "51b275aec346e60b12364908eab4da9147eb18c1efe3dfb1bac09321875a0fe9",
    "program-manager.md": "b9515648853266a7ee95c4bd8e49081fadb2228f32b329fbb383fb48f21c6fe7",
    "project-controls-planner.md": "6b432bfde1d44cee23dec180c5f85c75843a954ae7b9d8aaf755591c750470da",
    "project-manager.md": "b6d6933142987c6d4a420eab0bb22e98fa7dae41148f3deb8379e63fb9e8f7e1",
    "qa-qc-engineer.md": "8cb4a3b271902ed52ded28957aa63493d2b187ab586eaae15fd356e0d881a042",
    "senior-civil-engineer.md": "ca23910c492ed5f51dafcabe188759981ca3311b7a1165160d006ae48f810b95",
    "senior-electrical-engineer.md": "5be869d3550fc3f67eeb3a3e3615c690d00c58f713a5b060700d41c2bd644e09",
    "senior-fire-protection-engineer.md": "ffefd0567df2113057c9959a3720c0fff03f9296cbae4d09f9dc8a6fb4403e93",
    "senior-hvac-engineer.md": "fb426749652acf3ad4b327ca7134d056a87431c279fcacd976924f6039af48cf",
    "senior-instrumentation-control-engineer.md": "d093b12ff4eea00bf6bbc5d40ca54400f07c6377009dcc742287047069ff1307",
    "senior-mechanical-engineer.md": "2a0bf48ad65b9ef37732c559769caa1e9ded673a9995f79acd495079e0b1cad3",
    "senior-piping-plumbing-engineer.md": "7ced351dcdc62559adc5fba3d31705b02abbba957c9f244479a67474f2f1b6aa",
    "senior-telecommunications-engineer.md": "84ac6e36b6e7918dff35c678390fec760c11ee39cad97b5226b3ffc9699f25b9",
    "site-construction-manager.md": "69f96705063af0161857319df9ce11d6f5ca1e1dfef0fb5bf806e9e30b35e076",
    "technical-auditor.md": "1b1b72698388227365bf6ca348340699a43747494a54c455473f7666b506ec8f",
    "technical-reviewer.md": "9b180d7f271cf11ea9453bfa42ba2225c01d57ea43d7048fed2c101d0a44a648",
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
        self.assertEqual(len(found), 43)
        self.assertEqual(found, LEGACY_SHA256)


if __name__ == "__main__":
    unittest.main()
