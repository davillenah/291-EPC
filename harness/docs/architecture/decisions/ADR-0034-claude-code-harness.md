# ADR-0034: Claude Code harness (the platform driven from Claude Code)

Status: accepted. Date: 2026-11-10. Detail: `docs/harness/SPEC.md` (§1–§3, §6); goal and protocol: `docs/harness/GOAL.md`, `docs/harness/LOOP.md`.

## Context
The platform is driven today through the web UI and the backend. The owner wants the same work done end to end from Claude Code: a short form, seven fixed stages, independent verification and a draft package, with every number coming from the engines and never from a model.

## Decisions
1. **Four commands as skills**: `/init` (form and confirmed summary), `/run` (seven stages), `/review` (corrections to data changes and partial re-run), `/approve` (IFA or IFC issue). The main session is the orchestrator.
2. **One tool interface with one core**: MCP server `epc` (stdio) and `python -m epc_cli`, both calling the backend `public.py` functions in process. A gate check `mcp-parity` compares their files with the web path.
3. **Numbers only from engines.** Agents call tools; they never compute, copy or round an engineering value.
4. **Code before models.** Format, recalculation and cross-document checks are code (`checks_run`). Five agents handle judgment: `plan-reader`, `electrical-designer`, `spec-writer`, `input-verifier`, `standards-reviewer`. Producers and verifiers are separate, and verifiers are read-only.
5. **One roster file**: `claude/harness/roster.json` is the only source of each agent's model, effort, tools, skills and turn limit; the agent frontmatter is generated from it and a gate check `roster` fails on any difference. Every agent uses `claude-sonnet-5-5`; an optional final audit before IFC is off.
6. **State is files in the project folder** (`workspace/`, `deliverables/`, `.epc/`), so a run can be resumed and audited. The ledger records model, effort and tokens per stage.
7. **Existing Spanish names stay.** No English migration of existing code, keys or files. New code follows the language rule in `CLAUDE.md`.
8. **No git writes by the loop that builds the harness** (owner rule, 2026-11-09). Undo is by file snapshots (`tools/harness/snapshot.py`). This overrides the branching and merge rules of `CLAUDE.md` for that work only.

## Consequences
- New packages: `claude/mcp/epc`, `epc_cli`, `epc_checks`, plugin `epc-harness`; new gate checks `mcp-parity` and `roster`.
- The 12 electrical specialist agents become `check-*` skills; the non-electrical agents move to `_on-hold`.
- Unreviewed norm values stay unreviewed and are reported in every package.
- Cost is estimated at about 7 USD per 100-circuit project with one review round; the ledger gives the real figure.
