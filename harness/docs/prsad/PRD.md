# PRD — Autonomous EPC Platform (`epc-autonomous-platform`)

Version 0.4 · 2026-11-11 · Status: **reconstructed, pending owner review**

> **Nota para el dueño.** Este documento reconstruye el PRD v0.3 que pegaste en el chat (el texto original no quedó guardado) y le suma lo que decidiste después: adopción gradual (M1), web en pausa (M2), Fase 1 solo BT (M3), orden estructura → código → valores de norma (M4), nombres en inglés para todo lo nuevo (M7), D1–D28 y el loop sin detenciones (M10). Mantiene la numeración de secciones que usan el plan y el loop (§5, §10.2, §10.3, §12, §13, §14.1, §18–§19, §21, §24). Lo que no recordaba con exactitud quedó como propuesta y está listado en §24.

---

## 1. Purpose

Build a platform where an electrical engineer gives the input data of a project (architecture plans, loads, client requirements, meeting minutes) and receives real, standards-based engineering: calculations, studies, single-line diagrams, plans, lists, calculation report and technical specification. Claude orchestrates; deterministic engines calculate and draw; independent checks verify; the engineer reviews only the final deliverables and either approves them or writes corrections, which are applied and re-verified.

## 2. Problem

Today the engineering of an LV installation takes days of repetitive calculation, cross-checking and drafting. Errors appear in the interfaces between documents (a cable in the SLD that differs from the cable list, a breaker that does not match the calculation). Generic AI tools write numbers by hand and cannot be trusted for signed engineering.

## 3. Goals and non-goals

### Goals

1. Produce a complete, consistent **draft** LV package for a project from structured inputs, unattended.
2. Every number comes from an engine, never from a model, and is traceable to its inputs, engine version and norm record.
3. Every deliverable carries a manifest; nothing is "approved for construction" while any norm value it uses is unreviewed (D21).
4. Same inputs, same outputs: reproducible by hash.
5. The engineer's corrections become data changes; only affected stages run again.

### Non-goals (Phase 1)

- Medium voltage, lighting design, HVAC, BIM, fabrication, field and commissioning (planned, later phases).
- The web application (paused, M2). The harness around the model is the product of Phase 1.
- Replacing the engineer of record: the platform drafts, the engineer signs.

## 4. Users

| User | Needs |
| --- | --- |
| Engineer of record (owner) | Give inputs once, review final deliverables, approve or correct, sign. |
| Reviewing engineer | See findings, assumptions, unreviewed values, and the difference between revisions. |
| Procurement | Bills of quantities, datasheets and RFQ derived from the same data. |
| Client | Issued packages with transmittal and revision history. |

## 5. Roles and responsibilities (RACI base)

| Activity | Engineer of record | Reviewing engineer | `orchestrator` | `electrical_lv` | `calc_check` | `documentation` | `procurement` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Project profile and inputs | A | C | R | C | I | I | I |
| Design criteria (design basis) | A | C | R | R | C | I | I |
| Calculations (through engines) | A | I | C | R | C | I | I |
| Deterministic verification | I | I | C | I | R/A | I | I |
| Drawings and documents | A | C | C | C | C | R | I |
| Lists, BOQ, datasheets, RFQ | A | I | C | C | C | C | R |
| Norm values review | **R/A** | C | I | I | I | I | I |
| Approval and signature | **R/A** | C | I | I | I | I | I |
| Issue and transmittal | A | I | R | I | I | C | I |

R = responsible, A = accountable, C = consulted, I = informed. Detail per organization: open decision (§24).

**Segregation of duties:** the agent that produces a result never verifies it; `calc_check` runs deterministic checks first and reports with the finding schema; only a person approves norm values or signs.

## 6. Principles

1. **Engines calculate, models orchestrate.** No agent writes a number by hand.
2. **One source of truth** per datum (ADR-0012). Norm values live in one place and are read through one loader.
3. **Disciplines contain no calculation and no drawing**; they sequence engines.
4. **Inputs are immutable** once accepted; every change is a new revision.
5. **Every deliverable has a manifest** (§13).
6. **Draft by default** (D21): unreviewed norm values block construction status.
7. **Reproducibility:** same inputs, engine versions and norm profile give the same hashes.
8. **Hard rules in code**, not in prompts: permissions, hooks and architecture tests (§14.4).
9. **A folder is documented as existing only if it has tests.** Every node carries a status: `implemented`, `in development`, `planned`.
10. **Copyrighted standards are never versioned**; only extracted values with their clause references are.
11. **Language:** product content and code in English, user interface i18n `es`/`en`; explanations to the owner in Spanish. Existing Spanish names stay until migrated (M7).

