# Roles: one duty per role, never duplicated

Status: **proposed** (owner decision 2026-11-21: "each role fulfils a single role and is never duplicated"). Backlog: DGM-15. Inputs: the two research reports (repository roles, engineering practice; unverified web sources). Works with `PRD-diagram-flow.md` and ADR-0024.

## 1. Rule

- One duty has one owner. A duty is a kind of decision or product (for example "decides pass or fail"), not a task.
- A role owns one duty and nothing else. Two roles never produce the same thing.
- A role reads the product of the role above it and never re-derives it (ADR-0012).
- Whoever produces a result never judges it (segregation of duties, already a rule of `calc_check`).
- Only a person approves norm values and signs.

## 2. Role map

| Duty (one per role) | Role | Today | Does not do |
| --- | --- | --- | --- |
| Sequences the work: stages for one discipline, disciplines for the project | `orchestrator`, one entry with a `scope` (`discipline` or `project`) | `orchestrator` and `multidisciplinary_orchestrator` (same tools and rules) | calculate, design, judge |
| Owns the design intent of a discipline: circuit analysis, device lists, cable types without cross-section (flow steps 1 and 3), calls the engines | discipline leader: `electrical_lv` for electrical LV; PV and the others as the same role with a discipline parameter | `electrical_lv`; seven planned `*_lead` placeholders | sequence the run, judge its own result, write documents |
| Calculates | the engines (not an agent) | engines | any decision of design intent |
| Decides pass or fail (flow step 5) | auditor: `calc_check` | `calc_check`, plus legacy `technical-auditor`, `technical-reviewer`, `qa-qc-engineer`, `electrical-drawing-checker` | produce the calculation or the documents |
| Owns the interface register between disciplines (who owns each shared datum, open items) | interface coordinator: a duty of the project-scope `orchestrator` reading the `epc_plan.clash` output | four overlapping definitions: `multidisciplinary_orchestrator`, `lead-technical-coordinator`, `interface-manager`, `bim-clash-detection-coordinator` | detect clashes (the engine does), edit another discipline's data |
| Assembles the single hand-over | `epc_drawing.diagram_assembler` (not an agent) | done | compute |
| Writes documents and specifications from the assembly | `documentation` | `documentation` and the legacy writers `document-writer`, `electrical-spec-writer`, `electrical-report-writer` | read the calculation directly, buy |
| Lists, BOQ, datasheets and quotations from the assembly | `procurement` | `procurement`, plus legacy `procurement-buyer-agent`, `electrical-materials-takeoff` | write specifications |
| Reviews and signs the package | engineer of record (a person) | person | n/a |

## 3. What changes

1. One orchestrator entry with a scope; `multidisciplinary_orchestrator` becomes that scope, not a second agent.
2. `electrical_lv` is the electrical discipline leader and takes flow steps 1 and 3; the other discipline leaders stay `planned` as one parameterized role until an engine exists.
3. `calc_check` is the only pass or fail; the advisory `violations` of the assembler become inputs to its verdict.
4. The interface register is kept by the project-scope orchestrator from `epc_plan.clash`; no other coordinator exists in the flow.
5. `documentation` and `procurement` start from the assembly only.
6. Legacy agents that duplicate a role above leave the flow and are kept as reference. Nothing is deleted: they are replaced through a reviewed change, and a test pins their hashes today, so the change updates that test deliberately and visibly.

## 4. Order of work

1. This map reviewed by the owner (now).
2. (done) Single-owner test: a test that lists every duty and fails when two roster entries own the same one or an entry owns two (no weakening of any other test).
3. (done) Merge the two orchestrators into one entry with a scope (roster, bodies, regenerate agents).
4. Move steps 1 and 3 into `electrical_lv` (skills `design-board`, `diagram-model`), and make `calc_check` the single verdict.
5. Point `documentation` and `procurement` to the assembly.
6. Move the duplicated legacy agents out of the flow, with the hash test updated.

Steps 3 to 6 touch the rosters and generated files, so each goes through its own pull request with the gate and CI green. The product agents' model, effort, tools and skills still come only from `roster.json` and `roster.disciplines.json`.

## 5. Open points

- Whether the interface register lives in the orchestrator body or in its own data file owned by the coordination module (ADR-0024).
- The generated header of `agents/disciplines/multidisciplinary_orchestrator.md` names `roster.json`, not `roster.disciplines.json`; check the generator (unverified).
- Naming of the discipline parameter for the leader role.
