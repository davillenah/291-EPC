# claude

Status: **implemented**

The AI layer of EPC-291: everything that is packaged for Claude. Engineering code lives in `engine/`; plugins then become thin wrappers.

| Folder | Content |
|---|---|
| [plugins/](plugins/README.md) | One folder per plugin: our `plugin.json`, code and data. `registry.json` is generated |
| [skills/](skills/README.md) | All skills (`<id>/SKILL.md`). Plugins govern them |
| [roster.json](roster.json) | The one place for model, effort, tools, skills and turn limit of the five product agents (schema `harness/schemas/roster.schema.json`) |
| [agents/](agents/README.md) | Specialist agents (Markdown with front matter) referenced by plugins |
| [marketplace/](marketplace/README.md) | Template for the marketplace that ships these plugins |
| [`../src/platform/mcp/`](../src/platform/mcp/README.md) | The EPC MCP server (package `epc_mcp`, with its tests) |
| [settings.json](settings.json), [hooks/](hooks/README.md) | Deny rules and the `guard_paths.py` PreToolUse hook that apply the permission matrix (PRD 14.4) |
| [prompts/](prompts/README.md) | Reusable prompts and style rules (planned) |
| [`../tests/evals/`](../tests/evals/README.md) | Evaluation cases per skill (planned) |

## Build and validate
```
.venv\Scripts\python harness\tools\build\epc_build.py registry      # plugins + skills + agents consistency
.venv\Scripts\python harness\tools\build\epc_build.py marketplace   # dist/marketplace (git-ignored build output)
claude plugin validate --strict dist\marketplace
```
`python harness/tools/ci/run_gate.py` runs all of it, including the official validator on the marketplace and on every plugin.

## Rules
1. Plugins govern skills; a skill defined twice is a warning in development and an error in production builds.
2. Plugin names are kebab-case and must not start with `claude-` or `anthropic-` (reserved).
3. Nothing from `local/` and no PDF/DWG is ever packaged.
4. The end-user app never exposes this layer; it exists for the admin role and for developers.