## 7. Scope by phase

| Phase | Scope | Exit criterion |
| --- | --- | --- |
| 1 | LV electrical (`electrical_lv`), 16-stage pipeline, draft package, manifests, spike on the 309 kVA golden project | Spike §21 passed |
| 2 | MV, lighting and receptacle layouts in plans, MLD, review and sign-off flow for IFA/IFC | To be defined |
| 3 | Other disciplines (HVAC, BIM, fabrication, procurement execution, field, commissioning) | To be defined |

## 8. Normative profile

Argentina, AEA 90364 and IRAM. One revision per part:

| Part | Revision |
| --- | --- |
| 90364-7-771 | 2006 |
| 90364-7-770 | 2017 |
| 90364-7-701 | 2012 |
| 90364-7-722 | 2018 |
| Parts 4 and 5 (scanned) | to be confirmed by the owner |

Every value used by an engine is a norm-register record: value, unit, clause, revision, `review_status` (`pending review`, `verified`, `conflict`). Profiles are selected per project in `project_profile.json`.

## 9. Architecture overview

```
engineer ──> intake ──> project_profile.json + inputs/ (immutable)
                              │
                     electrical_lv pipeline (16 stages, §12)
                              │ calls
              engines (calculation · validation · cad · quality)
                              │ reads
                 config/normative (one loader)  ·  catalogs
                              │ writes (pipeline only)
                  ssot/ ──> deliverables/ + manifests ──> review ──> issue
```

Claude layer (`harness/.claude/`): five agents, skills, hooks and settings. Platform (`harness/src/platform/`): workflow, permissions, audit, event log, MCP server and CLI over the pipeline.

## 10. Repository structure

### 10.1 Two roots

- `harness/` — the generation platform (versioned).
- `projects/` — one folder per project (never versioned in the platform repository; each project may have its own repository).

### 10.2 `harness/`

```
harness/
├── CLAUDE.md                       # ≤ 200 lines (§14.1)
├── .claude/
│   ├── agents/                     # generated from the roster
│   ├── skills/
│   ├── hooks/
│   └── settings.json               # deny rules for ssot/ and deliverables/
├── docs/
│   ├── prsad/                      # PRD, architecture, decisions (ADR)
│   ├── governance/                 # RACI, approvals, segregation of duties, change policy
│   ├── guides/
│   └── validation/                 # norm verification worksheet, spike reports
├── roadmap/                        # one file per phase, with exit criteria
├── schemas/                        # JSON schemas: profile, state, manifest, finding, inputs
├── catalogs/                       # cables, breakers, transformers, enclosures (manufacturer data)
├── config/
│   ├── normative/AR/               # norm tables and constants + norm register (one loader)
│   └── pmo/                        # templates, codes, document numbering
├── knowledge/
│   └── normative/                  # standards PDFs: local only, ignored, read-only
├── src/
│   ├── engines/
│   │   ├── calculation/            # load_balance, transformer_sizing, short_circuit, selectivity,
│   │   │                           # grounding, voltage_drop, feeder_sizing, (lighting, receptacles, hvac)
│   │   ├── validation/             # rules, standards checks
│   │   ├── cad/                    # sld, mld, plan, drawing, dxf, symbols, titleblock, arch
│   │   ├── quality/                # documents, report and specification builders
│   │   ├── procurement/            # BOQ, datasheets, RFQ            (planned)
│   │   ├── bim/                    # (planned)
│   │   ├── fabrication/            # (planned)
│   │   ├── field/                  # (planned)
│   │   ├── commissioning/          # (planned)
│   │   ├── cost/                   # (planned)
│   │   ├── contracts/              # (planned)
│   │   ├── risk/                   # (planned)
│   │   ├── hse/                    # (planned)
│   │   └── pmo/                    # (planned)
│   ├── disciplines/
│   │   ├── electrical_lv/
│   │   │   ├── intake/
│   │   │   ├── requirements/
│   │   │   ├── stages/
│   │   │   ├── rules/
│   │   │   └── pipeline.py
│   │   └── electrical_mv/          # (planned, Phase 2)
│   └── platform/
│       ├── workflow/
│       ├── permissions/
│       ├── audit/
│       ├── events/
│       ├── mcp/                    # MCP server over the pipeline
│       └── cli/                    # `epc` command
└── tests/
    ├── unit/
    ├── integration/
    ├── architecture/               # import rules, tree, permissions
    ├── golden_projects/            # synthetic projects + 309kva_logistics_center
    └── qa_gates/
```

### 10.3 `projects/<code>/`

