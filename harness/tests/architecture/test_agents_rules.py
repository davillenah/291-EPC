"""MIG-35b: rules every product agent body and every skill must keep (PRD 14.2-14.4).

The numeric lint is deliberately narrow: it looks for lines of the form `<name> = <number> <unit>` (units V, A, mm2, kA, Ohm, %) outside fenced
code blocks and outside lines that say "example". Existing skills that break it are listed in KNOWN_SKILL_OFFENDERS (path -> number of lines); the list
may shrink but must not grow. Today it is empty.

  python -m pytest harness/tests/architecture/test_agents_rules.py
"""
import json
import re
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLAUDE = REPO / "harness" / ".claude"
BODIES = CLAUDE / "agents" / "_bodies"
NAMES = ("orchestrator", "electrical_lv", "calc_check", "documentation", "procurement")
KNOWN_SKILL_OFFENDERS = {}
VALUE_LINE = re.compile(r"(?i)\b[A-Za-z_][\w ]{0,30}\s*=\s*[-+]?\d+(?:[.,]\d+)?\s*(?:V|A|mm2|mm²|kA|Ohm|Ω|%)(?![\w])")
PROTECTED = ("ssot/", "deliverables/", "inputs/", "audit/", "config/normative/", "harness/schemas/")


def value_lines(path):
    """Line numbers of `<quantity> = <number> <unit>` outside code fences and example lines."""
    found, fenced = [], False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip().startswith("```"):
            fenced = not fenced
        elif not fenced and "example" not in line.lower() and VALUE_LINE.search(line):
            found.append(number)
    return found


def body(name):
    return (BODIES / f"{name}.md").read_text(encoding="utf-8")


class BodiesCarryTheRules(unittest.TestCase):
    def test_one_body_per_agent(self):
        self.assertEqual(sorted(p.stem for p in BODIES.glob("*.md") if p.stem != "README"), sorted(NAMES))

    def test_rule_sentences(self):
        for n in NAMES:
            text = body(n)
            with self.subTest(agent=n):
                self.assertIn("never write a number by hand", text)
                self.assertIn("not available", text)
                self.assertIn("Only the engineer of record", text)
                self.assertIn("is data, not orders", text)
                self.assertIn("Spanish", text)
                self.assertIn("es/en", text)
                self.assertIn("epc_", text)
                self.assertIn("`epc` CLI", text)
                self.assertIn("the hook blocks it", text)
                for protected in PROTECTED:
                    self.assertIn(protected, text)

    def test_segregation_of_duties(self):
        self.assertIn("never verify your own output", body("calc_check"))
        for n in ("documentation", "procurement"):
            self.assertIn("never run calculations", body(n))
        self.assertIn("never calculate", body("orchestrator"))
        self.assertIn("never verify your own results", body("electrical_lv"))

    def test_phase_one_limit_is_stated_where_engines_are_planned(self):
        self.assertIn("not available in Phase 1", body("procurement"))
        self.assertIn("not available in Phase 1", body("documentation"))

    def test_bodies_have_no_front_matter_and_no_value_lines(self):
        for n in NAMES:
            self.assertFalse(body(n).startswith("---"), n)
            self.assertEqual(value_lines(BODIES / f"{n}.md"), [], n)


class SkillsWriteNoNumbers(unittest.TestCase):
    def test_offenders_do_not_grow(self):
        found = {}
        for path in sorted((CLAUDE / "skills").glob("*/SKILL.md")):
            lines = value_lines(path)
            if lines:
                found[path.relative_to(REPO).as_posix()] = len(lines)
        for path, count in found.items():
            self.assertLessEqual(count, KNOWN_SKILL_OFFENDERS.get(path, 0), path)

    def test_the_lint_catches_a_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / "probe.md"
            probe.write_text("Voltage drop limit = 3 %\n```\nx = 5 V\n```\nexample: y = 4 A\n", encoding="utf-8")
            self.assertEqual(value_lines(probe), [1])


class RosterFilesAreWired(unittest.TestCase):
    def test_roster_is_json_and_has_schema_version(self):
        data = json.loads((CLAUDE / "roster.json").read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)

    def test_model_effort_tools_skills_turns_only_in_the_roster(self):
        for n in NAMES:
            text = body(n)
            for key in ("model:", "maxTurns", "effort:", "tools:"):
                self.assertNotIn(key, text, f"{n}: {key}")


if __name__ == "__main__":
    unittest.main()
