# docs

Status: **implemented**

| File | Content |
|---|---|
| [explanation/knowledge.md](explanation/knowledge.md) | How a standard becomes engine knowledge: private sources, extracted rules that ship, Python execution |
| [explanation/what-is-epc.md](explanation/what-is-epc.md) | What an EPC is: lifecycle, artifacts, roles and what they imply for the software |
| [architecture/](architecture/README.md) | Target architecture, full folder tree, migration phases, ADRs ([decisions/](architecture/decisions/README.md)) |
| [BRANCHING.md](BRANCHING.md) | Branching policy: main (stable), dev (integration), feature/fix/chore branches |
| [DEPENDENCIES.md](DEPENDENCIES.md) | Python packages, system tools, plugin graph, known runtime notes |
| [USER_DATA_MODEL.md](USER_DATA_MODEL.md) | Files that feed the end-user app and the customer-input pipeline |

Per-module documentation stays next to the code: `harness/.claude/plugins/<plugin>/README.md`, `harness/.claude/skills/README.md`, `parked/web/backend/README.md`, `parked/web/frontend/README.md`, `parked/web/database/README.md`, `parked/web/infra/README.md`, `harness/tools/README.md`.