```
projects/<code>/
├── project_profile.json            # client, site, supply, normative profile, criteria, language
├── master_project_state.json       # stage status, revisions, open findings (pipeline writes it)
├── epc-progress.txt                # human-readable progress log
├── inputs/                         # immutable after intake; hashed
│   ├── plans/
│   ├── loads/
│   ├── requirements/
│   └── minutes/
├── ssot/                           # project data written only by the pipeline
├── runs/<pipeline_run_id>/         # intermediate results, logs (ignored)
├── deliverables/<rev>/             # issued files + one manifest per deliverable
├── reviews/                        # engineer corrections and findings
├── transmittals/
└── audit/                          # append-only event log
```

## 11. Inputs

- Architecture plans (DXF/DWG preferred; image or PDF accepted with lower confidence).
- Load list or load selection by area (lighting, receptacles, motors, special loads).
- Client requirements and meeting minutes (text).
- Supply data (utility, transformer or LV supply, earthing system TT/TN).
- Intake is a guided form (`/init`), not JSON; the engineer confirms a summary before the pipeline runs.

## 12. `electrical_lv` pipeline — 16 stages

| # | Stage | Engine(s) | Phase 1 status |
| --- | --- | --- | --- |
| 1 | Intake: profile, inputs, hashes | platform | in development |
| 2 | Requirements and design basis (criteria, profile, assumptions) | quality (design basis) | planned |
| 3 | Input verification (plans vs loads vs requirements) | cad/plan, validation | in development |
| 4 | Load schedule and phase balance | calculation/load_balance | implemented (inside aea90364) |
| 5 | Demand and simultaneity (771.9) | calculation/load_balance | implemented |
| 6 | Supply and transformer sizing | calculation/transformer_sizing | planned |
| 7 | Board structure and circuit assignment | calculation, validation | implemented |
| 8 | Feeder and circuit sizing (Ib ≤ In ≤ Iz, I2 ≤ 1.45 Iz, installation method) | calculation/feeder_sizing | implemented |
| 9 | Voltage drop, accumulated (D17) | calculation/voltage_drop | implemented |
| 10 | Short-circuit currents (max/min) | calculation/short_circuit | implemented |
| 11 | Protection and selectivity; thermal withstand k²S² | calculation/selectivity | implemented |
| 12 | Earthing and fault protection (TT: Ra; TN: Zs = c_min·U0/Ia; disconnection times) | calculation/grounding | implemented |
| 13 | Deterministic verification (`calc_check`): recalculation, format, cross-document consistency | validation | in development |
| 14 | Drawings: SLD, board layouts | cad | implemented (SLD) |
| 15 | Documents and lists: calculation report, specification, cable list, terminal-block list, BOQ, datasheets, RFQ, descriptive report | quality, procurement | in part |
| 16 | Package issue: manifests, review status, transmittal | platform | planned |

A stage without an engine returns an explicit "not available in Phase 1" result, never a placeholder value.

## 13. Deliverable manifest

One JSON per deliverable, next to it:

| Field | Content |
| --- | --- |
| `deliverable_id`, `title`, `revision` | identification (PMO numbering) |
| `pipeline_run_id` | run that produced it |
| `inputs` | path and SHA-256 of every input used |
| `engines` | name and version of every engine called |
| `normative_profile` | parts and revisions; list of norm records used with their `review_status` |
| `output_sha256` | hash of the file |
| `findings` | open findings (finding schema) |
| `review_status` | `draft`, `for_review`, `approved_for_construction` (blocked while any norm record is unreviewed, D21) |
| `signed` | signer, date, or null |
| `supersedes` / `superseded_by` | regeneration marks previous signatures `superseded` |

## 14. Claude layer

### 14.1 `CLAUDE.md`

At most 200 lines: purpose, owner rules (no git writes by Claude, no deletes, no `local/`, no norm value approval, frozen decisions), where SSOT, deliverables and manifests live, language rule, how to run the pipeline. Details live in skills and docs, not in `CLAUDE.md`.

### 14.2 Agents

| Agent | Role | Model |
| --- | --- | --- |
| `orchestrator` | Runs the pipeline, routes work, writes progress, never calculates | `claude-sonnet-5-5` |
| `electrical_lv` | Interprets inputs and criteria, calls engines through MCP/CLI | `claude-sonnet-5-5` |
| `calc_check` | Deterministic checks first; judgment review second; consolidates findings | `claude-sonnet-5-5` |
| `documentation` | Builds documents and drawings from SSOT through engines | `claude-sonnet-5-5` |
| `procurement` | Lists, BOQ, datasheets, RFQ from SSOT | `claude-sonnet-5-5` |

