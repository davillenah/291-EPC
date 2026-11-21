# agents

Status: **in development**

Specialist agents (Markdown with front matter) referenced by the plugins in `../plugins/`. The five product agents (`orchestrator`, `electrical_lv`, `calc_check`, `documentation`, `procurement`) are GENERATED from `../roster.json` and the bodies in `_bodies/` by `python harness/tools/build/regen_agents.py` (`--check` in the gate, check `agents`); do not edit them by hand. The other agent files here are the older ones that are still used: `document-writer` (called by the `generate-specification` skill) and the seven `senior-*-engineer` reviewers that the reserve discipline leads in `disciplines/` name. They are the source of themselves and are not generated (a test pins their hashes). The unused legacy agents were removed on 2026-11-21 (owner decision, roles map in `docs/prsad/ROLES-single-responsibility.md`).

`specialists/` holds the agents added after the legacy set (one `.md` per agent, hand-written, front matter with `tools` and `skills`): `freecad-modeler` (editable FreeCAD model of what the engines designed; uses the `freecad` skill and the `freecad` MCP server of the repository `.mcp.json`). A new agent goes here, never in the top folder, which a test pins.
