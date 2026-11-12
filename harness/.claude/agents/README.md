# agents

Status: **in development**

Specialist agents (Markdown with front matter) referenced by the plugins in `../plugins/`. The five product agents (`orchestrator`, `electrical_lv`, `calc_check`, `documentation`, `procurement`) are GENERATED from `../roster.json` and the bodies in `_bodies/` by `python harness/tools/build/regen_agents.py` (`--check` in the gate, check `agents`); do not edit them by hand. The other agent files here are the older specialist agents; they are the source of themselves and are not generated (a test pins their hashes).