Model, effort, tools, skills and turn limit come from one roster file; agent frontmatter is generated from it.

### 14.3 Skills

One skill per repeated procedure (intake form, design basis, calculation report, specification, SLD, lists). Skills never contain norm values; they call engines.

### 14.4 Hard rules in code

- `settings.json` deny rules and hooks: agents cannot edit `ssot/`, `deliverables/`, `inputs/`, `config/normative/`.
- `CODEOWNERS` for normative data, schemas and the platform.
- Architecture tests: no imports between disciplines; disciplines import engines, never the reverse; nothing imports the parked web application.

### 14.5 Tool interface

MCP server and `epc` CLI expose the same functions (init, run, status, review, issue, engine queries). Parity is tested.

## 15. Review loop

The engineer reviews the issued draft with a one-page summary (assumptions, findings, unreviewed norm values, cost). Written corrections become data changes in `reviews/`; the pipeline re-runs only the affected stages and issues the next revision with a difference report.

## 16. Quality gates

Unit, integration, architecture and golden-project tests; complexity and coverage floors; norm-register check; reference-case comparison; reproducibility test. Golden results are regenerated once, officially, after the norm values are verified (D27).

## 17. Security and confidentiality

Client data only under `projects/`, never in the platform repository. Standards' PDFs local and read-only. Credentials outside the repository. Audit log append-only.

## 18. Current state (as of 2026-11-11)

- Engines exist and are tested for LV calculation (`epc_aea90364`), SLD, symbols, title blocks, DXF, plans, lighting, receptacles, HVAC, rules, standards, documents.
- Norm register: 289 records, 318 points pending review; reference cases 36 agree, 8 differ, 11 without official value.
- A web application (backend, frontend, database, infra) exists and is paused (M2).
- A Claude layer exists (plugins, skills, agents, an MCP server in development) and an unattended loop with guard hook and file snapshots.

## 19. Gaps and corrections to the earlier diagnosis

- Duplicate calculation tools were already consolidated into the engines; old copies remain only under `local/legacy` (to archive).
- `.claude/harness-backups` exists because Claude does not write to git; it is replaced by tags in the new repository (D7).
- Missing: discipline pipeline, SSOT files, manifests, platform workflow and permissions, five-agent roster, several Phase 1 engines (transformer sizing, terminal blocks, BOQ, datasheets, RFQ, design basis, descriptive report).

## 20. Migration

Gradual adoption of this structure (M1), following `docs/harness/MIGRATION_PLAN.md`: clean starting point, skeleton, relocation without behaviour change, code, then norm values and validation. Executed unattended by the migration loop (M10).

## 21. Spike — Phase 1 acceptance

Run on the golden project `309kva_logistics_center`. All ten criteria must pass:

1. The pipeline runs from `project_profile.json` to `deliverables/` with no manual edit.
2. Calculation results are within the owner's tolerances of independently calculated reference values.
3. Every number in every deliverable is traceable to an engine call and its norm records.
4. Quantities in lists and BOQ are within the owner's tolerances of the reference.
5. Two runs with the same inputs give the same output hashes.
6. Every error seeded in a test copy of the inputs is caught by `calc_check` or a gate.
7. Unreviewed norm values are listed and block `approved_for_construction`.
8. Agents cannot write `ssot/`, `deliverables/` or `inputs/` directly (permission tests).
9. Cost and time per run are recorded per agent and stay within the targets set by the owner.
10. A correction re-runs only the affected stages and marks previous signatures `superseded`.

## 22. Metrics

Time from inputs to draft package; findings per package and per stage; share of norm records verified; cost per run and per agent; reproducibility rate; revisions until approval.

## 23. Risks

| Risk | Mitigation |
| --- | --- |
| Wrong norm values in drafts | D21 draft status; norm register; owner verification before IFC |
| Model writes numbers | Engines only; `calc_check` recalculates; hooks |
| Plan reading errors | Input verification stage; confidence levels; engineer confirms summary |
| Cost of agent runs | One model tier (Sonnet), cost ledger, per-run budgets |
| Migration breaks behaviour | Reference snapshot, zero-difference tranches, rollback |

## 24. Open decisions (owner)

1. Organization name and identity for deliverables.
2. RACI detail per organization (§5).
3. Revision of parts 4 and 5 in the normative profile (§8).
4. Tolerances for spike criteria 2 and 4, and cost and time targets for criterion 9 (§21).
5. Scope and exit criteria of Phases 2 and 3 (§7).
6. **Review of this reconstruction against the original v0.3**: anything missing or different from what was intended.
