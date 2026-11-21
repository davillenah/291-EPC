#!/usr/bin/env python3
"""Generate the five product agents (PRD 14.2) from the roster and their hand-written bodies (stdlib only).

  python harness/tools/build/regen_agents.py            write harness/.claude/agents/<name>.md for every agent of the roster
  python harness/tools/build/regen_agents.py --check    exit 1 if any agent file differs from what would be generated (the gate runs this)

Single source (ADR-0012): model, effort, tools, skills and turn limit live ONLY in harness/.claude/roster.json. The text of each agent lives in
harness/.claude/agents/_bodies/<name>.md. The generated file is: front matter (name, description, tools, model, effort, maxTurns, skills),
a header comment, the body and the summary rules of the roster. Output is deterministic: LF line ends, one trailing newline.
`--claude-dir DIR` points the tool at another copy of the `.claude` folder (the tests use it on a temporary copy).
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLAUDE = REPO / "harness" / ".claude"
NAMES = ("orchestrator", "electrical_lv", "calc_check", "documentation", "procurement")
HEADER = "<!-- GENERATED FROM harness/.claude/roster.json BY harness/tools/build/regen_agents.py - do not edit by hand -->"
REQUIRED = ("name", "role", "model", "effort", "tools", "skills", "max_turns", "summary_prompt_rules")


class RosterError(Exception):
    """The roster or a body is unusable; the message says what to fix."""


def load_roster(claude_dir, filename="roster.json", names_expected=None):
    """The agents of a roster file as a list of dicts (checked for the keys the generator needs and for the fixed names)."""
    names_expected = NAMES if names_expected is None else names_expected
    path = Path(claude_dir) / filename
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RosterError(f"cannot read {path}: {exc}") from exc
    agents = data.get("agents", [])
    for agent in agents:
        missing = [k for k in REQUIRED if k not in agent]
        if missing:
            raise RosterError(f"agent {agent.get('name')!r}: missing {missing}")
    names = tuple(a["name"] for a in agents)
    if sorted(names) != sorted(names_expected):
        raise RosterError(f"the roster must name exactly {list(names_expected)}, found {list(names)}")
    return agents


DISCIPLINES_ROSTER = "roster.disciplines.json"
DISCIPLINE_NAMES = ("civil_structural_lead", "mechanical_lead", "hvac_lead", "piping_plumbing_lead",
                    "fire_protection_lead", "instrumentation_control_lead", "telecommunications_lead")


def read_body(claude_dir, name, group=""):
    path = Path(claude_dir) / "agents" / "_bodies" / group / f"{name}.md"
    try:
        return path.read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
    except OSError as exc:
        raise RosterError(f"body of {name} not found: {path}") from exc


def front_matter(agent):
    lines = ["---", f"name: {agent['name']}", f"description: {agent['role']}", f"tools: {', '.join(agent['tools'])}",
             f"model: {agent['model']}", f"effort: {agent['effort']}", f"maxTurns: {agent['max_turns']}"]
    if agent["skills"]:
        lines += ["skills:"] + [f"  - {s}" for s in agent["skills"]]
    return lines + ["---"]


def rules_section(agent):
    return ["## Summary rules (generated)", ""] + [f"- {r}" for r in agent["summary_prompt_rules"]]


def render(agent, body):
    """The full text of one agent file."""
    parts = ["\n".join(front_matter(agent)), HEADER, body, "\n".join(rules_section(agent))]
    return "\n\n".join(parts) + "\n"


def expected(claude_dir):
    """{path of the agent file: text} for every agent of the roster."""
    out = {Path(claude_dir) / "agents" / f"{a['name']}.md": render(a, read_body(claude_dir, a["name"])) for a in load_roster(claude_dir)}
    if (Path(claude_dir) / DISCIPLINES_ROSTER).is_file():  # second roster: orchestration and discipline leads (planned), generated into agents/disciplines/
        for a in load_roster(claude_dir, DISCIPLINES_ROSTER, DISCIPLINE_NAMES):
            out[Path(claude_dir) / "agents" / "disciplines" / f"{a['name']}.md"] = render(a, read_body(claude_dir, a["name"], "disciplines"))
    return out


def current(path):
    try:
        return path.read_bytes().decode("utf-8")
    except OSError:
        return None


def check(claude_dir):
    """The files that differ from what the roster generates (missing files included), as readable lines."""
    return [f"{p.name}: {'missing' if current(p) is None else 'differs from the roster'}" for p, text in expected(claude_dir).items() if current(p) != text]


def write(claude_dir):
    done = []
    for path, text in expected(claude_dir).items():
        if current(path) != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))
            done.append(path.name)
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if an agent file is not what the roster generates")
    ap.add_argument("--claude-dir", default=str(CLAUDE), help="the .claude folder to read and write (default harness/.claude)")
    a = ap.parse_args(argv)
    try:
        if a.check:
            problems = check(a.claude_dir)
            for line in problems:
                print("ERROR:", line + " (run python harness/tools/build/regen_agents.py)")
            print(f"agents: {len(NAMES)} agents, {len(problems)} out of date")
            return 1 if problems else 0
        done = write(a.claude_dir)
        print(f"agents: {len(NAMES)} agents, rewrote {len(done)}" + (": " + ", ".join(done) if done else ""))
        return 0
    except RosterError as exc:
        print("ERROR:", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
