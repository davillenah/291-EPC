# Repository layout

What lives where today. The older target tree (separate `frontend/`, `backend/`, `engine/`, `management/`) was folded into `harness/`; this page replaces it. The generated dependency map is `DEPENDENCIAS.md`.

```
EPC-291/
├─ README.md  README.es.md  CHANGELOG.md  CONTRIBUTING.md  CLAUDE.md  LICENSE  requirements*.txt
├─ .github/workflows/            CI (the test battery runs the gate)
├─ assets/  dist/                images and built plugin packages (generated)
├─ projects/_template/           the project skeleton every project starts from
├─ tmp/                          simulations (git-ignored, never committed)
└─ harness/
   ├─ CLAUDE.md                  main guide (owner rules, numbers, how to verify)
   ├─ src/
   │  ├─ engines/<group>/<engine>/    one pure-Python package per engine: pyproject.toml, README.md, src/epc_<engine>/, tests/
   │  │     bim · cad · calculation · fabrication · geometry · procurement · quality · validation   (groups with engines)
   │  │     commissioning · contracts · cost · field · hse · pmo · risk                           (planned, README only)
   │  ├─ disciplines/            one folder per discipline (electrical_lv is the first full pipeline)
   │  └─ platform/               epc_platform (api, cli, audit, events, permissions, workflow) and the MCP server
   ├─ .claude/                   the Claude layer: agents, skills, plugins, hooks, prompts, marketplace, rosters
   ├─ config/                    normative data, PMO methodologies and templates, DXF and i18n settings
   ├─ knowledge/                 diagram knowledge and normative knowledge (data, not code)
   ├─ schemas/                   JSON schemas and catalogues shared by engines and tools
   ├─ catalogs/                  manufacturer catalogues
   ├─ tools/                     build, ci (the gate), dev, hooks, landing
   ├─ tests/                     architecture, unit, integration, characterization, golden_projects, qa_gates, evals
   ├─ docs/                      ADRs and guides, BACKLOG.md (the only place for pending work), NAMING.md, generated maps
   └─ roadmap/                   planning
```

Rules that keep it tidy:
- One engine, one folder; engines import each other only through their `api.py` (architecture test).
- One source of truth per datum (ADR-0012); generated files are never edited by hand (`python harness/tools/build/regen_all.py`).
- File and folder names follow `harness/docs/NAMING.md`.
- Standards PDFs, `local/` and `tmp/` are never versioned.

Open structure decisions (owner): flatten `engines/<group>/<engine>/src/epc_<engine>/` to one level less, and fold the seven planned groups into the roadmap (the PRD tree test, `harness/tests/architecture/expected_tree.json`, lists them today).
