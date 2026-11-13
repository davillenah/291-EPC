# EPC-291

**A Claude-native harness for multidisciplinary engineering.**
Deterministic engines calculate and draw, Claude agents orchestrate, an independent checker verifies, and the engineer of record reviews and signs.

[Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [License](LICENSE) · [Español](README.es.md) · [Architecture](harness/docs/architecture/README.md) · [Docs](harness/docs/README.md)

---

## Idea

Agents never write a number. Every value comes from an engine (through the `epc` MCP server or the `epc` CLI) and is traceable to its inputs, the engine version and the norm record behind it. The platform follows the Anthropic way of building agents: a `CLAUDE.md` with fixed rules, subagents with their own tools, skills, hooks that enforce the rules in code, and MCP for the tools.

| Layer | Where | What it does |
|---|---|---|
| Rules | `CLAUDE.md`, `harness/CLAUDE.md` | Owner rules and conventions. |
| Agents | `harness/.claude/agents/`, `roster.json`, `roster.disciplines.json` | Orchestrators and discipline leads. Model, effort and tools come from the rosters only. |
| Skills and plugins | `harness/.claude/skills/`, `harness/.claude/plugins/` | Repeatable workflows; never hold norm values. |
| Hooks and permissions | `harness/.claude/hooks/`, `harness/src/platform/epc_platform/permissions/` | Agents cannot write `ssot/`, `deliverables/`, `inputs/` or norm data. |
| Engines | `harness/src/engines/` | Calculation, CAD, validation, quality and procurement engines (Python, standard library first). |
| Disciplines | `harness/src/disciplines/` | One folder per discipline; `electrical_lv` has a 12-stage pipeline, the others are planned. |
| Platform and MCP | `harness/src/platform/` | Single source of truth store, hash-chained event log, manifests, MCP server and CLI. |
| Projects | `projects/<code>/` | Client data. Never versioned here; only `projects/_template` is. |

## Status

- Electrical low voltage (AEA 90364, Argentina): in development, 12-stage pipeline.
- Civil/structural, mechanical, HVAC, piping, fire protection, instrumentation and control, telecommunications: folders, contract and lead agents created; no engines yet.
- Norm values are `pending review` until a person approves them. No deliverable is "approved for construction" while it uses an unreviewed value.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python harness/tools/ci/run_gate.py                  # full check battery
```

## Legal

- Standards, books and other copyrighted material are never versioned (`*.pdf` is ignored; `harness/knowledge/normative/` is local only). Bring your own licensed copies.
- Released under the [MIT License](LICENSE). **Any copy, fork or derivative work must keep the author's name, Daniel A. Villena H., as owner of the original repository.**
- Outputs are aids for a qualified engineer and are not valid for construction until reviewed and signed by the engineer of record.

© 2026 Daniel A. Villena H.
