# _bodies

Status: **implemented**

The hand-written text of the five product agents (`orchestrator`, `electrical_lv`, `calc_check`, `documentation`, `procurement`), one `<name>.md` each, in English, without front matter. `python harness/tools/build/regen_agents.py` puts the front matter from `../../roster.json` in front of each body and writes `../<name>.md`. Edit the body here; never edit the generated file. Every body must contain the rule "never write a number by hand" (tested).
