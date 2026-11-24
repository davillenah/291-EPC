# Backlog maestro de EPC-291

Única fuente de los pendientes (ADR-0012): lo que falta, en orden. Los archivos por área (`docs/BACKLOG_*.md`) guardan lo hecho y su contexto.
Actualizado: 2026-11-08.

## Cómo se usa
- Cada tarea tiene un ID estable (`E1-01`, `ILU-05`…) y un estado: `[ ]` pendiente, `[~]` hecho en parte (dice qué falta), `[x]` hecho (con fecha).
- Se trabaja **la primera tarea `[ ]` de «Siguiente»**, salvo que el dueño pida otra cosa. Una tarea por rama (`feat/<id>-<nombre>`), con el gate en verde y merge `--no-ff` a `dev`.
- Al terminar, en el mismo commit: marcar `[x] (AAAA-MM-DD)`, anotar lo que quedó como `[~]` o como un ID nuevo, mover la tarea hecha al historial de su área y correr la cola de «Siguiente».
- Lo que aparezca en el camino se agrega con un ID nuevo al final de su bloque. Un pendiente no se borra sin hacerlo o sin una decisión del dueño (se anota la decisión).
- **En espera:** lo que no es eléctrico está en «En espera / más adelante» y no se trabaja hasta que el dueño lo pida.
- **(Dueño)** marca lo que el programa no puede hacer (aprobar normas, conseguir archivos reales, decidir): se recuerda al dueño, no se ejecuta.

## Siguiente (repo nuevo, 2026-11-13)

- [x] **RUN-01 · Etapa de partida automática** (2026-11-14). `epc run --resume` compara las firmas de las entradas de la última corrida (`runs/<id>/run_inputs.json`) con las nuevas y arranca en la primera etapa que lee algo que cambió (`harness/src/disciplines/electrical_lv/resume.py`); una sección nueva de `engine_inputs` arranca en la etapa 3; cambiar respuestas o lista de cargas se rechaza. La tabla de `GUIA_MOTORES.md` sigue siendo la referencia manual.
- [ ] **(Dueño) NORM-01 · Revisar los valores de norma** con `harness/docs/validation/norm_verification_worksheet.xlsx` y luego pedir la regeneración de los golden (87 casos de `aea90364` y `drawing`), único motivo por el que la CI queda roja.

- [x] **PRB-01 · Lista de cargas inválida por `--loads`** (2026-11-13). La etapa 1 valida con el esquema la lista recibida en memoria; antes una carga con `kind` inválido rompía la etapa 4 con `KeyError`.
- [x] **PRB-02 · La etapa 3 lee el contenido del plano** (2026-11-13). Regla IV-05: un `.dxf` que `epc_arch` no puede leer bloquea la etapa 3 (antes bastaba que el archivo existiera). Otros formatos de plano siguen sin abrirse.
- [x] **MOD-02 · Modo por defecto según la rama** (2026-11-14, ADR-0035). `epc run` sin `--mode` usa `EPC_RUN_MODE` o, si no está, `harness/config/default_run_mode`: `edit` en `dev`, `production` en `main`; un `--mode` explícito siempre gana y un archivo ausente o inválido cae a `production`. La promoción `dev` → `main` es un paso explícito (`harness/tools/build/set_default_run_mode.py production`, procedimiento en `docs/BRANCHING.md`) y el check del gate `default-run-mode` falla si el archivo dice `edit` en `main`, en un release (`EPC_RELEASE=1`) o en el CI de un PR a `main`.
- [x] **MOD-01 · Modos de corrida producción y edición** (2026-11-14, ADR-0035). `epc run --mode production|edit` (API y MCP `mode`). `production` es el comportamiento de siempre (por defecto). En `edit` las normas sin verificar no frenan `approve` ni `issue` (D21 no se aplica mientras todos los manifiestos vigentes sean de edición) y el paquete, el manifiesto, los informes y la carátula dicen «MODO EDICIÓN: valores de norma sin verificar, no para producción»; los registros de norma no se tocan, el manifiesto sigue en `draft` y nada se firma. Falta (dueño): que el roster de agentes incluya `epc_project_submit` y decidir si el DXF debe llevar la marca.
- [x] **PRB-03 · `epc approve` alcanzable por CLI** (2026-11-14). Nuevo `epc submit` (API `submit`, MCP `epc_project_submit`): `draft_ready` → `in_review`; después `epc approve` (ingeniero de registro) y la guarda D21 siguen igual. Falta agregar la herramienta al roster de agentes (`harness/.claude/roster.json`), que es del dueño.
- [ ] **PRB-04 · Cables en paralelo.** Si ninguna sección ≤ 300 mm² cumple, el motor avisa «usar paralelo» pero no lo calcula: deja ΔU 0 e Iz vacío y `calc_check` lo marca. Usar paralelo exige factores de norma sin verificar (pendiente de revisión del dueño).
- [ ] **PRB-05 · Acometidas con `together`.** En la prueba «Aurora Sur» dos acometidas en paralelo salieron con 834,9 A cada una, sin repartir la corriente de cabecera. Confirmar si es un error o el uso del parámetro.
- [x] **PRB-08 · Etapa de tomacorrientes** (2026-11-14). El motor `epc_receptacles` (ADR-0031) ya existía y se usaba en el ingreso de edificios; ahora también es el slice 31 de la etapa 3 (`engine_inputs.receptacles`, opcional), con hallazgos `major` por cada verificación fallida y su texto en español (`i18n.es`). Los valores típicos siguen pendientes de revisión (`TOM-01`).
- [ ] **PRB-06 · Motores fuera del pipeline.** Iluminación, climatización y tomacorrientes no entran en las 16 etapas (la potencia se escribe a mano); el transformador usa un `demand_kva` escrito a mano porque la demanda total del tablero está pendiente (etapa 5).
- [ ] **PRB-07 · Tensión fuera de 380/400 V.** El pipeline bloquea media tensión (p. ej. 13200 V) en la etapa 4. Obra civil y estructura (`civil_structural`) no tienen motores.

## Diagram knowledge (DGM)

Data in `knowledge/diagrams/` (research of 2026-11-20). The open items of DGM, OPT, GEN, PRO, COD and SYM are in the roadmap below. All `unverified`/`typical`/`not_found`; test `tests/unit/test_diagram_knowledge.py`.

PRD of the symbols: `docs/prsad/PRD-symbols.md` (one `epc_symbols` segmented by domain, migrated in parts; one pull request per phase, gate green before the next; nothing here changes norm values or calculation results).

## Roadmap (organized 2026-11-22, owner request)

One ordered list. Rules: (1) an item never sits before something it needs; (2) related items are adjacent and share a phase; (3) work that makes later work safe or measurable goes first; (4) items that need a person (**P**) are grouped in their own phase so they do not block agent work. **A** = an agent can do it now. Within a phase, do items in the order listed. Detail stays in each entry.

Dependency summary: Block 1 (measure and protect) → Block 2 (engine rules and contracts) → Block 3 (engines as functions and one symbol engine, together because both touch the generators) → Block 4 (speed, needs 1 and 3) → Block 5 (the flow and PV, needs 3) → Block 6 (trust and quality) → Block 7 (new product features) → Block 8 (owner and person decisions, parallel from the start).

### Block 1 · Measure and protect (A, no dependency, first)

Cheap, change no drawing, and make every later change measurable and safe. Do first.

- [x] (2026-11-23) **OPT-08 · One command that regenerates every generated file** (registry, plugins, agents, impact map) before a commit; stale generated files caused most CI failures.
- [x] (2026-11-23) **COD-15 · Pre-commit check for stale generated files** (with OPT-08).
- [x] (2026-11-23) **OPT-01 · Time every stage.** A stopwatch per pipeline stage (calculation, netlist, SLD, MLD, DXF, documents) written to the project log, so each later change is judged with measured data.
- [~] **COD-05 · Profile first** (cProfile on an example run); fix only the three most expensive points. Profile done 2026-11-23 on the whole-building run (about 13 s): (1) PDF text layout in matplotlib, 8.7 s of the 13 (`backend_pdf.draw_text`); (2) DXF files read again and again, `ezdxf.readfile` 50 times for 3.7 s (`epc_dxf.deliverable.convert`, `_finish`, `capas_dxf.colorear`, 8 calls each); (3) the plan sheets, 2.5 s (`plan_sheet.compose`). Done 2026-11-23 (a correction of the profile): the 8.7 s of `backend_pdf.draw_text` come from the report and transmittal PDFs (`report_pdf`, `transmittal_pdf`), not from `epc_drawing.export.pdf` (the DXF to PDF function, which no stage calls today; only its command line and its test do). That function no longer lets matplotlib work out the data limits patch by patch: its four PDFs of the example board take 5.1 s instead of 13.1 s with identical SHA-256 (fixed `SOURCE_DATE_EPOCH`). The report PDF was looked at too: its time is matplotlib's own glyph layout (`_text_helpers.layout`, about 1.1 s of 4.6 s for a 400-row table), which cannot be shortened without changing the PDF bytes (font type), so it stays open. Left for Block 4: each fix can change DXF or PDF bytes, so it needs the characterization tests of COD-13 first.
- [x] (2026-11-23) **COD-14 · Fast and slow tests separated** with markers.
- [x] (2026-11-23) **OPT-07 · Faster gate:** run only the tests the impact map says are affected on pull requests; the full battery stays for the release. No check is weakened. Fixed 2026-11-23: with no engine suite affected (a documentation change) the coverage check failed on missing data; it now passes with nothing to check.
- [x] (2026-11-23) **COD-13 · Characterization tests per engine,** not only for drawings, before each conversion. Done: `harness/tests/characterization/engine_cases.py` records, in `golden/engines.json`, what each of the 31 engines gives for fixed fictional inputs (110 numeric and document cases, the five `run` engines, rules, plan, arch, standards) plus the SHA-256 of every stage file and delivered file of the pinned `synthetic_lv_small` run (sld, mld, dxf, symbols, titleblock, documents, calc_check); test `test_characterization_engines` also fails when an engine is not pinned. `epc_drawing`, `epc_documents` and `epc_aea90364` keep their own golden files. To record again (only when the owner asks for a behaviour change): `python harness/tests/characterization/engine_cases.py --write`.
- [x] (2026-11-23) **GEN-02 · Reference projects (was C).** `python harness/tools/ci/reference_run.py` runs four fictional projects of `harness/tests/golden_projects/` (`synthetic_lv_small` office floor, `reference_dwelling` AEA 90364-7-771 dwelling, `reference_shed` industrial shed with three motors, `reference_pv_plant` small PV plant with an `epc_pv` array) and compares each with its previous run (stage statuses, findings, delivered files; times never fail it); the weekly simulation workflow runs all of them; test `test_reference_projects` checks that each finishes its 12 stages and that the PV one carries its plant. Invented data only; reports go to `tmp/`.
- [x] (2026-11-23) **OPT-14 · Automatic simulation report:** one command runs a fictional simulation in `tmp/` and gathers times, warnings and the difference with the previous one.
- [x] (2026-11-23) **GEN-10 · Scheduled simulation (was K).** A weekly fictional run in `tmp/` that reports when something breaks.
- [x] (2026-11-23) **COD-16 · Check the GitHub workflow files in the gate.** Done: architecture test `test_workflows_parse` (pyyaml in `requirements-dev.txt`). A YAML error in `ci.yml` (2026-11-23, an unquoted `: ` in a step name) left a pull request with no CI at all and no local check noticed; parse every `.github/workflows/*.yml` in the gate (needs a YAML reader in `requirements-dev.txt`).

### Block 2 · Rules and contracts for every engine (A)

The patterns the conversions of phase 3 follow; do before converting more engines. Errors and results first because the contracts use them.

- [~] (2026-11-23) **COD-21 · Explicit result type** (success, warnings, bilingual errors) instead of exceptions or silences. Done as ADR-0039 (proposed in PR #97, waiting for the owner's acceptance): 29 engines raise their own `<Engine>Error` built from a code with `.en` and `.es`; ratchet test `test_engine_errors`. Left: `epc_documents` (its golden file pins `ValueError`; converting it needs the golden recorded again, by the owner).
- [~] **COD-11 · No generic `except` and no silent fallback** (for example the box fallback of `pv_diagrams`): every failure with a message in English and Spanish. Done 2026-11-23: the architecture test `test_no_silent_catch_all` forbids a silent `except:` / `except Exception:` unless its line states why (`# noqa: BLE001 - <reason>`); six silent catch-alls in `epc_dxf`, `epc_documents` and `epc_drawing.export.logo` now catch only the expected error. Left: the documented fallbacks (`epc_arch` backdrop and PDF readers, logo drawing, hidden folder on Windows) still answer None without a bilingual message, and the `pv_diagrams` box fallback is SYM-03.
- [x] (2026-11-23) **GEN-08 · Error catalogue (was I).** `harness/docs/ERROR_CATALOGUE.md` is generated by `error_catalogue.py` from every `messages.py`; gate check `error-catalogue`. (Rest of the engines: `epc_documents`, see COD-21.) Original goal: stable error codes with messages in English and Spanish saying what happened and what to do.
- [x] (2026-11-23) **COD-22 · Immutable value objects between stages (first part).** `StageResult` and `RunResult` are frozen dataclasses (test `test_frozen_results`); `PipelineContext` stays mutable on purpose (the stages fill it). Left: freeze the dict payloads inside the results. Original goal: which makes the input-hash cache and parallel runs safe.
- [~] (2026-11-23) **COD-12 · Frozen dataclasses or schemas** (done for the stage and run results; the payloads are still dicts, see COD-22). Original goal: for what travels between stages, instead of dicts with loose keys.
- [~] (2026-11-23) **OPT-09 · Validate each engine input** (first part: input schemas for `epc_boq`, `epc_terminal_blocks` and `epc_datasheets`, checked against the engines' own bilingual errors by `test_engine_input_schemas`; they appear in `ENGINE_CONTRACTS.md`. Done 2026-11-23: input schemas for `epc_rfq` and `epc_design_basis` (their entry is one function whose arguments are the document; tests `test_input_schema.py` in each engine check schema and engine agree). Decision 2026-11-23 (owner's standing authorization): the input of an engine is a document only where the entry is one function that takes a document or the arguments of one call (the schemas above); the libraries of functions (`calc_common`, `feeder_sizing`, `grounding`, `load_balance`, `selectivity`, `short_circuit`, `transformer_sizing`, `voltage_drop`, `aea90364`) keep their per-argument checks and bilingual errors, covered by property tests (OPT-13). Done 2026-11-23: `epc_descriptive_report` too. Left: `epc_documents`, `epc_calc_check`, `epc_rules`, `epc_standards` and the drawing engines (their typed `*Input` dataclasses of ADR-0040 are their contract)). Original goal: against a schema at its entry point, failing with a clear message in English and Spanish.
- [x] (2026-11-23) **GEN-09 · Engine contracts generated from schemas (was J).** `harness/docs/ENGINE_CONTRACTS.md` is written by `engine_contracts.py` from the five engines that have schemas (lighting, pv, receptacles, hvac, plan) and lists the 26 that have none (OPT-09); gate check `engine-contracts` (49 checks). Input and output documented from the schema, not by hand.
- [ ] **OPT-16 · One small versioned example case per engine,** used as test, documentation and call example.
- [ ] **COD-17 · Functional core, imperative shell:** the engine is a pure function; reading files and environment and writing outputs live in an adapter (ADR-0038).
- [ ] **COD-04 · Parameters instead of environment variables** inside the engines (the SLD already takes `environ`; stop reading `os.environ` inside). Done 2026-11-23: `epc_dxf.capas_dxf` no longer reads `SLD_FORMATO` (the sheet format is the `a3` argument; same bytes). Left: `epc_dxf` (layer file, text-style folder and files), `epc_aea90364.solutions` and `epc_calc_common.norm_data`; they are read by many callers and tests, so they move together with each drawing engine's typed input (ADR-0040, proposed).
- [x] (2026-11-23) **COD-02 · One public door per engine** (`epc_x/api.py` and `__all__` for 29 engines; architecture test `test_engine_doors` with a baseline of 160 internal imports that may only shrink; `epc_documents` and `epc_standards` have no door yet). Original goal: (`__all__`, an `api` module); the architecture test fails when another package imports internals.
- [ ] **COD-18 · Facade with aliases** for each catalogue (symbols as `epc_symbols.resolve`; devices, cables next).
- [ ] **COD-19 · Strategy chosen by data** for what varies by view or norm, no `if` chains.
- [ ] **COD-20 · Builder as the only way to assemble the diagram model** (`diagram_model`, stable ids).
- [ ] **COD-23 · Practices kept:** schema contracts at the engine door, characterization tests before refactors, one small reversible PR per phase, an ADR for each architecture rule, architecture tests for dependency rules. Not adopted for now: a dependency-injection container, deep inheritance, an event bus.

### Block 3 · Engines as functions, and one symbol engine (A)

Same code (the SLD and MLD generators), so done together: SYM-01 (done) and SYM-02 with the SLD contract first, then the MLD, then the other engines. Phases that turn strokes into blocks (SYM-04, SYM-05) wait for the golden review of phase 8.

- [~] **SYM-01 · Catalogue schema and `epc_symbols` API** (`resolve`, `svg_fragment`, `dxf_block`, `terminals`, `list`) with aliases of the old names. Done 2026-11-22: `epc_symbols.registry` over the five libraries (catalogue id, qualified id and file name resolve to one record; a missing symbol raises, in English and Spanish; views are `sld`, `mld`, `ssd`; 227 DXF blocks checked: block name = file name), catalogue schema `schema/symbol_catalog.schema.json`, 14 tests. The library depends on nothing (architecture test), so placing a block in a DXF is `epc_dxf.symbol_blocks.insert(doc, *dxf_block(id, view), ...)`, not `epc_symbols.insert` as the PRD listed. No drawing changes, no golden touched. Pending: the plan, PV and architecture domains (SYM-03 to SYM-05) and the `relates_to` link between views.
- [ ] **DGM-16 · Engines are called functions** (owner, 2026-11-22, ADR-0038): every engine receives all its data and answers; none reads files, workbooks or environment variables on its own or searches for work. Convert one by one. SLD first: (1) define the input contract of `epc_sld.draw(entrada, out_dir, name, maxl, stamp_date)` (assembly, label slots, board figures, header, title block, layout); (2) make `sld_paginate` a function that calls `sld_generator.generate(..., environ=env)` in process, keeping the CLI as an adapter, with byte-identical output (`test_deterministic_design`, sld tests); (3) stage 10 / `board_design` call `epc_sld.draw`; (4) remove the internal Excel round trip. Then the MLD, then audit the other engines. Done 2026-11-22: step 2 and the in-process call of step 3: `sld_paginate.paginate(...)` is a function (CLI kept as an adapter) and `board_design` draws the SLD in process; the output is byte-identical to the subprocess path (checked on the example board with `--date`). Done 2026-11-23: step 1, `epc_sld.draw(SldInput, ...)` with a frozen contract and `SldError`; `board_design` calls it (step 3); the MLD takes its data as arguments (`epc_mld.generate(..., titleblock_request, log)`). Done 2026-11-23: step 4, the SLD draws from `SldInput.board` (data) and `board_design` writes no workbook. Pending: `epc_dxf` still reads `SLD_FORMATO` from the environment.
- [ ] **OPT-02 · All engines as called functions** (ADR-0038): MLD, `pv_diagrams`, `epc_plan`, `epc_arch`, one public entry point each (DGM-16). ADR-0040 accepted by the owner's standing authorization of 2026-11-23 (decisions: verbs `draw`, `draw_plan`, `draw_pv`; the PV drawings stay in `epc_drawing`; golden drawings are never re-recorded, a conversion that cannot keep the bytes waits for the owner). Done 2026-11-23: MLD, `epc_mld.draw(MldInput, out_dir, name)` (`board_design` calls it; same bytes, characterization tests pass). Done 2026-11-23: plan, `epc_plan.draw_plan(PlanInput, path)` (process then write_dxf; `plan_drawings` calls it; test compares the file with the two calls, same bytes); PV drawings, `epc_drawing.draw_pv(PvDrawInput, out_dir, name)` (one call for the ground layout, the roof planes and the equipment detail; `pv_drawings` calls it; same order and same drafts). Done 2026-11-23: the 3D calls, `epc_plan.draw_model3d(Model3dInput, out_dir, board)` (the model and its sections) and `epc_arch.building_solids(FloorInput)` / `epc_arch.draw_elevation(ElevationInput, path)`; the `model3d` stage calls them, same files (tests compare them with the lower-level calls). The pure builders `solid.solids`, `detail.parts` and `scene3d.merge` stay as functions of data. ADR-0040 is complete for the five jobs.
- [~] **DRW-01 · One drawing base** (2026-11-23, owner request, three stages). Option B done 2026-11-24 (PR open, awaiting the owner's approval of the proposed layer names): all layers `291-` NCS/AIA, English, with descriptions. Dynamic layers 2026-11-24: `0-Viewport` is the catalog role `sheet.viewport`; `epc_dxf.logo_layer_name` / `add_logo_layer` give `0-Logo-<Company>` from the project data; no DXF writer draws a logo or a viewport yet, so wiring them in is open. the prescribed layers of the other disciplines are in `/mnt/project-files/capas-ncs` reference only, (Owner) review of the proposal list. Stage 1 option A done 2026-11-23: `A-*` layers and pens are `arch.*` roles of `layers.json`, read by `epc_arch` as data (no engine dependency, so no `new_document` there), same bytes; next, the owner's single `291-` convention (option B, own PR, golden files re-recorded). Stage 2 done 2026-11-23: one function creates every DXF document, `epc_dxf.new_document(version, setup=, stamp=)`; `epc_plan` (`dxfout`, `scene3d`, `solid`) and `epc_drawing` (`pv_diagrams`, `pv_roof_model3d`, `pv_model3d`, `part_library`) use it; same bytes (characterization and engine tests pass). Correction 2026-11-23: stage 3 is already one geometry (`epc_arch.export.sheet_iram` reads the SVG of `epc_titleblock`; only the layer name `A-TITLE` differs). The decisions, with the expected diffs, are in `docs/OWNER_DECISIONS.md`. Original note: stage 1 (one source of layers and pens) and stage 3 (one IRAM title block) wait for the owner: the layer names and pens of `epc_plan`, the sheets and the diagrams differ today (`ARQ-/ELEC-/PLAN-*`, `291-*`, `A-*`; `epc_style.json` and `config/dxf/layers.json`), so reading them from one table changes layer names and line weights inside the DXF files, and `epc_arch.export.sheet_iram` is a second title block with its own geometry from `epc_titleblock`; both change the bytes of drawings that golden files and deliverables pin. They need the owner to say that the new bytes are accepted and to re-record the golden files (ARQ-37 is the same item). (Owner)
- [~] **COD-01 · No subprocess calls between engines** (done 2026-11-23 for the MLD in `board_design`; others pending) Done 2026-11-23: `epc_arch` takes the sheet as data (owner decision) and starts no process; its command line is the adapter that fetches the sheet. Pending: `epc_dxf` reads `SLD_FORMATO` and the layer, text style and norm-data folders from environment variables (COD-04); `epc_documents` runs `pdftotext`/`soffice` as external tools (not engine to engine). (MLD and the rest): call the function in process (DGM-16).
- [x] (2026-11-23) **OPT-03 · End the Excel round trip inside the SLD** (DGM-16 step 4): the model already holds the data.
- [~] **OPT-11 · Read the project once:** one loader builds the data package and hands it to each function. Done 2026-11-23: the title block request is read once per run and handed as data to the plan and PV sheets. The pipeline context already holds the answers, loads and criteria in memory; pending: the stage inputs read from `inputs/` (weather file, plans) through one loader.
- [~] **SYM-02 · SLD and MLD generators use the API** (no engine builds a symbol file name). Done 2026-11-23: both generators resolve the symbol file through `epc_symbols.resolve` for the default library. Symbols are placed as DXF `INSERT` blocks (SYM-00, done 2026-11-24). Pending: the other drawing engines (SYM-03 to SYM-05).
- [ ] **OPT-05 · One symbol engine** (SYM-02 to SYM-07).
- [~] **COD-03 · One source per symbol and device table** (DGM-13a, ADR-0012). Done 2026-11-24: the SLD legend table (`SIG` in `sld_generator.py`) moved into the symbol catalog as a `legend` field (`abbr`, `es`, `en`) of `_catalog.json`; same drawings. Done 2026-11-24: `device_symbol_map.json` keeps only the device to symbol link; ports and MLD variants come from the symbol catalogue through `symbol_for` (the old copy matched it in all 57 devices). Pending: the device to symbol link of the `close` and `placeholder` matches needs a person.
- [~] **SYM-03 · `photovoltaic` domain and PV drawings insert library symbols;** (done 2026-11-23: `pv_diagrams._symbol` resolves through `epc_symbols`; pending: the `photovoltaic` domain and the end of the box fallback, which need real IEC 60617 geometry supplied by a person) the silent box fallback in `pv_diagrams._symbol` is removed.
- [ ] **CIV-01 · Civil detail from the Samet catalogue** (owner request 2026-11-24). Done: the Samet Smarttray catalogue as data and the ladder drawing of a tray with a width. Pending: (1) the tray sizes of the plan (`sizing.tray_mm`, typical, pending review) come from the catalogue (widths 150 to 600 mm, rail heights 65, 90, 115 mm) and the stretch label carries the catalogue code (`TRES-<width>-<ala>-<gauge>-<finish>`); (2) fittings drawn at bends, tees and crosses (elbow, tee, cross, reduction) with the catalogue radius 300 mm (geometry done in `tray_fittings.py`, crossings by height in `tray_levels.py`; pending: the plan places them, reusable DXF blocks named by catalogue code, dimensions and MLEADER output); (3) supports (wall bracket, trapeze hanger) along the run at a spacing taken from the load test; (4) a bill of quantities of trays and fittings through `epc_boq`; (5) section views of the tray with its rail height. Each one changes drawings or typical values, so goldens and the norm register wait for the owner.
- [ ] **SYM-06 · Complete `electrical-mv`:** DXF blocks for `mld-mv` and `ssd-mv`. Checked 2026-11-23: `mld-mv-symbol` has an empty catalogue ("pending: no MV MLD symbols yet") and `ssd-mv-symbol` holds one SVG, so there is no existing geometry to approximate; the IEC 60617 shapes have to be drawn by a person (owner item). 2026-11-24: until a person draws them, a missing symbol is a named box through `epc_symbols.placeholder` (done: the function; pending: the MV generators call it).
- [~] **SYM-04 · `electrical-plan` domain:** the 31 symbols of `epc_plan/symbols.json` move into `epc_symbols` (replaced through a reviewed change, not deleted silently). Done 2026-11-23: the file and `pleno.svg` moved unchanged to `epc_symbols/library/plan-symbol/`; `epc_symbols.plan_symbols()` serves them and `epc_plan.core` asks for them (the plan output is identical). Pending: turning the primitives into catalogue blocks (waits for the golden review).
- [~] **SYM-05 · `architecture` domain:** the 25 `epc_arch/biblioteca` symbols and the door and window drawings. Done 2026-11-23: the 25 symbols (`catalogo.json`, `svg/`, contact sheet, repertoire) moved unchanged to `epc_symbols/library/arch-symbol/`, served by `epc_symbols.arch_symbols()`; the generator script writes there. No engine used them yet. Pending: door and window drawings as blocks (golden review).
- [~] **SYM-07 · Gate guard** (done 2026-11-23: `test_symbol_access` lets no file outside `epc_symbols` build a symbol file name, and the allowed list only shrinks; pending: deliverable DXF with `INSERT` blocks (needs the golden review), every symbol id used in the code exists): no drawing engine draws a symbol outside `epc_symbols`; deliverable DXF files of the golden projects have `INSERT` blocks; every symbol id used in the code exists.
- [~] **OPT-10 · Deterministic output in every engine** (dates, element order, identifiers), so cache and golden comparisons are reliable. Audit 2026-11-23 (clock reads left in the engines): drawings already take the day as data (`sld`, `mld`, `titleblock.project_request(today=)`); still read the clock inside the engine: `epc_arch.cli_v2._manifest` (`run_at`), `epc_documents` charter and canvas seals (`updated`), `epc_standards.promote_rules` (`validated_on`, `date`), `epc_pv.weather` (`retrieved`). None of them changes a drawing, but the manifest and seals differ run to run. Done 2026-11-23: `epc_documents` charter and canvas exports and `epc_arch.cli_v2._manifest` take the time as an optional argument (`ahora=`, `now=`; the clock is only the default), with tests. `epc_pv.weather.fetch_tmy` already took `retrieved=`; `epc_standards.promote_rules` reads the clock only in its command line (the adapter). Done 2026-11-24: when no time is handed in, the seals of `epc_documents` and the manifest of `epc_arch` use `SOURCE_DATE_EPOCH` (reproducible builds) before the clock; tests added.

### Block 4 · Speed, only what phase 1 shows is worth it (A)

Needs the stopwatch and profile of phase 1, the deterministic output of phase 3 and the value objects of phase 2.

- [x] **COD-06 · Load once and cache:** symbol catalogue, schemas, templates, norm records. Same measurement: the catalogue, schemas and norm records load in under 10 ms; `epc_symbols` reads its catalogue once per process already. Nothing to cache beyond COD-07.
- [~] **COD-07 · Parse each SVG and DXF block once per run** and reuse it. Done 2026-11-23 (first part): `epc_dxf.bloques_dxf` reads each library symbol file once per run (cached by path and modification time); the importer only reads from it. Done 2026-11-23 (second part): layer assignment, colouring and block insertion work on one document read once and written once (`aplicar`, `colorear`, `insertar` take `doc=` and `write=`). Measured on the example board (`epc_drawing.board_design`, `--date` fixed, four DXF files): 4.4 s before COD-07, 3.8 s after the symbol cache, 3.6 s after the shared document; the SHA-256 of the four DXF files is the same in all three. Third part: `convert` and `finish_draft` count the entities per layer on the document they just wrote instead of reading the file back (example board 3.6 s to about 3.2 s, same four SHA-256). Left: the SVG parsed twice.
- [x] **OPT-12 · Load drawing templates once per run:** title block, symbol blocks and styles. Measured 2026-11-23 on the example board (cProfile): reading the JSON data of the generators takes under 10 ms in total, so nothing is gained by loading templates once more; the cost is ezdxf parsing DXF files and importing the libraries. Not worth doing as written; the remaining time is in COD-07 (SVG parsed twice) and COD-08.
- [ ] **COD-08 · Batch DXF writing,** only if the profile confirms it.
- [x] **OPT-04 · Cache by input hash.** Decided 2026-11-23 against, from the stage timings of a house run: the repeated work is the drawings and documents (7 of 8 s), and a cache would help only a re-run with the same inputs, which stage 10 already skips for the calculation (the stage that changes the answer). A cache of drawings would need every input of every drawing in the hash (plans, titleblock, library files) and a way to know when it is stale; a stale drawing in a deliverable costs more than the seconds saved. Reopen if re-runs with unchanged inputs become the common case.
- [x] **OPT-06 · More parallelism:** documents (PDF, DOCX, XLSX) and plan sheets, as MLD and SLD already run in threads. Done 2026-11-23 for the documents: stage timings of a house run (4 bedrooms, 2 bathrooms, lighting and receptacles, through the landing form; 11.2 s: drawings 4.4 s, documents 6.1 s, the rest under 0.5 s) showed the 14 report PDFs drawn one after the other; `report_pdf.render_many` now draws them in up to four processes (matplotlib is not thread-safe) while the DOCX files are written here: documents 6.1 s to 3.0 s on four cores, the run 11.2 s to 8.3 s; a test checks the files are byte-identical to `render` one by one. Plan sheets are not worth it: `plan_sheet.compose` is a small part of the drawings stage.

### Block 5 · The flow: circuit analysis, netlist, calculation, auditor, assembler (A, with P inputs)

Needs the engine contracts of phase 3. DGM-12 and DGM-15 first (the flow and who owns each step), then the diagrams reading the model, then other disciplines and PV.

- [ ] **DGM-12 · Circuit analysis first, then netlist, then calculation** (owner, 2026-11-21): the order of the flow changes. (1) The circuit analysis lists the devices of each circuit (roles, from the load type, the typical topologies and the design constraints); (2) the netlist organizes how they connect; (3) the cable types are estimated without a cross-section (conductor material, insulation, number of cores, installation method, from the load, the environment and the design criteria); (4) the calculation sizes each device already placed and each cable (In, Icu, poles, sensitivity, cross-section, voltage drop); (5) the auditor, with all the calculations and lists in hand, checks them against the design constraints and gives the verdict (ok or not ok, with the findings); it is the only one that decides, and it runs before the assembly (the existing `calc_check` agent and the advisory `violations` of the assembler are the starting point); (6) the assembler joins everything only once the auditor has given its verdict; (7) the assembly is the single hand-over: the SLD, MLD, lists (cable list, terminal blocks, BOQ), datasheets and specifications are generated from it and none re-reads the calculation. Checked 2026-11-22: the SLD generator (`epc_sld.sld_generator`) takes its device chain from `detalle.cadena`, the same chain the netlist reads, and a test now pins that both give the same symbols; the SLD still reads the workbook and three JSON files of the calculation (`SLD_CALC_JSON`, `SLD_CALC_DETAIL`, `SLD_FIGURES_JSON`), so making it read the assembly needs the assembly to carry the label slots and the board figures first (a change of the SLD input contract, to design with the drawing characterization tests). Found and fixed 2026-11-22: stage 10 ran the whole calculation (grouping, sizing, memo) a second time inside `board_design.design`; it now reuses the one of the run (same files, byte for byte). Today the calculation writes the device text (`disp`) and the netlist reads it, the opposite. PRD: `docs/prsad/PRD-diagram-flow.md`. Found 2026-11-21: the device chain is already chosen by the standard solutions (`epc_aea90364.solutions`, data in `standard-solutions.json`), and the calculation keeps its structured chain in `detalle.cadena`; step 1 of the flow is that resolver run before the sizing for the structural conditions (`in_a` conditions need the value). Done: the netlist now reads the structured chain (devices and poles) and falls back to the `disp` text. Done: the cable type of each circuit (material, insulation, cores, installation method, never a section) is decided by `epc_aea90364.cable_types`, used by the pipeline before the section search (same results) and callable on its own to estimate a board ahead of the calculation. Pending: the resolver called before the sizing for the structural conditions, and the auditor verdict as an agent step. Done: `diagram_knowledge.audit(model)` gives the verdict (ok or not_ok, unverified) from the design constraints, and `diagram_assembler.assemble` refuses to run without it and carries it (`verdict`); `calc_check` still has to own it (DGM-15). Touches stage 3 and the calculation input (other threads, golden files): spike first to measure what it breaks, then design; no norm value changes.
- [ ] **DGM-15 · Discipline leaders and interdisciplinary coordinators** (owner, 2026-11-21): a coordination layer above each discipline flow: discipline leader (owns its flow and verdict), interdisciplinary coordinator (audits the interfaces between disciplines, for example the loads handed to the board and the inverter-to-board connection), multidisciplinary leader (sequences the disciplines and prepares the transmittal for the engineer of record). Open: new roster entries or duties of the orchestrator (`roster.json`, `roster.disciplines.json`). See `docs/prsad/PRD-diagram-flow.md` section 5. Owner decision 2026-11-21: each role has one duty and no duty is duplicated; map and order of work in `docs/prsad/ROLES-single-responsibility.md` (single-owner test, one orchestrator with a scope, `electrical_lv` as discipline leader, `calc_check` as the only verdict, `documentation` and `procurement` from the assembly, duplicated legacy agents out of the flow). Done 2026-11-21: the 35 unused legacy agents were removed (owner decision; `document-writer`, the seven `senior-*-engineer` reviewers named by the reserve discipline leads, and `agents/disciplines/` stay). Done 2026-11-21: every roster entry has one `duty` (schema field) and a test fails when a duty has two owners; one `orchestrator` with a scope (discipline or project, with the interface register); `multidisciplinary_orchestrator` removed. Done 2026-11-21: `calc_check` states the verdict (it reads the assembly `verdict`, never recomputes it) and `documentation` and `procurement` already say they never verify. Next: `electrical_lv` takes flow steps 1 and 3; `documentation` and `procurement` read the assembly once the generators do (DGM-12 step 7).
- [ ] **DGM-13 · Research follow-ups of the assembler flow** (2026-11-21, agent reports, all unverified): (a) one device catalogue for the diagrams (today the symbol tables are duplicated across `sld_generator.py`, `device_symbol_map.json` and the symbol catalog); (b) the netlist builder, the audit and the assembly of one board now run in `epc_drawing` (`diagram_assembler.assemble_board`, done 2026-11-22; stage 10 only selects the circuits and values) and one circuit-view selector is used (done 2026-11-22: `stages/circuit_view.py` replaces the four selectors of terminal, BOQ, report and cable rows); (c) owner decision on the duplicated HVAC and lighting `typical.json` values; (d) candidate constraints `dc-03` to `dc-16`, each to be confirmed by a person before it enters `design_constraints.json`; (e) five speedups listed in the research report.
- [~] **DGM-02 · SLD/MLD read the relational model** (ADR-0037, 2026-11-21). Hecho: model per board (devices, loads, wires, circuits by stable ids; cable data stays in the stage 8 cable list), schemas, typical topologies (`circuit_topologies.json`), builder and CLI `epc_drawing.diagram_model`, skill `diagram-model`, tests; stage 10 hands over the assembled board diagram (`diagram_assembly`: `epc_drawing.diagram_assembler` joins the model, the calculation values and the cable-list rows with the design rules; the calculation does not generate the model; the design rules are constraints checked on the netlist, `violations`). Falta: more constraints (a person confirms each one), showing `violations` as findings, and the swap of the symbol provider to `epc_symbols`. Falta: the optional SLD/MLD input path that reads the model (the board workbook path stays as is). Typical topologies of star-delta, ATS, UPS and the MV intake are done (all unverified); the ATS second source and the real wiring of the star-delta contactors wait for DGM-10.
- [~] **DGM-10 · The harness draws functional and control schemes** (owner, 2026-11-21; design written 2026-11-23 as ADR-0041, proposed, for the owner to accept; the engine waits for it and for the IEC 60617 geometry of the control symbols, which a person supplies): power and control circuits (DOL, star-delta, reversing, ATS...) from `funcional_iec60617` and the relational model, with its own drawing path (IEC 60617 symbols, terminal marking, cross-references). Design first, then engine.
- [ ] **DGM-11 · Same method for the other disciplines and for PV plants** (owner, 2026-11-21): builders and topology kinds for PV strings and combiners, HVAC, lighting and control schemes, same four-file model and id rule (ADR-0037, point 5).
- [ ] **DGM-14 · Same flow for photovoltaic plants** (owner, 2026-11-21): analysis of the plant (string, optimizer, combiner, fuse, isolator, SPD, inverter, rapid shutdown, RCMU or IMD, AC protection), netlist per array and board, DC and AC cable types without cross-section, calculation with the PV engine, audit with the PV constraints (candidates in `docs/prsad/PRD-diagram-flow.md`, each confirmed by a person), assembly. Depends on DGM-12 and on the real symbols of DGM-03. Done 2026-11-22: typical topologies `pv_string` (DC string fuse, DC load-break switch, module string) and `pv_inverter_ac` (AC protection, inverter) in `circuit_topologies.json`, unverified; the board model builds them. Done 2026-11-22: `pv_string_optimized`, `pv_combiner_dc` and `pv_inverter_ac_rcmu` use the optimizer, combiner box and RCMU with their block placeholders. Pending: DC SPD and rapid shutdown in the chain, real IEC 60617 symbols (DGM-03: drawn only from the standard, which is not stored here; a person supplies or confirms the geometry), DC cable types, PV audit constraints (a person confirms each), and the PV engine feeding the calculation.
- [ ] **DGM-07 · Feed `epc_pv` and the PV drawings from these criteria** (decision rules for DC protection, grounding, SPD) once the PV equipment loader (audit H1-H3) is in.

### Block 6 · Trust and quality (A)

Build on the traceable flow of phase 5 and the reference projects of phase 1.

- [x] **GEN-01 · Pending-norm view (was D).** Done 2026-11-23: `REVISION_NORMAS.md` lists the review units ordered by how many engines change if the unit changes (from the generated dependency map), with a new column; the unit-to-engine table is `UNIT_ENGINE` in `review_list.py`. Original goal: One generated view of every value still `pending review`, ordered by how many deliverables depend on it, so the owner approves first what unblocks most. Agents never approve a value (P: approval).
- [ ] **PRO-01 · Decision register per project.** Every assumption the harness makes (a default, a norm chosen between two) listed for the engineer of record to review before signing.
- [ ] **GEN-04 · Traceability in every deliverable (was B).** Each number shown with its engine, version and norm record.
- [ ] **GEN-03 · Independent cross-check before sign-off (was A).** A second path recalculates the critical values (voltage drop, cross-section, protection) and flags differences; `calc_check` keeps the only verdict.
- [x] (2026-11-23) **OPT-13 · Property tests for the calculation engines** (done 2026-11-23 for `voltage_drop`, `feeder_sizing` (section choice), `load_balance`, `grounding`, `short_circuit`, `transformer_sizing`, `selectivity` and `calc_common`: seeded, standard library only, no new dependency; done 2026-11-23 for `lighting`, `receptacles`, `hvac` and `pv` too: seeded generated documents, values taken from the document only) (invariants, for example more load never lowers the cable section); no norm values touched.
- [ ] **PRO-02 · Outdated-norm alerts.** A notice when a norm edition in the register has a newer one; a person decides whether to update (P).
- [~] **COD-10 · Gradual static typing:** annotations on the public entries and `mypy` on those modules only, widening slowly. Started 2026-11-23: `epc_transformer_sizing.sizing`, `epc_voltage_drop.voltage_drop` and `epc_load_balance.current_and_loads` are fully annotated and `harness/tests/architecture/test_typed_modules.py` runs mypy (`--disallow-untyped-defs`) on the listed modules; add a module to `TYPED_MODULES` once it is annotated, one engine at a time. Done 2026-11-23 (second part): `calc_common` (`fmt`, `aea_rounding`, `_validate`, `norm_data`, `policy`, `api`), the `errors` of grounding and short circuit and the `api` doors of grounding, short circuit, selectivity and feeder sizing. Done 2026-11-23 (third part): `selectivity.aea_protection`. Left: the larger modules (`aea_icc_*`, `short_circuit.py`, `aea_earthing`, `aea_ampacity`, `aea_conductors`, `aea_route`, `cable_thermal`, `conductor_selection`, `aea_tables`).
- [ ] **COD-09 · Lower complexity per module touched** (OPT-15), never raise the baseline.
- [ ] **OPT-15 · Lower the complexity baseline** a little at each module touched; never raise it.
- [ ] **COD-16 · Remove dead code** guided by the dependency map, one reviewed change per removal (nothing is deleted silently).
- [ ] **PRO-03 · Backup of the projects** (they live outside the repository): versioned, encrypted copy.

### Block 7 · New product features (A)

After the flow is stable. Related items adjacent: delivery and revisions, then studies and quantities, then inputs, then knowledge and team.

- [ ] **PRO-07 · Project status panel:** stages run, pending reviews, what blocks the issue.
- [ ] **PRO-10 · Issue checklist** generated from the real project state.
- [ ] **GEN-06 · One-click delivery package (was G).** Drawings, memo, lists, transmittal and manifest in one numbered folder, with the edit or production mark visible.
- [~] **GEN-07 · Change control between revisions (was H).** A readable summary of what changed between revision A and B (circuits, sections, symbols). Done 2026-11-24: engine `epc_changes.compare` (added, removed, changed by field). Pending: feed it from the manifests of two issues and write the readable summary into the transmittal.
- [ ] **GEN-05 · Shorter guided form (was E).** `/init` asks only what cannot be deduced and proposes defaults with their basis.
- [ ] **PRO-09 · "What if" mode:** change a load or a cable and see the effect without redoing the project.
- [ ] **PRO-06 · More studies:** short circuit and protection selectivity on the relational model.
- [ ] **PRO-05 · Typical Argentine tables from the same model:** load schedule, phase balance, earthing table.
- [ ] **PRO-04 · Bill of quantities and budget from the assembly,** joining the cable list and the quotation with costs per item.
- [ ] **PRO-08 · Import architecture plans from other formats** (for example IFC), not only DXF.
- [ ] **GEN-11 · More disciplines on the same method (was L).** Lighting, HVAC and control on the relational model and the symbol engine, after SYM (see DGM-11).
- [ ] **PRO-11 · Lessons from simulations:** each simulation finding creates its draft lesson (only the owner makes it `standard`).
- [ ] **PRO-12 · Onboarding guide** for another engineer, generated.
- [x] **PRO-13 · Harness metrics:** projects, failures per stage, time per stage. Done 2026-11-23: `python harness/tools/ci/harness_metrics.py --root <projects folder>` reads each project's stage statuses and the stage timings of its runs (`EPC_TIMINGS=1`); terminal or `--json`, nothing stored.

### Block 8 · Needs a person (P), parallel from the start

Does not block agent work. SYM-00 and the golden review gate every phase that turns strokes into blocks; the symbols PRD decisions and the norm and symbol confirmations are for the owner or the engineer of record.

- [x] **SYM-00 · DXF block lookup in the SLD and MLD path** (done 2026-11-24, owner OK to re-record the golden once). `bloques_dxf` finds the library file through the library's `_catalog.json` (id to file) and keeps the block name the file gives; the MLD passes its symbol library to the conversion. The example board gives 18 `INSERT` in the SLD and 7 in the MLD, no audit errors; golden files re-recorded with the official tools (drawings and engine cases).
- [ ] **(Owner) SYM-OD · Open decisions** of the PRD section 9: ids (keep file names plus aliases, or rename), shared record across views for the same meaning, where the catalogue spreadsheet lives, placement of the architecture symbols.
- [~] **DGM-03 · Six devices without a library symbol:** IMD, blocking diode, power optimizer, rapid shutdown device, RCMU, string combiner box. Done: each is now a block placeholder (a box with the device name; SVG, DXF block and catalog entry, `origin: placeholder`, made by `tools/symbols/add_block_placeholders.py`). Pending: the real IEC 60617 symbol swapped in later (always a block), and the MLD variants.
- [ ] **DGM-04 · Confirm the 'close' symbol matches** (e.g. RCD types A/B/F to the RCCB symbol, ANSI relays to the generic relay) and the contactor main-contact symbol (S00286 note says closed at rest). (Owner)
- [ ] **DGM-05 · Open source conflicts for a person:** string fuse factor (1.5 x Isc vs 1.25 x 1.25 x Isc), RCD type on transformerless inverters (A vs B), rapid shutdown threshold (30 V / 30 s from SMA, not in IEC 60364-7-712), DC/AC shutdown order, RS485 terminator, MV station envelope. (Owner)
- [ ] **DGM-06 · Standards read only through secondary sources:** IEC 60445 / EN 50005 terminal marking, IEC 81346-2, IEC 62548, AEA 90364-7-712, NEC 690. Read the standards and promote values (pending review).

### Done (kept for history)

- [x] **DGM-01 · Research data and bridge to the symbol library** (2026-11-21). 57 devices mapped to `epc_symbols` symbols and ports, netlist contract proposal and 18 netlists.
- [x] **DGM-08 · Code that reads the diagram knowledge** (2026-11-21). `epc_drawing.diagram_knowledge`: `rules()`, `matching(variables)`, `symbol_for(device_id)` and `check_board(calculo)` (advisory notes EN/ES, never changes a result). Tests: `tests/unit/test_diagram_knowledge_use.py`.
- [x] **DGM-09 · Stage 9 lists the diagram-rule notes** (2026-11-21). `calc_check_stage.diagram_findings`: where the protective device of a circuit differs from the one the LV rules select for its current, a `note` finding (verifier calc-check, EN and ES text) joins stage 9. Advisory, no result changes; goldens unchanged. Test: `tests/unit/test_diagram_knowledge_use.py`.


## Landing (LND)

- [~] **LND-01 · Landing conectada al pipeline** (2026-11-19). Hecho: lectura del pedido por reglas, propuesta de casa de una planta, campos editables, corrida de 12 etapas y lista de entregables. Dos plantas con escalera y montante ya corren. Falta: más de dos plantas, techos, otras disciplinas (solo se guarda el pedido), abrir DXF desde la página.
- [ ] **LND-02 · El lector de planos parte los pasillos en ambientes fantasma** cuando las paredes de los dos lados no coinciden. La casa generada no lleva pasillo por esto (los dormitorios abren al living). Arreglar `epc_arch.recognizers` y volver a poner el pasillo.
- [ ] **LND-03 · Pedido libre con un modelo de lenguaje.** Las reglas no entienden descripciones sin cantidades, medidas ("living de 6 m al sur"), negaciones ni otros idiomas. Un LLM detrás de `brief.interpret` lo haría; las salidas seguirían siendo campos editables.
- [ ] **LND-04 · Valores propuestos de la casa** (`house_defaults.json`: tamaños de ambientes, 2,6 m de altura, luminaria 18 W, toma 100 VA, fp 0,9, jardín 20 lux). Son propuestas de diseño, no norma; el ingeniero los confirma. (Dueño)

## Harness (HRN)

> **2026-11-11:** the HRN queue below is replaced by `migration-loop/BACKLOG.md` (plan §8, `docs/harness/MIGRATION_PLAN.md`). No HRN item is deleted; they stay as history.

**Out of scope (owner, 2026-11-10):** the English migration of existing code, keys and files is removed to save cost. Existing Spanish names stay; new code follows the language rule in `CLAUDE.md`. Design: `docs/harness/SPEC.md`; protocol: `docs/harness/LOOP.md`. The original seed stays in `docs/harness/BACKLOG.harness.md`; from now on this section is the only source.

Rules, in addition to «Cómo se usa»:

- **No git writes** (owner rule, 2026-11-09). The `label` of each task is only a name for PROGRESS and the snapshot folder. No branch is created and nothing is committed or merged. Undo is `snapshot.py rollback`.
- "Gate green" means: no check is worse than the baseline recorded by `HRN-01`.

- Each task gives `deps`, `label` and `acceptance`. The loop takes the first task, in the order of this file, whose `deps` are all `[x]`.
- A task with sub-items is done one sub-item per iteration. It stays `[~]` until every sub-item is `[x]`.
- **(Owner)** marks what only the owner can do. The loop reminds the owner and never executes it.
- **Decided: Dnn (2026-11-10)** replaces the old «Owner decides first» marker: the owner answered in `docs/harness/DECISIONS.md`, and the task follows that answer (the line under the task states it). **(Frozen: D15)** and **(Frozen: D26)** mark tasks the loop skips like **(Owner)** tasks until the owner lifts the freeze. **(blocked until the owner verifies the values involved)** is still treated like **(Owner)**.
- Leftovers get new IDs `HRN-29`, `HRN-30`, … at the end of the queue (`HRN-30` to `HRN-74` come from the engineering review of 2026-11-10, Phase 9; `HRN-75` and `HRN-76` were added with the owner's answers of the same day).

---

### Phase 0 · Prepare

- [x] **HRN-01** (2026-11-09) Gate baseline. Result: 35/38 checks pass; web-types, web-tests and web-build fail before any change (frontend/console). Recorded in `STATE.gate_baseline`.
  - deps: — · label: `chore/HRN-01-baseline`
  - Run `PY tools/ci/run_gate.py` once, before any change. Record each check and its result in `STATE.gate_baseline` and in PROGRESS. From now on, "gate green" means no check is worse than this baseline.
  - If `.git` is absent, the checks that call `git ls-files` (`check_single_source`, `check_complexity`, `check_ignored_sources`, `check_dev_credentials`, `collect_metrics`) fail. Record them as failing for that reason; `HRN-01A` fixes them.
  - Change nothing in the repository. Leave the owner's untracked files (for example `incoming/*.docx`) untouched.
  - acceptance: `STATE.gate_baseline` lists every check with pass or fail.

- [x] **HRN-01A** (2026-11-10) Gate checks work without git. Not needed: .git present (`git ls-files` lists 1975 files).
  - deps: HRN-01 · label: `fix/HRN-01A-gate-without-git`
  - Only if `.git` is absent, or `git` cannot run. Otherwise mark it `[x]` with the note "not needed: .git present".
  - Add `tools/ci/_repo_files.py`: it lists the repository's versioned-equivalent files by walking the tree and honouring `.gitignore` (root and nested), with a small matcher written for this purpose and tests on a synthetic tree. Each of the five checks uses `git ls-files` when it works and this function otherwise. With git present, the output must be identical.
  - `check_dev_credentials` and `check_ignored_sources` use `git check-ignore`: route them through the same matcher.
  - acceptance: with `.git` absent, the five checks run and pass or fail on their merits; the tests of `_repo_files.py` pass.

- [x] **HRN-00** (2026-11-10) Install the harness into the repository.
  - deps: HRN-01A · label: `chore/HRN-00-install-harness`
  - With `SNAP move`, move `harness-loop/` to `docs/harness/` (`README.md`, `README.es.md`, `GOAL.md`, `LOOP.md`, `SPEC.md`, `DECISIONS.md`, `STATE.json`, `PROGRESS.md`, `BACKLOG.harness.md`, `seeds/`, `settings.loop.json`, `prompts/`) and `harness-loop/scripts/*` to `tools/harness/`. Fix the paths in both READMEs and the script headers. The runners and `stop.ps1` already look in both places.
  - Set `STATE.home` to `docs/harness`.
  - Append `CLAUDE.harness.md` to the root `CLAUDE.md` as a new section, then move the copy to `docs/harness/archive/`.
  - Insert this queue into `harness/docs/BACKLOG.md` as described above and update «Siguiente».
  - Add `docs/harness/STOP` to `.gitignore`. Runner logs and backups live under `.claude/`, which `.claude/*` already ignores.
  - acceptance: `docs/harness/LOOP.md` exists; `harness-loop/` holds no file; the gate is not worse than the baseline; `single-source` does not flag the seeds (add exemptions with their reason if needed).

- [x] **HRN-02** (2026-11-10) Fix the inconsistencies found in the 2026-11-09 analysis. README counts now 15 plugins, 6 skills (from `registry.json`); skill `design-board` created; «Siguiente» lists open items.
  - deps: HRN-00 · label: `fix/HRN-02-inconsistencies`
  - The README counts 15 skills but `harness/.claude/skills/` has 5: make the README count come from `_registry.json` (or state the real number).
  - `harness/.claude/plugins/board-design/README.md` lists the skill `design-board`, which does not exist: create it as a thin skill over `python -m epc_drawing.board_design` (owner `board-design`), or remove the reference. Prefer creating it, since `HRN-14` needs it.
  - The «Siguiente» queue lists done items (E4-09, E4-10, E1-10): replace them with the next open ones, in their current order.
  - acceptance: `check_skill_conflicts.py` reports no orphan or missing skill; the gate is green.

- [x] **HRN-03** (2026-11-10) ADR-0034 and the no-git rule in `CLAUDE.md` (the rule went in with HRN-00).
  - deps: HRN-00 · label: `chore/HRN-03-adrs`
  - ADR-0034 "Claude Code harness" (summary of `SPEC.md` §1–§3, §6). Index it in `harness/docs/architecture/decisions/README.md`.
  - Add the owner's no-git rule to `CLAUDE.md`, as it stands in `LOOP.md`.
  - acceptance: the ADR is present and indexed; the gate is not worse than the baseline.

### Phase 0b · Safety first (owner decision, 2026-11-10)

HRN-30 to HRN-33 moved here from Phase 9(a) so that the loop, which takes the first task in file order whose deps are done, runs them before HRN-09 and everything else. Nothing was deleted; their text is unchanged except HRN-33, now decided (D23).

- [~] **HRN-30** Loop guard hook and narrower permissions.
  - deps: — · label: `chore/HRN-30-loop-guard`
  - A `PreToolUse` hook for loop sessions (declared in `docs/harness/settings.loop.json`, script `tools/harness/guard_hook.py`) denies: Bash commands with a git write, any Edit/Write/NotebookEdit of a path under `.git/`, `local/`, `.claude/harness-backups/`, `.claude/settings*`, `docs/harness/settings.loop.json` or `.env*` (not `.env.example`), and Bash that writes there. Replace the prefix allows `Bash(python *)`, `pip *`, `npm *`, `npx *`, `node *`, `py *` with the exact commands the loop needs (gate, `snapshot.py`, unittest/pytest, `tools/build/*`); add `Write(./local/**)`, `Write(./.git/**)`, `Edit/Write(./.claude/**)` and `Edit/Write(./.env*)` to deny. (F19)
  - acceptance: hook tests with sample payloads (git commit, write to `local/x`, edit of `settings.loop.json`, `python -c` writing into `.git`) are denied; an edit in `docs/` and the gate command are allowed; the owner confirms the new allow list.
  - (2026-11-10) implemented outside the loop; pending: test on Windows with Claude Code. Done: `tools/harness/guard_hook.py` + `tools/harness/tests/test_guard_hook.py`, hook wired in `settings.loop.json`, pip/npm/npx allows removed, deny rules added. Remains: real-session check (hook command cwd, exit-code-2 deny, subagent calls), `python *` still allowed (the hook is the barrier), the owner confirms the allow list.

- [~] **HRN-31** Runner hardening.
  - deps: HRN-30 · label: `chore/HRN-31-runner`
  - Total budget across iterations (today `--max-budget-usd` is per iteration, default 8 x 60); after each iteration compare `LOOP_STATUS` with `STATE.json` and the last PROGRESS entry (status, `current_task`, `done` count) and treat a mismatch as `unknown`; stop after three blocked tasks in a row (LOOP.md Stop conditions); PID check in `loop.sh` like `loop.ps1:73-76`. (F19)
  - acceptance: tests with a fake `claude` command: the total budget stops the loop; a log that says `done` while STATE is not done counts as unknown; a second `loop.sh` refuses to start.
  - (2026-11-10) implemented outside the loop; pending: test on Windows with Claude Code. Done: total budget as iterations x per-iteration <= `-MaxTotalBudgetUsd` (default 10 x 6 = 60), STATE.json cross-check, blocked streak of 3, hook self-test before start, PID check in `loop.sh` (tested with a fake `claude` in `tests/test_loop_sh.py`). Remains: `loop.ps1` never run (PowerShell 5.1 and 7), the last PROGRESS entry is not compared, no real cost accounting.

- [~] **HRN-32** `snapshot.py` fixes.
  - deps: — · label: `fix/HRN-32-snapshot`
  - Files over 200 KB show size, sha256 and changed-line count in `diff` instead of being hidden; `move` writes its manifest entry before moving and `rollback` copes with an interrupted move; new `verify` command lists files changed since the task opened that are not in the manifest (hash index kept at first `save`), and `diff` calls it. (F19)
  - acceptance: temp-repo tests: large-file diff, interrupted move, an unsnapshotted edit is reported; existing commands unchanged.
  - (2026-11-10) implemented outside the loop; pending: test on Windows with Claude Code. Done: journaled `move` with every file, exact rollback, baseline + `audit <task>` (alias `verify`), size/sha256 in `diff` for large or binary files, refusal of `local/` and `.env*`, lock file (`tests/test_snapshot.py`). Remains: `diff` does not call `audit` itself (LOOP.md step 7 runs it), baseline hashing is capped at about 45 s, check the lock on a Windows folder.

- [~] **HRN-33** Backend side effects against the no-git rule. **Decided: D23 (2026-11-10).**
  - Decision (D23, owner 2026-11-10): No automatic commits and no automatic rewriting of git-tracked registers: `history.confirm` makes no commit and project creation leaves `harness/.claude/plugins/registry.json` untouched.
  - deps: — · label: `fix/HRN-33-backend-side-effects`
  - `sld/history.py` `confirm()` runs `git add`/`git commit` when the project folder is a repository (`:103-114,128`); `projects.create` calls `refresh_lock`, which runs `cmd_registry` and rewrites `harness/.claude/plugins/registry.json` (`projects/repository.py:103-108`). Implement the answer to D23. (F20)
  - acceptance: with the chosen option, a confirm inside a git project makes no commit and project creation leaves `harness/.claude/plugins/registry.json` byte-identical (tests); the web behaviour the owner keeps is unchanged.
  - Done 2026-11-10 (ENG-12): `sld/history.py` no longer runs git (`uses_git`/`_commit` removed; the status `git` key stays, always False); `projects/repository.py:refresh_lock` no longer calls `cmd_registry`, it only writes the lock from the existing registry. Tests added/adapted in `test_load_chain_api.py` and `test_projects_api.py` (pass). Left: the web note `eng.sld.gitNote` (SldEditor.tsx, dict en/es) is now dead UI and can be removed with the frontend; the full `test_load_chain_api` suite was not green in the ENG-12 environment (19 failures/errors, unrelated to git, missing engine dependencies), so mark `[x]` once the gate confirms it.

### Phase 2 · Tool interface

- [ ] **HRN-09** MCP server `epc`.
  - deps: HRN-03 · label: `feat/HRN-09-mcp-server`
  - As in `SPEC.md` §4: package `harness/src/platform/mcp/` (`epc_mcp`), stdio, in-process calls to the backend `public.py` functions, the tool list of §4.2, the write guard and the read-only profile.
  - Parity test `tools/ci/check_mcp_parity.py`: build a synthetic project through the tools and through the backend service functions, then compare the files (ignoring timestamps and ids listed in the test).
  - acceptance: `mcp-parity` is in the gate and green; each tool has a unit test.

- [ ] **HRN-10** CLI `epc_cli` over the same core.
  - deps: HRN-09 · label: `feat/HRN-10-cli`
  - `python -m epc_cli <tool> --project CLIENT/CODE --json <args>`: one subcommand per MCP tool, same JSON in and out.
  - acceptance: CLI tests mirror the MCP tests.

- [ ] **HRN-11** Guards and the read-only profile.
  - deps: HRN-09 · label: `feat/HRN-11-mcp-guards`
  - See also HRN-34, HRN-35, HRN-36, HRN-30 (engineering review 2026-11-10).
  - Writes are limited to `<project>/workspace/`, `<project>/deliverables/` and `<project>/.epc/`. The `EPC_MCP_PROFILE=readonly` profile exposes only the read and recalculation tools; `recalc_board` works on a temporary copy. Every estimate returns `reason` and `confidence`.
  - acceptance: tests prove a write outside the project fails and that the read-only profile cannot write.

### Phase 3 · Roster and model routing

- [ ] **HRN-12** Roster file, schema, generator and gate check.
  - deps: HRN-03 · label: `feat/HRN-12-roster`
  - `claude/harness/roster.json` from `seeds/roster.seed.json`, `shared/schemas/roster.schema.json`, `tools/build/regen_agents.py` (writes the frontmatter of `harness/.claude/agents/<name>.md`, keeping the body), and a gate check `roster`.
  - acceptance: changing a model in the roster and running the generator changes only that agent's frontmatter; the gate fails when they differ.

- [ ] **HRN-13** Shared prompts.
  - deps: HRN-12 · label: `chore/HRN-13-shared-prompts`
  - `harness/.claude/prompts/rules.md` (no invented data, one source of truth, unreviewed values, citations, language) and `harness/.claude/prompts/findings.md` (how to report a finding). The generator injects a reference into each agent body; the copied rule blocks are removed from the agents.
  - acceptance: no agent repeats the rule block; the gate is green.

- [ ] **HRN-14** Runtime agents per the roster; specialists become skills.
  - deps: HRN-13, HRN-02 · label: `feat/HRN-14-runtime-agents`
  - See also HRN-65, HRN-66, HRN-67 (engineering review 2026-11-10).
  - Create the five runtime agents of the roster (`plan-reader`, `electrical-designer`, `spec-writer`, `input-verifier`, `standards-reviewer`) plus `final-auditor`, disabled. The `orchestrator` is the main session and has no agent file.
  - Turn the 12 `electrical-*` specialists into skills `check-*` (cable sizing, protection, earthing and lightning, lighting, motors, backup and reactive, switchboard, drawings, loads, materials). Their bodies become the checklists, owned by a new plugin `epc-harness`, which `HRN-28` packages. Then move the 12 specialist agent files and the 33 non-electrical agents to `harness/.claude/agents/_on-hold/` with `SNAP move`.
  - acceptance: `check_skill_conflicts.py` is clean; every roster agent exists; the gate is green.

- [ ] **HRN-15** Ledger of model use and the cost report.
  - deps: HRN-09, HRN-12 · label: `feat/HRN-15-usage-ledger`
  - Each stage appends `{stage, agent, model, effort, input_tokens, output_tokens, started, ended}` to `<project>/.epc/ledger/harness.jsonl` through an MCP tool `ledger_record`. `cost_report` writes the per-agent table to the run sheet. Prices are a data file the owner fills in; no prices are invented (empty → tokens only).
  - acceptance: unit tests; the report renders tokens when no price file exists.

### Phase 4 · `/init`

- [ ] **HRN-16** Skill `/init`: the form.
  - deps: HRN-11, HRN-14 · label: `feat/HRN-16-init`
  - `SPEC.md` §8: blocks, questions, the mapping from checkboxes to `document-catalog.json` keys, and writing through the MCP tools only. The form writes structured requirements and loads directly; there is no intake agent.
  - acceptance: an eval script answers the form for one synthetic project and the resulting input files match what the backend creates for the same data.

- [ ] **HRN-17** Confirmation summary and assumptions.
  - deps: HRN-16 · label: `feat/HRN-17-init-summary`
  - Before any calculation: a summary with the data, the missing critical items (asked) and the assumed minor items (recorded in `workspace/00-setup/assumptions.json` with `reason` and `confidence`).
  - acceptance: `/run` refuses to start without a confirmed summary.

- [ ] **HRN-18** Plan intake.
  - deps: HRN-16 · label: `feat/HRN-18-plan-intake`
  - DXF, vector PDF and images through `arch_read`. DWG: document the conversion with ODA File Converter or LibreDWG as an owner-side step, and detect DWG to answer with those instructions. Do not bundle a converter.
  - acceptance: synthetic DXF and PNG fixtures go through; a DWG gets the instructions.

### Phase 5 · `/run`

- [ ] **HRN-19** Skill `/run`: the seven stages.
  - deps: HRN-12, HRN-17, HRN-18 · label: `feat/HRN-19-run`
  - See also HRN-62, HRN-63, HRN-64 (engineering review 2026-11-10).
  - `SPEC.md` §3. Stages 2, 3, 4 and 6 are delegated to their roster agents; stages 1, 5 and 7 are done by the orchestrator with tools only.
  - acceptance: one synthetic project goes from a confirmed `/init` to a draft package with no questions asked.

- [ ] **HRN-20** Stage contracts and resumable state.
  - deps: HRN-19 · label: `feat/HRN-20-run-state`
  - Precondition, deterministic validation (for example `sld/validation.py`) and state in `.epc/state/harness.json` for each stage. `/run` resumes from the first stage that is not done.
  - acceptance: killing a run mid-way and starting it again finishes without redoing finished stages.

- [ ] **HRN-21** Stop rules.
  - deps: HRN-20 · label: `feat/HRN-21-run-gates`
  - See also HRN-60, HRN-62 (engineering review 2026-11-10).
  - Stop only on a missing critical datum or a `blocking` finding. Everything else is recorded and the run goes on.
  - acceptance: tests for both stop cases and one non-stop case.

### Phase 6 · Verifiers

- [ ] **HRN-23** Finding schema.
  - deps: HRN-03 · label: `feat/HRN-23-finding-schema`
  - See also HRN-61 (engineering review 2026-11-10).
  - `shared/schemas/finding.schema.json` from `seeds/finding.schema.json`. MCP tool `findings_write` validates against it.
  - acceptance: schema tests pass.

- [ ] **HRN-22** Deterministic checks and the two verifier agents.
  - deps: HRN-14, HRN-19, HRN-23 · label: `feat/HRN-22-verification`
  - See also HRN-60, HRN-61 (the deterministic electrical checks move to code; the agent only adds findings) (engineering review 2026-11-10).
  - Package `epc_checks` (with tests) and MCP tool `checks_run`: `format-check`, `calc-check` (recalculation on a temp copy compared with the stored results) and `document-check` (SLD, memos, cable list, load schedule and material list agree). No model.
  - `input-verifier`, then `standards-reviewer`, as in `SPEC.md` §6–§7: read-only profile. The reviewer merges every finding and writes `workspace/03-review/review-sheet.md` (in the project locale) and `findings.json`.
  - acceptance: on each golden project, each check or agent catches its seeded error (`SPEC.md` §11).

### Phase 7 · Review loop

- [ ] **HRN-24** Skill `/review`.
  - deps: HRN-21, HRN-22 · label: `feat/HRN-24-review`
  - Free-text corrections become data changes through MCP tools. `impact_map` picks the stages to re-run; the next revision letter is issued with a change sheet.
  - acceptance: changing one load's power re-runs only its board, the studies that use it and their documents.

- [ ] **HRN-25** Skill `/approve`.
  - deps: HRN-24 · label: `feat/HRN-25-approve`
  - See also HRN-62, HRN-71 (engineering review 2026-11-10).
  - Issues IFA or IFC through the existing issuing module (transmittal, DXF stamp, ledger). IFC needs explicit owner confirmation in the session. The optional `fable` audit runs only if D5 enables it.
  - acceptance: an end-to-end test issues IFA for a golden project.

### Phase 8 · Evals, hooks, packaging

- [ ] **HRN-26** Golden projects and model comparison.
  - deps: HRN-22, HRN-25 · label: `feat/HRN-26-evals`
  - Three to five synthetic projects in `harness/.claude/evals/projects/` (no data from `local/`), with seeded errors (`SPEC.md` §11) and expected findings. `harness/.claude/evals/run_evals.py` and a gate check that runs the fast deterministic part. Cost report: run each golden project once and write `harness/.claude/evals/cost-report.md` with tokens per agent from the ledger (target from the 2026-11-10 estimate: about 7 USD per 100-circuit project with one review round). It advises and changes nothing.
  - acceptance: every seeded error is caught; the report exists.

- [ ] **HRN-27** Hooks.
  - deps: HRN-21 · label: `feat/HRN-27-hooks`
  - `hooks/hooks.json` of the plugin `epc-harness`: PreToolUse blocks Write and Edit outside the project folders during `/run`; PostToolUse validates the state after each stage tool; Stop refuses to end `/run` without `findings.json`.
  - acceptance: hook tests (scripts called with sample payloads).

- [ ] **HRN-28** Package `epc-harness`.
  - deps: HRN-26, HRN-27 · label: `feat/HRN-28-package`
  - Plugin manifest, skills (`init`, `run`, `review`, `approve`, `check-*`), agents, `.mcp.json` for the `epc` server, hooks and the roster. Built with `tools/build/epc_build.py` and validated with `claude plugin validate --strict` in CI. Plugin agents ignore `hooks`, `mcpServers` and `permissionMode`, so restrict tools per agent only.
  - acceptance: validation passes; installed into a temporary clean folder, it runs one golden project end to end.

- [ ] **HRN-29** HRN-00 leftovers.
  - deps: HRN-00 · label: `chore/HRN-29-hrn00-leftovers`
  - Archive `docs/harness/CLAUDE.harness.md` to `docs/harness/archive/` with `SNAP move` (needs the snapshot command to be allowed). The empty folder `harness-loop/` is locked by Windows: the owner deletes it by hand. The HRN-00 folder move is missing from its snapshot manifest (see PROGRESS entry 3).
  - acceptance: `docs/harness/archive/CLAUDE.harness.md` exists and the copy in `docs/harness/` is gone.

### Phase 9 · Engineering review (2026-11-10)

Source: `docs/harness/ENGINEERING_REVIEW.md` (findings F1 to F28) and `docs/harness/SPEC.md` §14. The owner answered D1–D26 on 2026-11-10 (`docs/harness/DECISIONS.md`); tasks say «Decided: Dnn». A task marked **(Frozen: D15)** or **(Frozen: D26)**, or **(blocked until the owner verifies the values involved)**, is treated like an **(Owner)** task. Tasks that change a calculation also change golden values: per D27 the golden and expected values are regenerated once, in HRN-75, with a difference report per decision; the loop never edits expected values on its own. HRN-30 to HRN-33 are safety fixes of the loop itself and now run first (Phase 0b).

#### (a) Harness safety

HRN-30 to HRN-33 now sit in Phase 0b (above), before HRN-09, so the loop does them first.

#### (b) MCP server

- [ ] **HRN-34** Write guard wired, true read-only profile, read-only default.
  - deps: HRN-09 · label: `fix/HRN-34-mcp-guard`
  - Call `guard.check_write` (`harness/src/platform/mcp/src/epc_mcp/guard.py:33`, no caller today) from every write path. Read tools must not write: `boards_list` and `layout_get` reach `repository.migrate_legacy` (`sld/repository.py:75,93`), which moves files; give the read-only profile a path that reports the legacy layout without moving it. Default profile `readonly` (`__main__.py:15`). (F18)
  - acceptance: an old single-board project read in `readonly` keeps every file byte-identical (tree hash); a write tool aimed outside the allowed folders returns `forbidden_path`; starting without `EPC_MCP_PROFILE` gives `readonly`.

- [ ] **HRN-35** Per-project norms, loud criteria errors, argument validation.
  - deps: HRN-09 · label: `fix/HRN-35-mcp-reads`
  - `norms_pending` is platform-wide (`read_tools.py:100-102`): return the units and register ids the project's disciplines use (later, the run manifest), and say which. `criteria_get` must return `{ok:false}` when the catalog cannot be read (`engineering/public.py:18-31` swallow every exception). The registry validates arguments against each tool's declared schema before calling it. (F18)
  - acceptance: a project with one discipline lists only its units; a broken catalog gives an error, not `{}`; a wrong-typed argument gives `invalid_arguments` for every tool.

- [ ] **HRN-36** Idempotent writes and a project lock.
  - deps: HRN-09 · label: `fix/HRN-36-mcp-idempotent`
  - `loads_add` appends with no key (`write_tools.py:72-79`) and `intake_add` can duplicate: add an idempotency key (or stable row hash) and a per-project lock file in `.epc/` with a stale-lock timeout around read-modify-write of loads, intake and board declarations. (F18)
  - acceptance: the same `loads_add` twice adds once; two concurrent processes lose no row.

- [ ] **HRN-37** MCP tests, import contract and dependencies in the gate.
  - deps: HRN-09 · label: `chore/HRN-37-mcp-gate`
  - Gate check `mcp` runs `harness/src/platform/mcp/tests` with the right paths (`tools/ci/run_gate.py` has no `mcp` reference); an import-linter contract that only `backend_link.py` imports the backend; declare dependencies in `harness/src/platform/mcp/pyproject.toml` (`dependencies = []`) or document the install. (F18)
  - acceptance: the new check is green in the gate; the other 38 checks are no worse than the baseline.

#### (c) Norm register and norm data

- [ ] **HRN-38** Adopt the norm register in the gate.
  - deps: — · label: `chore/HRN-38-register-gate`
  - The register exists (`shared/schemas/norm-register.schema.json`, `engine/*/src/*/norm_register/*.json`, `tools/build/norm_register.py`, `harness/docs/NORM_REGISTER.md`). Add `python tools/build/norm_register.py --report --check` as gate check `norm-register` (fails when a record is invalid or `harness/docs/NORM_REGISTER.md` is out of date), and add `norm_register/*.json` to `package-data` in each engine's `pyproject.toml` so built plugins carry it. The code-constant part for `aea90364` is still being completed by its author. (F12, F15)
  - acceptance: the check is green and fails when a register file or the generated doc is edited by hand; a built plugin contains the register files.

- [ ] **HRN-39** One schema for norm data.
  - deps: HRN-38 · label: `feat/HRN-39-norm-schema`
  - Schemas for `aea_tables.json`, `design-criteria.json`, `review.json` and `review-log.jsonl`; one rule shape, one norm-id form and one status vocabulary across `AP/rules/*.json`, `engine/standards`, lighting rules and criteria (today at least: `grupo/reglas` files and an index shape, `estado` texts in rules, `approved|pending|stale` in review, a `validated` flag in criteria). Migration maps old values; no value changes. (F15)
  - acceptance: all norm data validate in the gate; golden results unchanged.

- [ ] **HRN-40** Review state keyed by register id.
  - deps: HRN-39 · label: `feat/HRN-40-review-by-id`
  - Review points use `unit|point` strings (for example `criterion:ar-electrical|board_height_m`); key them by register id in every unit so `norms_pending`, run manifests and the acceptance of §14.4 list every unreviewed value a project used. Derive `design-criteria.json` `validated` from the review state (today `false` with 15 approved). No approval is made. (F11, F15)
  - acceptance: every register id resolves to one review state; `validated` follows the review; no point changes state.

- [~] (2026-11-10) **HRN-41** Earthing and shock-protection values to JSON. **(blocked until the owner verifies the values involved: D11, D12, D25)**
  - Decided: D11, D12, D25 (2026-11-10): TT 24 V / min(0.5·24/IΔn; 40 Ω); k from Table 771.19.II; TN sectional 2 s (5 s only with selectivity); one disconnection table. The norm values themselves still need the owner's verification.
  - deps: HRN-39 · label: `refactor/HRN-41-values-earthing`
  - Move to `aea_tables.json` and the register: `aea_earthing.py` (`UL_V`, `RA_MAX_OHM`, `TIEMPOS_DESCONEXION_S`, `T_SECCIONAL_S`), `aea_protection.py` defaults (50 V, 230 V, 400 V), `board_memo.py` (`UL_V`, `U0_V`), `cable_thermal.K_ADIABATICO`, `aea_conductors.K_TABLA_771`. One copy of the disconnection table. Both today's TT values stay, each under its own register id, until HRN-49 decides. (F4, F5, F6, F12)
  - acceptance: no norm value of these files remains in Python; the golden tests pass with no edit to expected values.
  - Done 2026-11-10 (ENG-14): `aea_earthing.py` (`UL_V`, `UL_COL1_V`, `RA_MAX_OHM`, `TIEMPOS_DESCONEXION_S`, `T_SECCIONAL_S`, the 0.5 adoption factor, selectivity time), `cable_thermal.py` (`K_ADIABATICO`, `T_ADIABATICO_MAX_S`, `T_CORTO_S`; k now unified with `aea_conductors.k_adiabatico_771`) and `board_memo.py` (`K_MAG`, `RATIO_TERMICO`, trip-band times) read `aea_tables.json`; the TT 50 V defaults of `aea_protection` and `board_memo.UL_V` were removed by D11 (see HRN-49). 23 new constants in `/constantes` (93 table/constant review points; `test_norms_api.py` expects 93).
  - Left: `U0_V = 230.0` in `board_memo.py`, `u0_v=230.0` and `u_v=400.0` defaults in `aea_protection.py` (they wait for D16); the electrode formula coefficients of `aea_earthing.py` (frozen by D26 / formula structure) and the Sverak default depth; `board_memo` curve letters per topology and the 63 A upstream-curve rule; `rules/proteccion_choques.json` still holds its own copy of the disconnection times (`tiempos_tabla_41_3`, `tn_s_tiempo_2s`, `tt_tiempo_1s`); the values are unverified by the owner.

- [~] (2026-11-10) **HRN-42** Short-circuit and protection constants to JSON. **(blocked until the owner verifies the values involved)**
  - deps: HRN-39 · label: `refactor/HRN-42-values-shortcircuit`
  - `short_circuit.py` (`C_MAX_BT_TOL_6`, `C_MAX_BT_TOL_10`, the `[VERIFICAR]` factors), `aea_icc_factors.py`, `aea_icc_decay.py`, `aea_pipeline.py` constants (`SERIE_IN_A`, `SERIE_ICU_KA`, `MARGIN_MOTOR`, `DU_ACUM_MAX_PCT`, `K_MAGNETICO_C`); the duplicate `c_fuente_max` of `aea_tables.json`. (F12)
  - acceptance: as HRN-41.
  - Done 2026-11-10 (ENG-14): `short_circuit.py` (`C_MAX_BT_TOL_6`/`C_MIN_BT` now read `impedancias_estandar.c_fuente_max`/`c_tension_min`; `C_MAX_BT_TOL_10`, `TEMP_MIN_C`, `XR_RED_DEFECTO`, `UMBRAL_MOTORES_DESPRECIABLE`, K_T and kappa coefficients), `aea_icc_factors.py` (`C_MAX_RED`, `RIGIDO_MAX_U_RATIO`, `LIM_MOTORES_*`) and `aea_icc_decay.py` (`U_FMAX`) read `aea_tables.json`; also `aea_special_locations.py` (701/722/EV limits) and the 3.0 x height rule of `aea_lightning.py`. `impedancia_red` now has `x_r=None` meaning the default ratio.
  - Left: `aea_pipeline.py` constants (`C_MAX_BT`, `C_MIN_BT`, `SERIE_IN_A`, `SERIE_ICU_KA`, `MARGIN_MOTOR`, `DU_ACUM_MAX_PCT`, `K_MAGNETICO_C`) and `aea_export.py` (later tasks); the n-factor structure of `aea_icc_decay.factor_n_simplificado` (coefficients derived from 0.1); `MU0` (physics); the values are unverified by the owner.

- [~] (2026-11-10) **HRN-43** Conductor, ampacity and voltage-drop constants to JSON. **(blocked until the owner verifies the values involved: D17, D18)**
  - Decided: D17, D18 (2026-11-10): Accumulated drop limits (lighting 3 %, receptacles 3 %, sectional 1 %, motors 5 %); reject outside grouping tables. The norm values themselves still need the owner's verification.
  - deps: HRN-39 · label: `refactor/HRN-43-values-conductors`
  - `aea_conductors.py` (R20, `ALFA_CU`, `PEN_MIN_MM2`, X), `aea_voltage_drop.LIMITES_PCT` against `771.19_limites_caida_pct`, the grouping caps of `aea_tables.py:145-158`. (F9, F12, F13)
  - acceptance: as HRN-41.
  - Done 2026-11-10 (ENG-13): single source with no change of any result (same values and types; old and new modules give identical output on a 27,778-line battery). `aea_conductors.py` (`SECCIONES_MIN_MM2`, `PEN_MIN_MM2`, `K_TABLA_771`, `IZ_771_16_I`, `R20_CU_OHM_KM`, `ALFA_CU`, `X_CABLE_OHM_KM`, `FACTORS_HARMONICS`, PE steps, neutral threshold), `aea_ampacity.py` (`SECCION_MIN_AL_MM2`, `ALFA`, `R20_AL_OHM_KM`, `TEMP_CONDUCTOR_C`, method-to-table and grouping maps, class-5 factor also in `aea_tables.iz_corregida`), `aea_route.py` (`KINDS`, `DEPTH_REFERENCE_M`), `aea_voltage_drop.py` (`VA_KM_TABLA`, `GDC_*`, `LIMITES_PCT`, lighting fractions, 25/70 mm2 start-drop cut, default voltages) and the 70 mm2 limit of `aea_motor.py` now read `aea_tables.json` (module names built from the JSON on access, refreshed by `limpiar_cache_tablas`). 31 new constants in `/constantes` (+31 pending review points; norms page and `harness/docs/REVISION_NORMAS.md` regenerated, register updated). Test: `tests/test_single_source.py`.
  - Left: the values are still unverified by the owner (the task stays `[~]`); `aea_pipeline.py`, `aea_export.py` (commercial series, 5 % thresholds) and `cable_thermal.K_ADIABATICO` are untouched; the `un_v=220.0` default in the signature of `aea_voltage_drop.drop_by_table` stays; the grouping caps inside `aea_tables.py` (`factor_agrupamiento_enterrado` uses min(n, 6); the air table uses its last column) and the validation bounds of `aea_route.validate` are not moved; backend test `test_norms_api.py:54` expects 39 table/constant points and must become 70.

- [~] (2026-11-10) **HRN-44** Demand, panel-thermal, motor, reactive and lightning-protection constants to JSON. **(blocked until the owner verifies the values involved: D14, D16)**
  - Decided: D14, D16 (2026-11-10): Simultaneity per D14; 230/400 V and 220/380 V with U0 by project system. The norm values themselves still need the owner's verification.
  - deps: HRN-39 · label: `refactor/HRN-44-values-demand`
  - `aea_demand.py` (`U_MONO_V`, simultaneity tables), `aea_panel_thermal.py` (`_K_CIRCUITOS`, `_PD_POLO`, `_PDC_DIF`: the second diversity table), `aea_motor.py`, `aea_reactive.py`, `aea_lightning.py`. (F12, F13)
  - acceptance: as HRN-41.
  - Done 2026-11-10 (ENG-13): `aea_demand.py` (`U_MONO_V`, `U_TRI_V`, `VA_BOCA_*`, `VA_TUG`, `VA_TUE`, `COEF_GRADO_771`, `COEF_CIRCUITS_770`, `DESEQUILIBRIO_MAX_PCT`, `_GRADOS_771`, 770 grade limits, `_CONJUNTOS_771_III`, three-phase thresholds, parallel factors, 1.25 motor feeder factor) and `aea_panel_thermal.py` (`K_E`, `K_CABLEADO`, `_K_CIRCUITOS`, `_PD_POLO`, `_PDC_DIF`) now read `aea_tables.json`; the new keys are in `/constantes`, the register and the norms page, results unchanged (same battery as HRN-43). Test: `tests/test_single_source.py`.
  - Left: D14/D16 and the owner's verification (default voltages keep 220/380 V until D16 is applied); `aea_reactive.py`, `aea_lightning.py`, `aea_backup.py` and the rest of `aea_motor.py` (already JSON) were not part of ENG-13; the second diversity table of `_PDC_DIF` still needs its unit confirmed.

- [ ] **HRN-45** Values of the other engines: single sources and conflicts. **(Frozen: D15)**
  - FROZEN (D15, owner 2026-11-10): Raceway-fill values and expected values tied to fill stay untouched until the owner verifies the AEA clause (35 % vs 40 %). The loop skips this task like an (Owner) task.
  - deps: HRN-39 · label: `refactor/HRN-45-values-others`
  - Lighting (`standards/D351-79.json` vs `data/levels.json`), receptacles (sources, bedroom under 10 m2 giving 3 outlets against 2 in reference case `r1`, corridor `r4`, flattened bedroom/corridor/kitchen rules), HVAC (`typical.json`; solar gains N = 100 / S = 200 W/m2 to verify for the southern hemisphere), plan `typical-values.json` fill limits, and the raceway fill conflict (35 / 40 / 53-31-40). The six criteria no calculation reads (heights, `board_spare_pct`, `raceway_fill_max_pct`, `frequency_hz`) either get a reader or are marked report-only. (F12, F13, F27, F28)
  - acceptance: one source per value; golden results unchanged until the owner answers D15.

- [ ] **HRN-46** Which copy of the rules is the register. **Decided: D19 (2026-11-10).**
  - Decision (D19, owner 2026-11-10): Unify the rules, validate against AEA and retire the redundant copy (the drafts under `local/`). The standards' PDFs are not deleted (the owner removes them himself) and are never versioned.
  - deps: HRN-38 · label: `chore/HRN-46-rules-copy`
  - Implement the answer to D19: one copy of the 177 rules, the other retired or merged through the promotion pipeline, with a diff report of what differs. No rule text is read from `local/` by the loop; the owner supplies the comparison. (F15)
  - acceptance: one authoritative copy; the gate fails if a second copy drifts.

- [ ] **HRN-47** Apply the six summary paraphrases. **(blocked until the owner confirms the paraphrases and the overlap check)**
  - deps: HRN-39 · label: `chore/HRN-47-paraphrases`
  - Apply `engine/standards/src/epc_standards/data/summary_fixes.json` to `AP/rules/` for `bandejas.altura_montaje`, `circuitos.equilibrio_trifasico`, `enterrados.profundidad_cables_directos`, `interruptores.distancia_al_marco`, `tableros.montaje_componentes`, `tomacorrientes.ev_una_acometida`. Text only. (F16)
  - acceptance: the six `regla` texts equal the paraphrases; their `parametros` and every other rule are byte-identical; rule tests green.

- [ ] **HRN-48** Fix the overstated documents.
  - deps: — · label: `docs/HRN-48-overstated-docs`
  - `harness/docs/FUENTES_NORMAS.md` (parts 2, 4, 4-42, 90909-1 and the missing standards: AEA 90909-0, Decreto 351/79 text, IEC 60364-5-52), `engine/aea90364/docs/09-tablas-normativas.md` («verificada» column), ADR-0011 counts, ADR-0012 paths and its «Project criteria overrides» row (append an amendment, do not rewrite), `SPEC.md` §8 criteria path. Documents only. (F17)
  - acceptance: every path named exists; counts match `harness/docs/REVISION_NORMAS.md`.

#### (d) Calculation closure

Each task: tests first, the golden and reference-case differences listed in PROGRESS, new expected values approved by the owner.

- [x] (2026-11-10) **HRN-49** TT earth resistance in the memo. **Decided: D11 (2026-11-10).**
  - Decision (D11, owner 2026-11-10): TT: UL = 24 V and Ra = min(0.5·24/IΔn; 40 Ω) in every module (memo, protection, earthing).
  - deps: HRN-41 · label: `fix/HRN-49-tt-ra`
  - `board_memo.py:40,137,344` and `aea_protection.ra_maxima_tt` use 50 V; make them read the single value chosen in D11. (F4)
  - acceptance: reference cases `j_tt_ra_*` agree; memo text matches; golden diff listed.
  - Done 2026-11-10 (ENG-14): `aea_earthing.ra_maxima` is the only function (UL 24 V, factor 0.5 and 40 Ω from `aea_tables.json`); `aea_protection.ra_maxima_tt`/`verifica_tt` (UL default `None` = the adopted value; the 50 V column only with an explicit `ul_v`) and `board_memo` (`ra_max_tt_ohm`) call it. The six `j_tt_ra_*` cases agree. Golden differences: `golden/core.json` (`tt|*`), `golden/memo.json` (`groups_tns`, `it_system_unvalidated`), listed in the ENG-14 report for HRN-75.

- [x] (2026-11-10) **HRN-50** k for PVC above 300 mm2. **Decided: D12 (2026-11-10).**
  - Decision (D12, owner 2026-11-10): Adiabatic k from Table 771.19.II, including PVC above 300 mm² (Cu 103, Al 68).
  - deps: HRN-41 · label: `fix/HRN-50-k-pvc`
  - `cable_thermal.k_material` reads the 771.19.II table (section-dependent). (F5)
  - acceptance: reference cases `f1`, `f2` agree.
  - Done 2026-11-10 (ENG-14): one lookup, `aea_conductors.k_adiabatico_771(aislacion, material, seccion_mm2=None)` (names `pvc`/`xlpe` plus the full table keys; `pvc` with a section above 300 mm2 gives Cu 103 / Al 68; `None` behaves as up to 300 mm2); `cable_thermal.k_material(material, aislacion, seccion_mm2=None)` calls it. Cases `f1`, `f2` agree. No engine caller of `k_material` knows a section today (the pipeline does not call `cable_thermal`): the callers that will use it must pass the section.

- [ ] **HRN-51** Checks that decide: I2, k2S2, minimum Icc. **Decided: D13 (2026-11-10).**
  - Decision (D13, owner 2026-11-10): I2 ≤ 1.45·Iz, k²S² and breaking capacity DECIDE the result; Zs and minimum Icc are REPORTED. Without a manufacturer curve k²S² uses the most unfavourable time of the normative band (D28) and the memo says so.
  - deps: HRN-49, HRN-50 · label: `feat/HRN-51-closing-checks`
  - In `aea_pipeline.calculate` evaluate I2 ≤ 1,45·Iz (`aea_protection.in_max_por_iz`), k²S² (`cable_thermal.verificar_i2t`) and minimum Icc against the magnetic threshold; return them in `detalle` as `checks[{id, value, limit, ok, anchor}]`; they raise the section or protection, or only report, as D13 says. (F1)
  - acceptance: `p2_pipeline_no_evalua_i2` agrees; a seeded circuit with Iz just above In is flagged; golden diff listed.

- [ ] **HRN-52** Demand in board and feeder current. **Decided: D14 (2026-11-10).**
  - Decision (D14, owner 2026-11-10): Dwellings: Table 771.9.II. Offices, shops, service buildings, industry: the factor defined per board or project, else Table 771.9.III. Terminal circuits at full load. Applies to boards, feeders, sectional lines and incoming supplies.
  - deps: HRN-44 · label: `feat/HRN-52-demand-current`
  - Apply the answer to D14 in `aea_pipeline._ib` (`:378`) and the `DEMAND` row; record the factors used in the result. (F3)
  - acceptance: reference case `q1` agrees with the chosen option; golden diff listed.

- [~] (2026-11-10) **HRN-53** Zs with minimum Icc, real temperature and one U0; PE section. **Decided: D13, D16 (2026-11-10).**
  - Decision (D13, D16, owner 2026-11-10): Zs maximum with c_min = 0.95 in every module (Zs is reported, not deciding). U0 is the phase-to-earth voltage of the project system (230/400 → 230 V; 220/380 → 220 V), never mixed. Per the case verdicts: PE minimum 2.5 mm² and round up to the next commercial section (47.5 → 50 mm²).
  - deps: HRN-41 · label: `fix/HRN-53-zs`
  - `zs.py` and `aea_earthing.zs_lazo`: add the upstream feeder impedance, replace the fixed 1.2 factor (`aea_tables.json:3014`) by the conductor temperature, take U0 from the nominal voltage set (D16, not `round(Un/√3)`); the pipeline's `current_sc_min` (`aea_pipeline.py:467`) uses the minimum followed Icc; `seccion_pe_mm2` (returns 1.5 mm2 for 1.5 mm2) agrees with `aea_conductors.pe_section` (minimum 2.5 mm2). (F7)
  - acceptance: reference cases `l4`, `s1`, `s2` agree; golden diff listed.
  - Done 2026-11-10 (ENG-14): `aea_earthing.seccion_pe_mm2` now calls `aea_conductors.pe_section` (minimum 2.5 mm2; S/2 rounded up to the commercial series, 47.5 -> 50); `aea_protection.verifica_tn` and the `board_memo` `zs_max_ohm` use `aea_earthing.zs_maxima` (c_min = 0.95). Cases `l4`, `s1`, `s2` agree.
  - Left: the upstream feeder impedance, the conductor temperature instead of the fixed 1.2 factor, the minimum Icc of `current_sc_min`, and D16 (one U0 from the project system; `u0_v=230.0` defaults stay in `aea_protection.verifica_tn` and `board_memo.U0_V`).

- [ ] **HRN-54** Rod formula. **(Frozen: D26)**
  - FROZEN (D26, owner 2026-11-10): The simplified rod formula is neither removed nor corrected until its normative and technical origin is identified. The loop skips this task like an (Owner) task.
  - deps: HRN-41 · label: `fix/HRN-54-rod`
  - Apply D26 to `aea_earthing.resistance_rod(simplificada=True)` (`:81-92`); production already uses the full formula, so no deliverable changes. (F8)
  - acceptance: reference cases `m_jabalina_*` agree or the branch is gone.

- [ ] **HRN-55** Breaking capacity from the followed Icc; motors, neutral, harmonics. **Decided: D13 (2026-11-10).**
  - Decision (D13, owner 2026-11-10): Breaking capacity DECIDES the result (from the followed maximum Icc); minimum Icc is REPORTED.
  - deps: HRN-42 · label: `feat/HRN-55-breaking-capacity`
  - Use the followed maximum Icc (`barsicc.follow`) instead of the declared one (`aea_pipeline.py:351-353`, `studies.py:59`); add motor contribution (`short_circuit.aporte_motor`); treat `3F+N` as its own case (`_fases`, `aea_pipeline.py:169`); neutral current and harmonic derating (`aea_conductors`). (F2)
  - acceptance: a board whose followed Icc exceeds the declared one is flagged; golden diff listed.

- [ ] **HRN-56** Nominal voltage set and drop limits. **Decided: D16, D17 (2026-11-10).**
  - Decision (D16, D17, owner 2026-11-10): 230/400 V at the transformer secondary, 220/380 V at points of use; U0 follows the project system. Drop limits are ACCUMULATED from the origin to the point of use: lighting 3 %, receptacles 3 %, sectional 1 %, motors in steady state 5 %; motor starting separate, 15 % maximum.
  - deps: HRN-43 · label: `fix/HRN-56-voltage-limits`
  - One voltage set and one meaning for the 3 % and the 2 % recommendation across `aea_demand`, `board_memo`, `zs.py`, `aea_tables.json:2889-2895` and the criteria options. (F13)
  - acceptance: one U0 and one limit source; golden diff listed.

- [ ] **HRN-57** Default insulation, D2 column and grouping beyond the tables. **Decided: D6, D18 (2026-11-10).**
  - Decision (D6, D18, owner 2026-11-10): Insulation by circuit role: feeders, incoming supplies, sectional lines XLPE; terminal lighting and receptacle circuits PVC; special terminal circuits may state another one; no global default. Grouping outside the tables: reject and ask for the datum (no interpolation); buried D2 requires the explicit installation method.
  - deps: HRN-43 · label: `fix/HRN-57-defaults`
  - Engine default insulation per D6 (E2-13: changes 28 tests); D2 column and grouping caps/interpolation (`aea_tables.py:145-158`, `aea_ampacity.py:150-174`) per D18, with a warning in the result. (F9, F10)
  - acceptance: reference cases `t1`, `h1`, `h2`, `h3`, `i1` agree with the chosen option.

- [ ] **HRN-58** Stale memos when criteria, norm review or engine change. **Decided: D21, D22 (2026-11-10).**
  - Decision (D21, D22, owner 2026-11-10): Corporate criteria with signed per-project exceptions (part of the stale hash); any unreviewed norm value blocks IFC.
  - deps: HRN-40 · label: `feat/HRN-58-stale-hash`
  - `sld/results.py:73-75` hash adds the criteria digest, the review sha of the register ids used and the engine version. (F11)
  - acceptance: changing a criterion marks the memos stale; unchanged inputs give the same hash.

- [~] (2026-11-10) **HRN-59** Disconnection-time table, one source. **Decided: D25 (2026-11-10).**
  - Decision (D25, owner 2026-11-10): TN sectional disconnection: 2 s, up to 5 s only when selectivity justifies it. One source of truth for the table.
  - deps: HRN-41 · label: `fix/HRN-59-disconnection`
  - One table (today `aea_earthing.py:39-43` and `aea_tables.json:2896`), the sectional TN time per D25 (5 s in code, 2 s in `proteccion_choques.json:125`). (F6)
  - acceptance: reference case `k1` agrees; the owner has checked the 230 V times against the printed standard.
  - Done 2026-11-10 (ENG-14): the table lives only in `aea_tables.json` (`771.18.III_tiempos_desconexion_s`; the code comment said 771.18.I: fixed, and the register carries the issue «verify the official table number»); TN sectional 2 s by default, `tiempo_seccional_max_s(esquema, selectividad=True)` gives 5 s. Case `k1` agrees (0 differences).
  - Left: the owner checks the 230 V times and the table number; `rules/proteccion_choques.json` keeps its own copy of the times and of the 2 s / 5 s rule (read by the rules page, not by the engine functions): merge into one source in a later task.

- [x] **HRN-75** (2026-11-15, edit mode: the owner asked for it, treating the norm values as OK for the simulation; no norm value was approved or changed). The golden files of `aea90364` (`pipeline.json`, `core.json`, `memo.json`) and `drawing` (`drawings.json`) were regenerated with their `--write` scripts; the differences per decision are in `docs/validation/GOLDEN_DIFERENCIAS.md`. Original text: Regenerate golden results once and write the difference report per decision (D27).
  - deps: HRN-49, HRN-50, HRN-51, HRN-52, HRN-53, HRN-55, HRN-56, HRN-57, HRN-58, HRN-59 · label: `chore/HRN-75-golden-regen`
  - Decision D27 (owner, 2026-11-10): golden results are regenerated ONCE, after all calculation corrections are implemented. Write the difference report (what changed, which case or golden value, which decision D6–D25/D28 caused it) and update the reference-case expected values listed there. HRN-54 (D26) and the raceway-fill part of HRN-45 (D15) are Frozen and not in `deps`; if the owner unfreezes them before this task runs, add them to `deps`.
  - Until this task, no iteration edits a golden or expected value (rule in `LOOP.md` §6 stays).
  - acceptance: the golden tests pass with the new values; the report lists every changed value with its decision; the owner reviews it.

#### (e) Harness design

- [ ] **HRN-60** Deterministic electrical checks in `epc_checks`.
  - deps: HRN-22, HRN-39 · label: `feat/HRN-60-electrical-checks`
  - Implement the check list and severity-by-check of `SPEC.md` §14.2 as code (`ib-in-iz`, `i2-1.45iz`, `voltage-drop`, `k2s2`, `breaking-capacity`, `icc-min-trip`, `zs-tn`, `ra-tt`, `rcd-required`, `pe-neutral`, `phase-balance`, `raceway-fill`, `input-complete`, `assumption-used`, `unreviewed-value`), so no agent does them. Checks needing a calculation not yet closed (HRN-49 to HRN-55) report what they can and say which input is missing. `raceway-fill` is **Frozen: D15** and is not built until the owner verifies the clause; `zs-tn` and `icc-min-trip` are reported (D13). (F21)
  - acceptance: each check has a seeded pass and fail; a reviewer agent cannot lower a severity.

- [ ] **HRN-61** Finding schema extension.
  - deps: HRN-23 · label: `feat/HRN-61-finding-fields`
  - Add `check_id`, `norm_ref`, `clause`, `review_state`, `value`, `limit`, `unit`, `evidence` and `severity_source` (`check|reviewer`) to `finding.schema.json`; `findings_write` rejects a finding without an anchor. (F21)
  - acceptance: schema tests; an anchor-less finding is rejected.

- [ ] **HRN-62** Engineer of record and sign-off gates. **Decided: D20, D21 (2026-11-10).**
  - Decision (D20, D21, owner 2026-11-10): One responsible engineer per discipline with formal approval at the four milestones; any unreviewed norm value blocks IFC.
  - deps: HRN-17, HRN-25 · label: `feat/HRN-62-sign-off`
  - `SPEC.md` §14.1 and §14.4: `workspace/00-setup/engineer-of-record.json`, sign-off records with hashes, acceptances file, IFC block. `/run` stops without the record; `/approve` IFC needs the sign-offs current. (F21)
  - acceptance: IFC refused without the engineer of record, with a stale sign-off, or with an unaccepted unreviewed value (if D21 says so).

- [ ] **HRN-63** Run manifest and stage invalidation.
  - deps: HRN-20, HRN-40 · label: `feat/HRN-63-manifest`
  - `SPEC.md` §14.5: write `.epc/runs/<run_id>/manifest.json`; stage input hashes include criteria, register/review sha and engine versions. (F21)
  - acceptance: changing a criterion, a review state or an engine version marks the affected stages stale; the manifest lists model IDs and hashes.

- [ ] **HRN-64** Critical `/init` data. **Decided: D24 (2026-11-10).**
  - Decision (D24, owner 2026-11-10): Available Icc and the earthing scheme are mandatory input data.
  - deps: HRN-16 · label: `feat/HRN-64-critical-data`
  - `SPEC.md` §14.6 in the form and in `input-complete`. (F21)
  - acceptance: the form asks for upstream Icc data and the earthing scheme and `/run` stops when they are missing.

- [ ] **HRN-65** Two MCP server entries.
  - deps: HRN-12, HRN-34 · label: `feat/HRN-65-mcp-entries`
  - The plugin `.mcp.json` declares `epc` (full) and `epc-ro` (`EPC_MCP_PROFILE=readonly`); verifier agents list only `mcp__epc-ro__*` tools (plugin agents ignore `mcpServers`). (F21)
  - acceptance: a verifier agent has no write tool; `claude plugin validate --strict` passes.

- [ ] **HRN-66** Missing roster skills.
  - deps: HRN-12 · label: `feat/HRN-66-roster-skills`
  - Create `aea-calc-conventions`, `consolidate-findings`, `design-circuits`, `harness-conventions`, `produce-drawings`, `read-architecture`, `verify-input` (the eight `check-*` come with HRN-14 and HRN-67). (F21)
  - acceptance: every skill in the roster exists; the `roster` gate check is green.

- [ ] **HRN-67** `check-*` skills with clause anchors; clean agent prompts.
  - deps: HRN-14, HRN-38 · label: `feat/HRN-67-check-skills`
  - Rewrite the `check-*` skills from the 12 `electrical-*` prompts using clauses from the rules files and the register (no clause from memory); drop the repeated rule block (HRN-13); remove the hardcoded «15 %» of `electrical-power-motors-engineer.md:13`; fix or drop the references in `senior-electrical-engineer.md`; give skill-backed agents the tools they need. (F22)
  - acceptance: every checklist item names a register id or rule id; no file refers to a path that does not exist.

- [ ] **HRN-68** Wait for jobs and recover stuck state.
  - deps: HRN-09 · label: `feat/HRN-68-jobs`
  - MCP tools that start background jobs (`sld/jobs.py`) return a job id and a `wait_idle` tool blocks with a timeout; a job saved as `running` by a process that no longer exists is shown as `stuck` and can be restarted. (F21)
  - acceptance: a stage never reads results before its job ends; a killed job is recovered.

- [ ] **HRN-69** Ghost circuits after removing loads.
  - deps: HRN-09 · label: `fix/HRN-69-ghost-circuits`
  - Reproduce first (the review saw it but this pass did not verify it in code). Removing a load removes its circuit from boards and results, or reports it. (F21)
  - acceptance: a test removes a load and finds no circuit for it.

- [ ] **HRN-70** Explicit board defaults. **Decided: D24 (2026-11-10).**
  - Decision (D24, owner 2026-11-10): Available Icc and the earthing scheme are mandatory input data; defaults are never applied silently.
  - deps: HRN-64 · label: `fix/HRN-70-board-defaults`
  - `sld/models.py:9-11,32` defaults (`TN-S`, 10 kA, pf 0.85, 20 m) are never applied silently by the tools: each use is an assumption with reason and confidence. (F21)
  - acceptance: a board created through MCP without those fields lists them as assumptions.

- [ ] **HRN-71** Idempotent issue.
  - deps: HRN-25 · label: `fix/HRN-71-issue-idempotent`
  - Reproduce first (not verified in this pass). Calling `issue_draft`/`issue_final` twice for the same inputs yields one revision and one transmittal. (F21)
  - acceptance: a double call leaves one revision.

- [ ] **HRN-72** Stale statements in `docs/harness`.
  - deps: — · label: `docs/HRN-72-stale-harness-docs`
  - README (counts, `BACKLOG.harness.md`, `scripts/` path), GOAL definition of done (HRN-29 and the new tasks), HRN-00 leftovers note, `STATE.json` iteration versus PROGRESS (**the owner or the loop fixes STATE; this task only reports the mismatch**), duplicate `CLAUDE.harness.md` (HRN-29), glossary seed (D9 removed the migration), `harness/docs/BACKLOG.md` date header. (F23)
  - acceptance: the listed statements match the repository.

#### (f) Reference cases

- [ ] **HRN-73** Adopt the reference-case suite.
  - deps: — · label: `chore/HRN-73-reference-cases`
  - The suite exists (`engine/aea90364/reference_cases/cases/`, 55 cases; `tools/build/reference_cases.py`; `harness/docs/REFERENCE_CASES.md`: 29 agree, 15 differ, 11 without official value). Wire it into the gate as a report that fails only when a case that agreed starts to differ (a baseline file of the 15 known differences, each linked to the HRN task that closes it). (F4, F5, F7, F8, F10)
  - acceptance: the check is green today; breaking an agreeing case turns it red; closing a task removes its case from the baseline.

- [ ] **HRN-74** Official-value cases. **(blocked until the owner provides official worked examples)**
  - deps: HRN-73 · label: `feat/HRN-74-official-cases`
  - Turn the 11 «sin valor oficial» cases and new ones into cases with the official value (worked examples from AEA 90364 or IRAM publications supplied by the owner; none copied from `local/`). (F15)
  - acceptance: each such case cites its source and has an expected value.

#### Owner reminders (never executed by the loop)

- **(Owner)** D15 (raceway fill): verify the AEA clause (35 % vs 40 %). Frozen until then (HRN-45).
- **(Owner)** D26 (rod formula): identify the normative and technical origin of the simplified formula. Frozen until then (HRN-54).
- **(Owner)** E2-05 / E5-04: review the 287 pending norm values and 83 `[VERIFICAR]` marks. Until then every package reports them.
- **(Owner)** PLG-01: approve one specification template. Until then `/run` skips the specification with a note.
- **(Owner)** Fill `claude/harness/prices.json` with model prices if you want costs in money, not only tokens.
- **(Owner)** Any git operation (commit, branch, push) is the owner's, by hand, whenever the owner wants.
- **(Owner)** Provide official worked examples (AEA 90364 or IRAM publications) for HRN-74, and check the 230 V disconnection times against the printed standard (D25).
- **(Owner)** Check that the six paraphrases of HRN-47 keep the meaning and no longer share 12 or more words with the standard text.
- **(Owner)** Obtain the missing standards: AEA 90909-0, the text of Decreto 351/79 and IEC 60364-5-52 (also listed in HRN-48).
- **(Owner)** Verify the HVAC solar gains (N 100 / S 200 W/m2) for the southern hemisphere (HRN-45).
- **(Owner)** Give the engineer-of-record data (name, matrícula, college) for each discipline (D20 is answered); the harness never invents them.
- [ ] **HRN-76** Final migration: fresh repository from zero **(Owner)** - only on the owner's explicit request (D7).
  - deps: the migration is completely finished · label: `chore/HRN-76-fresh-repository`
  - Decision D7 (owner, 2026-11-10): `.git` is NOT deleted, local history is kept and no new repository is created until the migration is completely finished; then a repository is created from zero, on the owner's explicit request. The loop never runs this task.
  - acceptance: done by the owner.

## Siguiente
Harness primero (decisión D1, hasta cumplir `docs/harness/GOAL.md`): la cola `HRN-*` de la sección «Harness (HRN)», en orden. Después, lo de abajo sin cambios.

1. `E2-04` DXF del unifilar al emitir.
2. `E2-05` Constantes a verificar del motor AEA.
3. `E4-02` Pliego técnico eléctrico con el agente Document Writer (espera la estructura de pliego del dueño, `PLG-01`).

## Disciplina eléctrica: hoja de ruta para terminarla

**Dónde estamos (2026-11-08).** Ya funciona el flujo completo: la lista de cargas del cliente, la declaración de los tableros, el análisis, los listados de tableros y de circuitos, y la memoria de cálculo y la síntesis por tablero. La memoria incluye cortocircuito, curvas, selectividad y diferenciales. Ya funcionan el unifilar y el multifilar editables, con historial y confirmación, y los planos de iluminación y de tomacorrientes con sus motores. También están el diseño automático de recorridos, circuitos y canalizaciones, y las hojas por plano, con un plano por piso.
**Lo que falta:**
- Varios documentos del catálogo se suben a mano (`tool: "files"`), aunque el motor ya sabe calcularlos.
- Quedaron cosas a medias en el cálculo y en el dibujo.
- Dos sistemas del catálogo no tienen motor: fuerza motriz y climatización.
- Faltan puesta a tierra, descargas atmosféricas, compensación de reactiva y respaldo (decisión del dueño del 2026-11-08).
- Faltan los entregables finales: informe, pliego, Word y listado de materiales.

### E1 · Documentos que el motor ya sabe hacer
Cada documento deja de ser `files` en `shared/schemas/document-catalog.json`. Se genera desde el modelo del proyecto, se lee en Markdown en Memorias o se ve como tabla, y se emite en PDF o XLSX desde Emitir.
- [x] **E1-01** (2026-11-08) Estudio de cortocircuito (`short_circuit_study`): documento del proyecto generado en Markdown a partir de las memorias de los tableros (resumen por tablero, hallazgos de poder de corte y de disparo magnético, detalle por circuito y supuestos). Se rehace solo cada vez que se genera una memoria; PDF al emitir. La Icc de barras es la declarada en cada tablero → `E1-07`.
- [x] **E1-02** (2026-11-08) Estudio de selectividad (`selectivity_study`): documento del proyecto generado en Markdown desde los pares de protecciones en serie de las memorias de los tableros (resumen por tablero, pares que no son totales con su nota, tabla de pares con relación térmica y corriente hasta la que son selectivos). Se rehace con cada memoria; PDF al emitir. Las curvas de los fabricantes siguen siendo bandas normativas.
- [x] **E1-03** (2026-11-08) Lista de cables (`cable_list` y los `*_cables` de iluminación, tomacorrientes, climatización y fuerza motriz): una fila por cable (tablero, desde, hasta, sistema, cable como lo escribe el unifilar, sección, conductor, aislación, método, largo que usa —el del plano o el del tablero—, In, Ib, caída y si cumple), generada de las memorias de los tableros; XLSX al emitir. Falta la canalización de cada cable (viene del plano) → `E2-02`.
- [x] **E1-04** (2026-11-08) Planilla de cargas (`load_schedule`): una fila por circuito de cada tablero (carga, fases, tensión, Ib, In y potencia aparente) y un TOTAL por tablero que suma los circuitos con cargas (no el alimentador de un grupo); generada de las memorias de los tableros, XLSX al emitir. Falta el reparto por fase (R/S/T) y los factores de demanda → `E1-08`.
- [x] **E1-05** (2026-11-08) Memoria de cables y canalizaciones (`raceway_memo`, documento nuevo del catálogo): cada vez que el diseño automático dimensiona una hoja se guarda su resultado y se rehace el documento del proyecto (por hoja: cable de cada circuito con el largo del plano y los plenos, y menor conduit o bandeja de cada tramo con su ocupación y los avisos); PDF al emitir.
- [x] **E1-07** (2026-11-08) Icc de barras seguida desde la alimentación: un tablero alimentado por un circuito de otro recibe la Icc de las barras de arriba reducida por el cable que los une (`short_circuit.ik_aguas_abajo`, cobre a 20 °C y X = 0,08 Ω/km, conservador para el aluminio) y el estudio de cortocircuito muestra la tabla declarada/calculada y avisa cuando la Icc declarada es menor que la que llega. El tablero de cabecera usa la declarada. Falta: red y transformador como origen (hoy la cabecera es un dato), Icc mínima por barra, decaimiento y valor de pico → `E1-09`.
- [x] **E1-08** (2026-11-08) Planilla de cargas con reparto por fase y simultaneidad: cada circuito monofásico se propone en la fase menos cargada (el mayor primero) y el trifásico se reparte en tercios; el TOTAL de cada tablero trae R/S/T y el desequilibrio contra el 30 % de la norma (`imbalance_phases`), y una fila DEMAND con el total por el factor de simultaneidad que el tablero declara (campo nuevo `demand_factor`, 1 por defecto, en el formulario del tablero). La fase propuesta no se guarda ni se dibuja en el unifilar; los factores por tipo de carga de la norma no se aplican → `E1-10`.
- [x] **E1-10** (2026-11-09) Demanda por tipo de carga y fase guardada: la fila DEMAND de la planilla de cargas suma cada circuito por el factor de demanda de su tipo (iluminación, tomacorrientes, fuerza motriz, climatización, otros; constante `factores_demanda_sistema` en la página de normas, **valores típicos a revisar por el dueño**) y por la simultaneidad del tablero. Cada circuito monofásico guarda la fase que carga (`phase_assigned`, R, S o T): la planilla la respeta y reparte el resto, y el unifilar la dibuja en la pata del circuito. Falta la pantalla para elegir la fase (hoy por la API) → `E1-11`.
- [x] **E1-11** (2026-11-09) En el editor del unifilar, el panel del cable de un circuito monofásico tiene el selector de la fase que carga (automática, R, S o T), que se guarda, la usa la planilla de cargas y se dibuja.
- [x] **E1-09** (2026-11-08) Cortocircuito desde la red y el transformador: el tablero de cabecera acepta la potencia de cortocircuito de la red (MVA), el transformador (kVA) y su uk (%) y de ahí sale su Icc (`short_circuit.ik_barras`); los tableros de abajo la siguen por sus cables. Para cada tablero el estudio da la máxima (c = 1,05, cobre a 20 °C), la mínima (c = 0,95, cobre a 70 °C) y el pico κ·√2·Ik″, junto a la declarada, y avisa si la declarada es menor. Los factores c, κ, la temperatura y X = 0,08 Ω/km siguen marcados [VERIFICAR]; la mínima de un tablero cuya cabecera solo declara su Icc no se calcula; no se suma el aporte de motores ni el aluminio.
- [x] **E1-06** (2026-11-08) Emitir ofrece generar lo que falte: la pantalla avisa qué documentos de la plataforma (estudios, listas de cables, planilla de cargas, listados) están sin hacer y el botón «Generar lo que falta» calcula los tableros que no tienen memoria o están atrasados y rehace esos documentos antes de armar el transmittal (`POST /issuing/generate`). La memoria de cables y canalizaciones solo se hace desde el diseño automático del plano.

### E2 · Cerrar lo que quedó a medias
- [x] **E2-01** (2026-11-09) El unifilar dibuja todas las acometidas del tablero (cada una con su cable de entrada, su Q-GRAL y su texto sobre la misma barra) y las que alimentan juntas (campo nuevo «Alimenta junto con las otras marcadas», cables en paralelo de la misma fuente) se reparten la corriente de la cabecera; las no marcadas (red y grupo) llevan cada una toda. Las acometidas se separan 105 mm: más de tres pueden salir del recuadro.
- [x] **E2-02** (2026-11-09) El agrupamiento se toma del plano: cada circuito tiene un campo «Agrupados» (circuitos tendidos juntos, baja la corriente admisible) y, vacío, usa los que el plano cuenta en su tramo más cargado de bandeja o conduit (el máximo entre las hojas); con valor, manda el valor. Sin plano, ninguno. Se cuenta cada circuito de la canalización por igual: no distingue separación entre cables.
- [x] **E2-03** (2026-11-09) Circuitos entre niveles: los niveles que el cable atraviesa sin hoja propia suman la altura del pleno (una por nivel); un nodo con `enlace` a otro nivel (conducto vertical) encadena las hojas y suma su `altura_m`; el dimensionado de canalizaciones da el mismo cable desde cualquier hoja del circuito (cada hoja muestra su tramo). El largo de cada nivel sin hoja usa la altura del pleno de entrada. Lo que no se hizo → `E2-12`.
- [ ] **E2-04** Los DXF del unifilar y del multifilar se generan al emitir. Hoy se generan junto con el SVG y quedan guardados. **Sin urgencia (2026-11-09):** es una optimización de velocidad; el DXF que se emite ya es el correcto, con su sello.
- [~] **E2-05** (2026-11-09) La lista de lo que hay que revisar sale sola en `harness/docs/REVISION_NORMAS.md` (`python tools/build/review_list.py`): los puntos pendientes de cada unidad de la página de normas y las 82 marcas `[VERIFICAR]` del código de los motores, archivo por archivo. **(Dueño)** revisa y aprueba en la página de normas; lo que está en el código y no en la página (las marcas `[VERIFICAR]`) se irá moviendo a la página a medida que se revise, y poder **agregar** medidas a las listas comerciales (hoy solo se corrigen) sigue pendiente.
- [x] **E2-06** (2026-11-09) Plantillas de circuitos por familia en el catálogo de circuitos típicos de la organización: iluminación, tomacorrientes de uso general y especial, climatización (split y equipo con arranque directo) y motores (estrella-triángulo, arrancador suave y variador), con su carga y largo típicos; el cable y la protección salen del cálculo. La organización los cambia, agrega o quita.
- [x] **E2-07** (2026-11-09) Un plano por piso también para el troncal de bandejas, los planos de bandejas de iluminación, tomacorrientes, climatización y fuerza motriz, y los planos de climatización y fuerza motriz (`per_floor` en el catálogo de documentos): cada requisito pide un documento por piso.
- [x] **E2-08** (2026-11-09) Defectos de comportamiento de `harness/docs/refactor/RESULTADOS.md`: F2 (el informe de alimentador aplica «XLPE sin método = B2»), F4 (el analizador de IA ya no fuerza una herramienta: `tool_choice` automático y reintento si no la llama), F6 (la iluminación cae con el 66 % de Ib en el informe, como en el cálculo) y F7 comprobado (los dibujos leen la sensibilidad del criterio; el 30 mA fijo solo queda en las planillas de ejemplo). Quedan F5 y F8 → `E2-13`.
- [x] **E2-09** (2026-11-09) Los factores de la protección de conductores (1,45·Iz, k2 convencional y k1 de no disparo) viven en la sección de constantes de `aea_tables.json` y `policy.py` los entrega con funciones: un valor corregido en la página de normas rige sin reiniciar y se aprueba por valor como las demás constantes.
- [~] **E2-12** El pipeline ya enruta el tramo vertical entre pisos (2026-11-14): con `building.main_board`, `elevation_m` y `shaft` por piso, `epc_plan` mide el recorrido desde el tablero general hasta el tablero de cada piso con la altura del pleno (`routing.route_riser`). Falta que el editor de planos proponga el tramo vertical de un circuito que cambia de nivel y que el dimensionado sume las canalizaciones de todas las hojas en una sola memoria.
- [~] **E2-13** (2026-11-09) F5 (decisión del dueño): el motor, cuando no recibe criterios, usa aislación PVC, y el catálogo de criterios del proyecto usa XLPE; la plataforma siempre pasa los criterios, así que sus proyectos usan XLPE. Hacer que el motor lea el mismo valor cambia 28 pruebas y los resultados dorados (se probó y se revirtió). **(Dueño decide)** si el motor debe usar XLPE por defecto. F8 (los vocabularios de emisión de `management/workflow` y del backend) pasa a «En espera» por no ser eléctrico.
- [ ] **E2-11** Las pestañas de nivel del lienzo (L0, +L1…): decidir si se quitan porque un plano es un piso y los niveles salen del requisito. **(Dueño decide)**

### E3 · Sistemas que faltan
Motores nuevos, o ampliaciones de `epc_aea90364`, con la skill `epc291-engine-builder`: la norma aporta los datos y el motor los algoritmos, cada documento entra al catálogo y cada estimación lleva su `reason` y su `confidence`.
- [x] **E3-01** (2026-11-09) Estudio de fuerza motriz generado (`power_study`, motor nuevo `aea_motor`): cada circuito con arrancador de motor (directo, estrella-triángulo, suave, variador) con su corriente de arranque y la caída de tensión de su cable durante el arranque contra el límite (constante nueva, 15 %), y los que no cumplen. Lo que falta → `E3-09`.
- [x] **E3-09** (2026-11-09) Fuerza motriz: el estudio da la protección propia del motor (relé térmico con su rango, clase de disparo y magnético mínimo), suma a la caída del arranque la de los alimentadores de los tableros de arriba (cobre, GDC de arranque; se dice cuando uno pasa de 70 mm²) y el **plano de fuerza motriz** existe: subdisciplina «Fuerza motriz» del editor con el nodo Motor (`MO`) y la clase de circuito `FMO` (7,5 kVA típicos, a confirmar en la página de normas); sale en Emitir como `power_plan`.
- [x] **E3-02** (2026-11-09) Análisis de climatización generado (`hvac_power_study`): circuitos de los equipos cargados como climatización, con potencia instalada por tablero, corriente, cable, caída y arranque de los que llevan arrancador. Lo que falta → `E3-10`.
- [~] **E3-10** (2026-11-09) Climatización: motor `epc_hvac` (ADR-0033), estudio de carga térmica (`E3-15`) y el **plano de climatización**: subdisciplina «Climatización (potencia eléctrica)» del editor de planos con el equipo `HV`; sale en Emitir como `hvac_power_plan`. Los valores típicos del motor están en la página de normas, sin revisar. Falta el diseño de conductos y los caudales por rejilla (otro motor).
- [x] **E3-03** (2026-11-09) Estudio de puesta a tierra generado (documento nuevo `earthing_study`): esquema, tensión a tierra, tiempos máximos de desconexión y de seccionales, Ra máximo que exige el diferencial en TT, la toma de tierra (la resistencia que se carga en el tablero contra el máximo, o jabalinas propuestas desde la resistividad del suelo) y el PE de cada circuito (`aea_earthing`). Campos nuevos en el tablero: resistencia de la toma y resistividad. Lo que falta → `E3-07`.
- [x] **E3-07** (2026-11-09) Puesta a tierra: el conductor de equipotencialidad principal se dimensiona con la regla de la norma (la mitad del PE más grande, entre 6 y 25 mm², constantes nuevas a confirmar). Falta la verificación de Zs con la impedancia real del lazo y los electrodos que no son jabalinas → `E3-11`.
- [x] **E3-11** (2026-11-09) Puesta a tierra: el estudio propone la toma como jabalinas, conductor horizontal, placas o **malla** cuadrada (fórmula de Sverak, `[VERIFICAR]`), según `electrode_kind` del tablero (elegible en su pantalla), y verifica el Zs de los circuitos TN con valores estándar por sección (constante `impedancias_estandar`, editable en la página de normas), partiendo de la Icc de las barras seguida desde la alimentación por los cables de arriba (la mínima cuando se conoce).
- [x] **E3-04** (2026-11-09) Estudio de compensación de energía reactiva generado (documento nuevo `reactive_study`, motor nuevo `aea_reactive`): P, Q y fp de las cargas de cabecera de cada tablero, reactiva que falta para llegar al fp objetivo (campo nuevo del tablero; vacío, 0,95 de las tablas), banco en escalones comerciales con su corriente y el cable y la protección de la corriente de diseño (1,43·Ic). Los escalones y el 1,43 son constantes típicas a confirmar en la página de normas; sin armónicos, resonancia ni contactor.
- [x] **E3-05** (2026-11-09) Estudio de grupo electrógeno y UPS generado (documento nuevo `backup_study`, motor nuevo `aea_backup`): cada circuito puede marcarse esencial («grupo» o «UPS», hereda el del grupo de arriba); el estudio da el grupo en kVA (marcha y arranque del motor más exigente según su arrancador), la UPS con su reserva, la batería para la autonomía del tablero (campo nuevo, 15 min) y el interruptor de transferencia. Valores típicos en las constantes de normas, a confirmar con el fabricante. Falta dibujar el interruptor de transferencia y la UPS en el unifilar → `E3-08`.
- [x] **E3-08** (2026-11-09) El unifilar dibuja el enclavamiento del interruptor de transferencia entre la red y la acometida del grupo electrógeno, y el by-pass manual de la UPS (se detectan por la fuente de la acometida: «grupo», «generador», «UPS»). Falta el símbolo propio del interruptor de transferencia y de la UPS → `E3-12`.
- [x] **E3-12** (2026-11-09) El unifilar dibuja el símbolo IEC 60617 del generador (círculo G 3~) y de la UPS (caja) en su acometida y el recuadro ATS sobre el enclavamiento de la transferencia. El interruptor de transferencia completo con dos entradas → `E3-18`.
- [x] **E3-06** (2026-11-09) Motor `aea_lightning` de protección contra descargas atmosféricas: superficie de captación, impactos anuales, frecuencia tolerable, eficiencia requerida, nivel de protección I a IV y sus parámetros (esfera, malla, bajadas). Los valores son típicos y sin revisar (constantes `descargas_atmosfericas`, a revisar por el dueño en `E5-04`). Falta el documento → `E3-13`.
- [x] **E3-13** (2026-11-09) Estudio de protección contra descargas atmosféricas generado (`lightning_study`): dimensiones de la estructura, densidad Ng y factores de riesgo se cargan en el tablero de cabecera (campos `lightning_*`, por la API); el estudio da impactos por año, eficiencia requerida, nivel I a IV, esfera, malla y bajadas. Sin revisar → `E5-04`.
- [x] **E3-14** (2026-11-09) Descargas atmosféricas: pantalla del tablero con los datos de la estructura y el **plano de captores y bajadas**: subdisciplina «Protección contra descargas atmosféricas» con captores (`CT`), puestas a tierra (`PT`) y conductores de bajada (`CD`, capa `ELEC-PARARRAYOS`); sale en Emitir como el documento nuevo `lightning_plan`.
- [x] **E3-15** (2026-11-09) Climatización conectada a la plataforma: los espacios y las condiciones de diseño se cargan por la API (`/sld/hvac/spaces`), el motor `epc_hvac` da la carga de refrigeración de cada uno, y el documento nuevo `hvac_load_study` (Estudio de carga térmica de climatización, PDF al emitir) la compara con la potencia eléctrica de los equipos cargados (con un COP típico). Los valores típicos del motor están en la página de normas («Climatización · valores típicos»), con el COP, para que el dueño los confirme. Falta la pantalla → `E3-17`.
- [x] **E3-18** (2026-11-09) El unifilar dibuja el interruptor de transferencia (ATS) como un solo aparato: la acometida de la red y la del grupo electrógeno entran por sus lados, con el rótulo «enclavamiento red / grupo», y sale una sola línea hacia las barras (antes eran dos acometidas unidas por una línea de puntos). El estudio de respaldo agrega los requisitos de la norma: dispositivos tetrapolares y toma de tierra del neutro del grupo de 10 Ω o menos, separada de la de la red.
- [x] **E3-17** (2026-11-09) Pantalla de climatización en Datos de entrada (debajo de la lista de cargas): condiciones de diseño, espacios con sus dimensiones, ocupantes, uso, iluminación, equipos, muro y ventana, y la carga de refrigeración por espacio y total, con el aviso de los valores típicos.
- [x] **E3-16** (2026-11-09) El unifilar dibuja el recuadro ATS del símbolo IEC 60617 sobre el enclavamiento entre la red y el grupo, con su rótulo. Dibujar el interruptor de transferencia con sus dos entradas y una salida única (el símbolo completo `lv_ats`) pide cambiar la topología de las acometidas → `E3-18`.

### E4 · Entregables finales
- [x] **E4-01** (2026-11-09) Informe técnico eléctrico generado (`electrical_report`): alcance, criterios del cálculo, una fila por tablero (circuitos, potencia, sección máxima, cumplimiento y estado) y observaciones (circuitos que no cumplen, tableros sin calcular o desactualizados), con la lista de documentos de respaldo. No incluye texto de criterios de diseño redactado por el agente ni conclusiones → `E4-06`.
- [x] **E4-06** (2026-11-09) El informe técnico eléctrico trae los capítulos de **criterios de diseño** (normas, caídas máximas, conductor y aislación, diferencial y reserva, condiciones de instalación, verificación de las protecciones, aviso de valores sin revisar) y de **conclusiones** (si cumple, cuántos circuitos y protecciones no cumplen, qué está pendiente y qué hacer), escritos por el programa desde los criterios y los resultados del proyecto, sin cambiar ningún número. El agente `electrical-report-writer` queda para redactar un texto más largo si se pide.
- [~] **E4-02** Pliego técnico eléctrico (`electrical_spec`) con el agente Document Writer. Hay un borrador con estructura provisoria en la etapa 11 (ver `PLG-01`); falta la estructura del dueño y la redacción del agente. Antes hay que elegir una sola estructura de pliego (`PLG-01`). El agente `electrical-spec-writer` ya existe; espera la estructura de pliego del dueño (**Dueño**, la entrega en unas horas).
- [x] **E4-03** (2026-11-09) Versión en Word de los documentos que salen en Emitir: los estudios, el informe y las memorias MC y SP se pueden emitir también como `.docx` (`formats` en cada ítem de la emisión; el Word es opcional y no sale si no se pide). Lo hace `epc_drawing.export.report_docx` sin librerías (estilos propios de Word, carátula con logos PNG y JPG, tablas con encabezado repetido y pie con «Página n de total»). **(Dueño)** revisa cómo se ve en Word. Falta la pantalla de Emitir para elegir el formato → `E4-14`; los logos SVG → `E4-11`.
- [x] **E4-14** (2026-11-09) Pantalla de Emitir: cada documento que tiene versión opcional (Word) muestra una casilla «.docx», activa cuando el documento está elegido; sin tildarla sale solo el PDF.
- [x] **E4-04** (2026-11-09) El plano con su lámina IRAM: lo que se emite de un plano del editor (iluminación, tomacorrientes, bandejas, fuerza motriz, climatización) es ahora el plano dentro de la lámina del formato (A1 por defecto) con el rótulo del proyecto, los logos y la lámina como la dejó la organización, a una escala normalizada: la que cabe (`epc_drawing.export.plan_sheet`, `layout/sheet.py`). El editor tiene el botón «Vista previa de impresión»: muestra la lámina completa, con elección de formato y la escala usada; se edita sin lámina y la vista previa la muestra completa. Cubre `TRZ-07` y `TRZ-16`. **(Dueño)** revisa cómo se ve en pantalla. Falta: elegir y guardar el formato y la escala de cada plano (hoy A1 y la mayor que cabe; la vista previa deja probar el formato), la vista previa dentro de las memorias de iluminación y tomacorrientes, y probar el botón en el navegador con un proyecto real → `E4-15`.
- [x] **E4-15** (2026-11-09) El formato de lámina (A0 a A4) y la escala (1:N o la mayor que cabe) de cada plano se eligen en la vista previa, se guardan en el plano (`sheet_format`, `paper_scale`) y son los que usa lo que se emite. **(Dueño)** prueba el botón en el navegador con un proyecto real.
- [~] **E4-05** (2026-11-09) Catálogo de fabricantes sembrado en `shared/catalog/manufacturers/<fabricante>/` (un JSON por fabricante y por categoría): Schneider Electric, ABB, Siemens (interruptores) y Prysmian (cables), todo `unverified` y con su fuente. Falta → `E4-07` y `E4-08`.
- [x] **E4-07** (2026-11-09) Listado de materiales (`material_list`, documento nuevo del catálogo, XLSX al emitir): tableros, protecciones (consolidadas por tipo, corriente, curva y poder de corte) y cables (metros por sección) que salen de las memorias de los tableros, con los modelos del catálogo de fabricantes que sirven para cada ítem y su estado (sin verificar, verificado o sin modelo). Los modelos son opciones, no una elección. Falta → `E4-13`.
- [~] **E4-13** (2026-11-09) Listado de materiales: ahora también motores y arrancadores (por tipo de arranque y potencia) y las cantidades de los planos: piezas de cada tipo dibujadas (luminarias, tomacorrientes, equipos de climatización, motores, captores, puestas a tierra) y el largo de cada canalización o conductor. Falta completar el catálogo de fabricantes con tableros, canalizaciones, luminarias, motores y compensación, y los precios de referencia cuando el dueño los entregue.
- [ ] **E4-08 (Dueño)** Entregar catálogos PDF de fabricantes para que se actualice y complete el catálogo (poder de corte, curvas, dimensiones), y marcar lo contrastado como `verified`.
- [x] **E4-09** (2026-11-09) Los documentos que la plataforma escribe en Markdown o CSV (estudios, informe técnico, listas de cables, planilla de cargas, listados y análisis de cargas) salen en Emitir: los Markdown como PDF y los CSV como XLSX, hechos al emitir desde la misma fuente que se lee en Memorias y con el código que el requisito registró (`engineering/documents_issue.py`). Probado de punta a punta con un transmittal. El PDF lleva título, proyecto, código, disciplina, fecha y pie con número de página; falta la carátula con logo y la revisión → `E4-10`.
- [x] **E4-10** (2026-11-09) Formato común de los documentos emitidos: el PDF abre con una carátula (logos del emisor y del cliente, título, proyecto, código, disciplina, fecha, revisión, emisión y transmittal) y el texto sigue con título, código, pie y «Página n de total»; las tablas reparten el ancho por su contenido. Lo hace el generador de PDF (`epc_drawing.export.report_pdf`, campo `cover`). Falta: los logos SVG (hoy solo PNG y JPG; hace falta un conversor) → `E4-11`; la misma carátula para las memorias MC/SP de los tableros y los estudios de iluminación y tomacorrientes → `E4-12`.
- [x] **E4-11** (2026-11-09) Logos SVG en las carátulas de los PDF y de los Word: el motor los dibuja (`epc_drawing.export.logo`: formas con sus colores, huecos y trazos; sin degradados ni textos) y los pasa como imagen. Comprobado con los logos del repositorio (dos de tres salen completos; el tercero, un SVG con efectos, sale recortado).
- [x] **E4-12** (2026-11-09) La carátula y el formato común también en las memorias MC y SP de cada tablero y en los estudios de iluminación y tomacorrientes (`engineering.issue_cover`).

### E5 · Del dueño (el programa no puede hacerlas)
- [ ] **E5-05 (Dueño)** Entregar las normas que faltan para reemplazar los valores típicos (lista y dónde se usan en `harness/docs/FUENTES_NORMAS.md`): IEC 62305 / IRAM 2184 (descargas), ASHRAE (carga térmica y ventilación), IEC 60947-4-1 (relés del motor), ISO 8528 e IEC 62040 (grupo y UPS), IEC 60831 (reactiva), IEC 60228 (resistencias) e IEEE 80 (malla). Las AEA del repositorio ya se usaron: equipotencialidad, arranque, demanda, tomacorrientes y transferencia salen de ellas.
- [ ] **E5-01** Aprobar los niveles del Decreto 351/79 y los valores típicos de iluminación y de tomacorrientes en la página de normas (`ILU-01`, `ILU-02`, `TOM-01`).
- [ ] **E5-02** Cargar las luminarias y los tomacorrientes reales del proyecto o de la organización (`ILU-03`, `TOM-02`), y la tarifa y el límite de W/m² si se quieren (`ILU-04`).
- [ ] **E5-03** Conseguir planos reales (PDF de CAD con mucho rayado, DXF y PNG de arquitectura) para ajustar el reconocimiento.
- [~] **E5-04** (2026-11-09) Las reglas nuevas (descargas atmosféricas, equipotencialidad, fuerza motriz, reactiva, respaldo) ya se ven en la página de normas con su título, como pendientes. **(Dueño)** las revisa y las aprueba. Desde el 2026-11-09 los valores que tienen norma en el repositorio llevan su cláusula (`harness/docs/FUENTES_NORMAS.md`).

## Otras áreas (eléctricas: iluminación, tomacorrientes y el editor de planos)
Van después de la disciplina eléctrica, salvo que una tarea eléctrica las necesite (entonces se nombra en esa tarea).

### Iluminación (`ILU`)

*Pendientes (lo que quedó sin hacer o sin verificar) › De tu lado (no los puede hacer el programa)*
- [ ] **ILU-01** **Revisar y aprobar los niveles del Decreto 351/79** en la pantalla de normas ("Niveles de iluminación"). Mientras estén pendientes no alimentan ninguna meta.
- [ ] **ILU-02** **Confirmar con la norma vigente** los criterios de emergencia antipánico (0,5 lx y relación máx/mín 40) y el factor 0,9 del chequeo directo: están como valores típicos con confianza 0,5.
- [ ] **ILU-03** **Reemplazar las luminarias de fábrica** por las del proyecto (flujo, potencia, factor de potencia, curva): hoy son valores típicos marcados como ilustrativos.
- [ ] **ILU-04** **Cargar el límite de W/m² y la tarifa por kWh** en las opciones de cada hoja si quieres que la verificación de energía y el costo se calculen: el programa no trae ninguno.

*Pendientes (lo que quedó sin hacer o sin verificar) › Motor*
- [ ] **ILU-05** Filas industriales de la Tabla 2 del Decreto 351/79 (hoy hay una fila marcada "sin cargar").
- [ ] **ILU-06** Reglas de uniformidad y relaciones de luminancia del Decreto: se revisan pero no se usan para verificar.
- [ ] **ILU-07** Otras normas de iluminación (IRAM-AADL J 20-06, EN 12464-1) como paquetes de norma, con el selector de norma (ADR-0028).
- [ ] **ILU-08** Ambientes que no son rectángulos: se calcula sobre el rectángulo envolvente y se descartan las luminarias que caen fuera. Falta calcular sobre el contorno real y los ambientes girados.
- [ ] **ILU-09** Inter-reflexiones en el punto a punto (hoy solo luz directa) y luminarias inclinadas o giradas.
- [ ] **ILU-10** Cálculo propio de UGR (hoy solo se compara un valor calculado afuera).
- [ ] **ILU-11** Áreas exteriores: ubicar los proyectores (hoy solo se calcula la cantidad), tabla de niveles exteriores típicos y aprovechamiento del haz (CBU) desde la curva isocandela.
- [ ] **ILU-12** Emergencia: el motor ya revisa rutas de escape, pero la pantalla no deja dibujarlas ni cargar sus datos; tampoco hay campo para la iluminancia mínima propia del ambiente.
- [ ] **ILU-13** Importar curvas de fabricante (archivos IES y LDT) y tablas de utilización del fabricante. (La planilla del catálogo ya se importa, sin curvas.)

*Pendientes (lo que quedó sin hacer o sin verificar) › Plataforma*
- [x] **ILU-14** (2026-11-09) Las memorias de iluminación que se emiten abren con la carátula con los logos (PNG y JPG), el proyecto, la disciplina, la fecha y la revisión (`E4-10` y `E4-12`). Los logos SVG → `E4-11`.
- [ ] **ILU-15** Un solo estudio por hoja (sin historial de estudios anteriores).
- [ ] **ILU-16** La revisión de las reglas de iluminación guarda su estado junto al de AEA 90364 (un solo archivo de revisión): moverlo al motor de iluminación cuando haya más normas.
- [ ] **ILU-17** La pantalla de revisión de normas para reglas de iluminación no se probó en el navegador (sí por API y tipos).
- [ ] **ILU-18** Las pruebas de emergencia tardan unos 6 s (búsqueda de hasta 400 luminarias): acelerar la búsqueda o limitarla.
- [ ] **ILU-19** Las luminarias del grupo `emergency` no se ofrecen al comparar ni al elegir sola; hoy el grupo solo lo trae la de fábrica (las del catálogo propio que sean de emergencia deben llevar ese grupo).

*Mejoras › Pantalla*
- [x] **ILU-20** (2026-11-18) Mapa de lux en DXF: lámina `<tablero>_luxmap_<planta>.dxf` en `04_PLANS` y figuras en el PDF y el Word del estudio luminotécnico (celdas de color según el nivel exigido y curvas con su valor). Falta el mapa de tomacorrientes → `ESP-01`.
- [ ] **ILU-21** Arrastrar las luminarias de la vista previa antes de aplicar (hoy se arrastran después, ya como nodos).

*Mejoras › Entregables*
- [x] **ILU-22** (2026-11-09) Versión en Word de la memoria de iluminación: sale en Emitir como `.docx` opcional (`E4-03`).

### Tomacorrientes (`TOM`)

*Pendiente › De tu lado*
- [ ] **TOM-01** **Confirmar en la página de normas los valores típicos** de «Tomacorrientes · valores típicos»: solo el depósito (un tomacorriente cada 9 m de perímetro, mínimo 2) viene de una cláusula; el resto es práctica habitual con confianza 0,4.
- [ ] **TOM-02** **Reemplazar los tomacorrientes de fábrica** por los del proyecto (potencia, corriente, IP).

*Pendiente › Motor*
- [ ] **TOM-03** Cantidades por cláusula de la norma para viviendas (770) y locales (771) cuando se carguen y aprueben las reglas.
- [ ] **TOM-04** Posición según puertas, muebles y puestos de trabajo (hoy se reparte parejo por las paredes); ambientes que no son rectángulos (hoy se usa el rectángulo envolvente).
- [ ] **TOM-05** Reglas especiales ya cargadas en las reglas de AEA que aún no se verifican: aulas con tomacorrientes junto al pizarrón, jardines infantiles a 1,7 m, tomas accesibles a niños (2x10+T con pantalla), circuitos ATE en rojo, carga de vehículos eléctricos.
- [ ] **TOM-06** Tomacorrientes de uso especial: un circuito por cada uno, con su destino.

*Pendiente › Plataforma*
- [x] **TOM-07** (2026-11-09) El informe de tomacorrientes trae el mapa de la hoja: los ambientes como contornos y los tomacorrientes colocados (uso general en azul, especial en rojo).
- [ ] **TOM-08** Exportar a DXF queda **en espera** con todo lo de optimizar el DXF.
- [ ] **TOM-09** La pantalla de normas con la unidad nueva no se probó en el navegador (sí por API y pruebas).

### Trazado (editor de planos) (`TRZ`)

*Prioridad alta (orden sugerido)*
- [x] **TRZ-01** (2026-11-09) Ya estaba hecho y probado en el editor: Imán (snap) a nodos y vértices del fondo, con la grilla opcional.
- [x] **TRZ-02** (2026-11-09) Ya estaba hecho y probado en el editor: Línea continua: sigue desde el último punto hasta Esc (`PlanEditor.test.tsx`).
- [x] **TRZ-03** (2026-11-09) Ya estaba hecho y probado en el editor: Barra de coordenadas bajo el lienzo: X, Y en metros, zoom, imán y escala.
- [x] **TRZ-04** (2026-11-09) Ya estaba hecho y probado en el editor: Colorear por tipo o por circuito, con leyenda.
- [x] **TRZ-05** (2026-11-09) Ya estaba hecho y probado en el editor: Selección por caja arrastrada (probado).
- [x] **TRZ-06** (2026-11-09) Ya estaba hecho y probado en el editor: Menú contextual con clic derecho (probado).

*Salida*
- [x] **TRZ-07** (2026-11-09) Hecho en `E4-04`: vista previa de impresión con la lámina IRAM y su rótulo.

*Según la especialidad*
- [~] **TRZ-10** Biblioteca de símbolos del catálogo, con rotación. — Hecho: giro del símbolo (también en el DXF). Falta: elegir el símbolo con una vista previa.

*Varios niveles*
- [x] **TRZ-11** Conectar nodos entre niveles (sube/baja) y ruta entre niveles por plenos. — Hecho: el enlace `nivel:nodo` de un conducto vertical y su comprobación (existe, cae en el mismo lugar, apunta de vuelta). Falta: medir un circuito que cruza niveles. → se hace en `E2-03`.


*Para hacer luego (lo que quedó incompleto o sin verificar) › Lo que no está completo*
- [x] **TRZ-13** Ruta de un circuito entre niveles: hoy solo se comprueban los enlaces de los conductos verticales; no se mide un circuito que cruza niveles (por plenos o por conductos verticales). → se hace en `E2-03`.
- [x] **TRZ-16** (2026-11-09) Hecho en `E4-04`: vista previa de impresión con la lámina IRAM y su rótulo.

*Para hacer luego (lo que quedó incompleto o sin verificar) › Otras cosas sin hacer o sin verificar*
- [ ] **TRZ-20** Probar a mano en el navegador lo que solo tiene prueba automática: matriz de copias, plantillas, copiar a otros niveles, reservar espacio, comentarios fijados, herramienta Ruta, alinear y recortar el fondo, exportar PNG e imprimir, historial con comparar.


### Pliegos técnicos (`PLG`)

*Pendientes*
- [ ] **PLG-01** **Tres convenciones de estructura conviven.** El agente nuevo usa 16 secciones en un solo archivo; el skill y el agente anterior usaban 9 capítulos (Alcance, Informe descriptivo, Normas, Materiales y equipos, Ejecución, Controles de calidad, Documentación de entrega, Garantías, Responsabilidades) y el verificador espera 10 archivos `NN_Nombre.md` con `00_Index_and_Control.md`. Decidir una sola y alinear las otras dos. Correspondencia aproximada del modelo de 9 capítulos al nuevo: Alcance y generalidades → Objetivo + Alcance; Informe descriptivo → Memoria Descriptiva; Normas → Marco Normativo; Materiales y equipos + Ejecución → Condiciones Generales de Ejecución + Requisitos Técnicos; Controles de calidad → Ensayos + Criterios de Aceptación; Documentación de entrega → Documentación Técnica; Garantías y Responsabilidades → Responsabilidades del Contratista + Recepción Provisoria y Final.
  - **Estructura provisoria (2026-11-14, a pedido del dueño):** la etapa 11 genera un borrador de pliego (`specification`, `stages/specification.py`) con 11 secciones: Objective, Scope, Descriptive memo, Normative framework, General conditions of execution, Technical requirements, Tests, Acceptance criteria, Technical documentation, Responsibilities of the contractor, Provisional and final reception. Es una propuesta que se optimizará cuando el dueño elija la estructura única; los datos que faltan salen como `[DEFINIR]` con quién debe darlos, sin valores de norma. Solo se produce cuando la etapa 3 trazó las plantas (el golden no cambia).
- [ ] **PLG-02** **El verificador no revisa el archivo único.** `specification_verifier` lista `NN_Nombre.md` y marca como fuera de patrón cualquier otro archivo; hace falta un modo para un pliego en un solo archivo (las comprobaciones de obligaciones, normas repetidas, comerciales y formato Pandoc sirven igual).
- [ ] **PLG-03** **Pasos 2, 5 y 6 del skill** (puerta por capítulo, guardado por capítulo, autocontrol por capítulo) a reescribir según la estructura que se elija.
- [ ] **PLG-05** **Modo de guardado**: el agente puede escribir en el proyecto; confirmar que solo lo haga en `02-engineering/TECHNICAL_SPECS/` y nunca sobrescriba (hoy lo dice su prompt, no hay una restricción técnica).

### Calidad del gate

- [x] **QA-01** (2026-11-09) Pruebas intermitentes resueltas. Backend: (1) una generación nueva recibía 409 si llegaba mientras la anterior, ya en «done», publicaba los estudios; ahora espera a que termine (`jobs._finishing`), con una prueba que lo reproduce; (2) una prueba borraba su carpeta temporal bajo esos mismos estudios; ahora espera (`jobs.wait_idle`). Web: `LoadList.test.tsx` espera cada campo de la fila nueva. El gate guarda el detalle de un fallo en `.cov/failed-<chequeo>.txt`.

### Agentes por disciplina (`AGT`)

- [x] **AGT-01** (2026-11-09) Agentes especialistas de la disciplina eléctrica en `harness/.claude/agents/` (12 `electrical-*`: cargas, conductores, protecciones, tierra y descargas, iluminación, fuerza motriz, respaldo y reactiva, tableros, planos, redactor del informe, redactor del pliego, listado de materiales).
- [ ] **AGT-03** Enlazar los agentes eléctricos a los plugins que los usan (`agents` en su `plugin.json`) y probarlos con un proyecto real.

### Simulación real del 2026-11-15 (`SIM`)

Origen: `BUGS-Y-TEMPORALES.md` de la simulación (proyecto ficticio, modo edición). Arreglados en la misma rama: B-03 (el resumen de la etapa 9 ahora da también el total de la corrida), B-06 (el manifiesto ya no lista dos veces el documento que tiene PDF/DOCX), B-11 (la Memoria dice "Pendiente" sin "Hz" si falta la frecuencia), T-06 (`catalog_dir` acepta un nombre relativo al catálogo del repositorio), y la etapa 6 ya no se cae con un aparato de más de 125 A.

- [x] **SIM-01** (T-01) Vía soportada (CLI/MCP o formulario) para definir ambientes, muros y aberturas desde cero; hoy `epc_arch` solo lee o redibuja planos existentes. **Hecho 2026-11-15:** `epc_arch.author` dibuja las plantas desde una descripción (ambientes como rectángulos en metros, puertas y ventanas por lado) y `python -m epc_arch.author` escribe el DXF; falta el formulario guiado que arme esa descripción (queda en SIM-05).
- [x] **SIM-02** (T-02) El lector de planos pierde ambientes (5 de 7) cuando hay ventanas en un muro vertical exterior (x = 0). **Hecho 2026-11-15:** las anotaciones ya no toman por etiqueta la esquina de muro entre dos ventanas (capas que nombran muros, puertas o ventanas nunca son anotación; una caja de etiqueta guarda proporción con su texto).
- [x] **SIM-03** (T-03) Leer el código del ambiente (PB-01…) del texto del plano; hoy vuelven `r1`…`r7` con `code` vacío. **Hecho 2026-11-15:** el plano escribe "PB-01 · 53,0 m²" bajo el nombre y el lector lo recupera (`code`, `written_m2`); en `building`, `rooms`, `special`, `emergency` y `exclude` aceptan el código del ambiente.
- [x] **SIM-04** (T-04) Poder indicar el ambiente (por id) donde va el tablero o el shaft, en vez de coordenadas en el marco de la hoja. **Hecho 2026-11-15:** `board`, `shaft` y `main_board` aceptan `{"room": id, código o nombre}` y se ubican en el centro del ambiente (`resolve_rooms`).
- [ ] **SIM-05** (T-05, T-07) Bloque guiado para cargas y `engine_inputs` (luminarias, tomas, estudios, HVAC, tierra) y que el agente `electrical_lv` pueda guardar las respuestas sin intervención manual.
- [x] **SIM-06** (hecho 2026-11-16: `review_state.py`; el manifiesto sigue el flujo y la carátula muestra estado, firmante y hallazgos mayores) (B-01) Tras `approve` e `issue`, el manifiesto y el PDF del transmittal siguen en `draft` y `signed: null`; deben reflejar el estado del flujo (decisión del dueño: cómo se firma sin romper el hash del manifiesto).
- [x] **SIM-07** (parcial 2026-11-16, opción «solo reflejar»: los `major` se listan en la carátula y en la respuesta de `approve`/`issue`; **decisión del dueño pendiente:** si algún `major` debe bloquear o aceptarse con motivo) (B-02) `approve`/`issue` no se bloquean con hallazgos `major` abiertos (decisión del dueño: qué severidad bloquea y si el ingeniero puede aceptar un hallazgo con motivo). **Cerrado 2026-11-17 (decisión del dueño, opción A):** un `major` abierto bloquea `approve` e `issue`; el ingeniero de registro sigue con `--accept-major "motivo"`, que marca esos hallazgos `accepted` (motivo y quién) en el manifiesto y en la carátula. Las notas quedan `accepted` («seen at approval») al aprobar (SIM-17).
- [x] **SIM-08** (B-04) Falta el dato de protección diferencial en el formulario y en `engine_inputs`: 20 hallazgos `major` (`differential_ok = False`, esquema TT).
- [x] **SIM-09** (B-05) F-0060: la caída de tensión máxima del dibujo (2,17) no coincide con la esperada (2,53); averiguar si es redondeo o fuente.
- [x] **SIM-10** (B-07) Los entregables sin entrada en `engine_inputs.deliverable_names` salen sin el código del proyecto; derivar el nombre AAAA-PROVEEDOR-CLIENTE-CODIGO desde el proyecto.
- [x] **SIM-11** (B-08) Unificar las tres convenciones de capas (`A-*`, `ARQ-/ELEC-/PLAN-*`, `291-*`) y la tipografía (OpenSans/Liberation vs Arial).
- [x] **SIM-12** (B-09) El rótulo del unifilar deja vacíos cliente, ubicación, estado y revisión; llenarlos desde `fields`.
- [ ] **SIM-13** (B-10) Plano eléctrico de PB: el edificio ocupa poca hoja y los circuitos tapan los muros; ajustar escala y capas (observado, no medido).
- [x] **SIM-14** (B-11) Idioma: con el proyecto en `es`, el informe descriptivo sale en inglés.
- [x] **SIM-15** (B-12) Etapa 4: sin etapa para un edificio alimentado en BT directo.
- [x] **S1-B02** El lector devuelve 27 muros donde se dibujaron 11 (los muros se parten en tramos entre aberturas y encuentros, no es un error) y en la planta alta `P1` lee 7 de 8 ventanas: falta la del muro norte entre x≈33 y 35 (en `PB` esa misma ventana sí se lee). Causa sin investigar: mirar `recognizers/openings.py` (`find_gaps`, `_window_evidence`). **Cerrado 2026-11-17: no es un error del lector.** La abertura de 2 m (x 32.8–34.8, muro y=26.2) de `P1` se dibujó con una puerta (arco de radio 1) y vidrio de ventana en el mismo hueco; el lector lee una puerta. La que falta en la cuenta es esa; las otras 7 se leen.
- [ ] **SIM-16** (B-13) Iluminación: entrada de coeficiente de utilización en el formulario; hoy se usa una tabla ilustrativa. **Aclaración 2026-11-17:** el motor ya toma el coeficiente por ambiente (`coefficient_of_utilisation` en los datos del ambiente de `engine_inputs.building`) o por luminaria (`cu`, `cu_table`); la tabla ilustrativa es solo el respaldo y lo avisa. Falta únicamente pedirlo en el formulario guiado: queda dentro de SIM-05.
- [x] **SIM-17** (B-14) Los hallazgos `note` quedan abiertos sin dueño; el manifiesto no distingue los ya vistos. **Hecho 2026-11-17:** al aprobar, los hallazgos `note` abiertos pasan a `accepted` (motivo «seen at approval», firmante), así el manifiesto distingue los vistos de los nuevos.
- [x] **SIM-18** (B-15) Probar si una nueva corrida marca como cambiado el acta de `inputs/minutes/` editada después de la corrida. **Hecho 2026-11-17:** verificado: `inputs/minutes/` es una entrada más; editarla después de la corrida da el hallazgo IM-01 `changed` (test `test_a_minutes_file_edited_after_the_freeze_is_a_changed_input`).
- [x] **SIM-19** (B-06) Cinco entradas del manifiesto no tienen archivo (`boq`, `datasheets`, `lighting_study`, `rfq`, `terminal_block_list`): decidir si se renderizan o se quitan.

## En espera / más adelante
Nada de esto se hace hasta que el dueño lo pida.

### Todo lo que no es eléctrico (en espera desde 2026-11-09, decisión del dueño)
Se retoma cuando el dueño lo pida: reconocimiento de arquitectura, cloacas y otras disciplinas del trazado, táctil y teléfono, y el pliego de otras disciplinas.
- [ ] **E2-10** (en espera: gestión, no eléctrico) Flujo de gestión: las pruebas de `management/workflow` no corren en el gate (necesitan `90_MANAGEMENT/DELIVERABLES.md`); un proyecto que termina en conceptual o en básica no tiene emisión de cierre al cliente.

- [ ] **AGT-02** Mismos agentes especialistas para las demás disciplinas (civil, mecánica, climatización, cañerías, instrumentación, telecomunicaciones, incendio), uno por cada especialidad, con el mismo formato.

### Arquitectura (`epc_arch`) (`ARQ`)
*Reconocimiento*
- [ ] **ARQ-01** Puertas finas del baño en PNG (p1 y p6): 4 de 6. Se ven completas en la imagen; una (0,6 m) no pasa los criterios de `swings.doors_at_wall_ends`. Falta instrumentar arco, espacio libre y hoja para ese caso.
- [ ] **ARQ-02** IoU de muros en PNG de p1, p3 y p6: 0,50 a 0,70 (meta 0,90). Muros de 12 cm pierden en la lectura de imagen.
- [ ] **ARQ-03** Escala de los PNG sin unidades: sale de las puertas (0,8 m típicas), con error de 2 a 4 % (p4: 10 %). Con una referencia en la imagen (escala gráfica, cota, o que el usuario la diga) se resuelve; el ajuste a anchos estándar empeoró y se descartó.
- [ ] **ARQ-04** Área de ambientes: 3 a 5 % de error contra una meta de 3 %. Pide cuadrícula más fina o calcular el polígono exacto.
- [ ] **ARQ-05** p2: cocina y estar son un solo espacio abierto para el motor (el tabique no cierra); la verdad los separa.
- [ ] **ARQ-06** Filtro de etiquetas antes de buscar puertas (R3.4): círculos, hexágonos, rombos y directrices a 45°.
- [ ] **ARQ-07** Huecos anchos (R3.7): portón de 3 m y corrediza de 1,2 m están en la verdad y se detectan en los planos de prueba; falta descartar huecos falsos por etiquetas en láminas reales.
- [ ] **ARQ-08** Espesores por familia (R3.3): vectorial ya da error de 0 cm; en imágenes depende de la escala.
- [ ] **ARQ-09** Verdad con coordenadas para láminas reales (A-201): hoy solo hay conteos; hace falta etiquetar a mano para medir F1 y `wall_iou` ahí.
- [ ] **ARQ-10** Planta alta de A-201: espesor 40 cm contra 30 cm de la baja y 45 muros; sospechoso.
*Salida (dibujo)*
- [ ] **ARQ-11** Escala automática que llene mejor la lámina (hoy 1:100 por defecto; una casa de 14 m queda chica en A1). Cambia el comportamiento por defecto del PRD: decidir antes.
- [ ] **ARQ-12** Nombre del ambiente que no cabe en una sala angosta: escribirlo más pequeño en vez de omitirlo.
- [ ] **ARQ-13** Etiqueta redonda P-02 del estudio de A-201 no se mueve.
- [ ] **ARQ-14** Cajas rectangulares de etiquetas de la fuente (PB-01 · 16,00 m²) pueden caer sobre un borde: son anotaciones del original.
- [ ] **ARQ-15** Muro marcado en gris oscuro y trazos extra en ventanas de la parte central de A-201.
- [ ] **ARQ-16** DXF sin logos del rótulo (el DXF no guarda imágenes aquí).
- [ ] **ARQ-17** PDF con Helvetica estándar (no lleva fuente embebida) y PNG con Arial del sistema: no se redistribuye `arial.ttf`.
- [ ] **ARQ-18** Renderizador de SVG (PNG vs SVG no se compara: la app no tiene ninguno).
- [x] **ARQ-19** Empaquetado: agregar `epc_style.json` al `package-data` de `pyproject.toml` (hoy funciona con `PYTHONPATH=src`). **Hecho 2026-11-15:** `epc_style.json` agregado al `package-data`.
*Calidad y rendimiento*
- [ ] **ARQ-20** Rendimiento: un PNG de 2340×1740 tarda 15 s (meta 10 s por plano en A3): 26 lecturas de muros, huecos y ambientes, búsqueda de puertas (3,6 s) y relleno de ambientes (2 s). Posible mejora: evitar la segunda pasada completa de escala.
- [ ] **ARQ-21** Caché de máscaras repetidas (R4.8): no hecha porque el cuello de botella resultó ser el cálculo.
- [ ] **ARQ-22** CI propio de `epc_arch` (R4.9): hoy lo cubre el gate completo.
- [ ] **ARQ-23** Regresión visual PNG contra SVG (falta renderizador) y contra imágenes guardadas.
*Integración*
- [ ] **ARQ-24** El backend debe componer la lámina IRAM (`epc_titleblock.service.render` con los datos del proyecto) y dársela al motor (`sheets.iram_template` o `--sheet-svg`): hoy el comando v2 la genera él mismo por línea de comando.
- [ ] **ARQ-25** Cambios del PRD que modifican código existente y esperan aprobación: unificar los dibujantes antiguos (`svgout.py`, `planta_prueba`) con el modelo común `drawing.py` (fase de unificación, "primero sube todo al dev").
- [ ] **ARQ-26** Editor del Layout: verificar visualmente el cambio de capas ocultables tras las anotaciones y la separación de láminas.
*Hallazgos del proyecto 13 (hospital de tres niveles, `engine/arch/scripts/proyecto_13.py`)*
- [x] **ARQ-27** El DXF ignora `CIRCLE` ("not read: 12 circle"): las burbujas de los ejes se pierden y la lámina sale sin ejes dibujados, solo con las letras. Leerlos como arcos de 360° y mandarlos a anotaciones. **Hecho 2026-11-15:** el DXF lee `CIRCLE` como un arco de 360°.
- [x] **ARQ-28** Los códigos de rótulo con dígito en la sigla (`N1-01`, `P1-02`) no se reconocen: quedan pegados al nombre ("HABITACIÓN 101 N1-01") y no se lee la superficie escrita (`written_m2` vacío). `TAG_CODE` y `TAG` de `room_names.py` aceptan solo letras antes del guion. **Hecho 2026-11-15:** los códigos con dígito en la sigla (`N1-01`, `P1-02`) se reconocen.
- [ ] **ARQ-29** Puertas de 1,40 m (de camilla): 4 de 4 en el nivel de quirófanos y la de acceso de la planta baja no se reconocen; salen como hueco o como ventana "de un trazo". Revisar los rangos de ancho de `swings` (`width_spread`) y el cálculo del ancho usual. **Parcial 2026-11-15:** en planos vectoriales con unidades el radio de puerta admitido sube a 1,50 m (`metres.door_radius`); falta revisar las imágenes (`swings`).
- [ ] **ARQ-30** Una puerta que abre hacia un pasillo lo parte: aparecen dos ambientes sin nombre de 4 a 10 m² por nivel y el pasillo principal pierde el 25 % de su área medida. Descontar las hojas y arcos de giro al cerrar ambientes.
- [ ] **ARQ-31** Ventanas en PNG (tres trazos de 1 px en muros de 12 a 30 cm a 60 px/m): 16 de 35. Es la misma debilidad de las ventanas finas de los PNG ya anotada arriba.
- [ ] **ARQ-32** Área medida de los locales: 5 a 9 % de error medio (máximo 26 % en pasillos) contra la verdad calculada con shapely; la meta es 3 %.
- [ ] **ARQ-33** Una ventana falsa de "2 paneles dentro del muro" en la planta de internación, junto a una puerta de 0,90 m.
- [ ] **ARQ-34** PNG de 2940 × 2220: 16 a 21 s por plano (ya anotado en rendimiento).
*Láminas y estilo de la organización*
- [ ] **ARQ-35** Falta verificar con un proyecto real que la lámina propia (márgenes, rótulo) sale bien en los unifilares y multifilares: la configuración ya viaja en `titleblock.sheet_config`.
- [ ] **ARQ-36** La franja de coordenadas se escribe en mm (es demasiado angosta para arrastrarla); los márgenes sí se arrastran en la vista de toda la lámina.
- [ ] **ARQ-37** `epc_plan` (DXF de las disciplinas) y los generadores de unifilares dibujan con sus propias plumas: no leen todavía las de la organización.

- [~] **TRZ-08** Modos por disciplina: la botonera y la paleta se adaptan (eléctrica, cloacas, etc.). — La paleta sale del perfil; la herramienta Ruta solo aparece en eléctrica.
- [~] **TRZ-09** Pendiente automática en cloacas con aviso si queda fuera de norma. — El motor ya calcula las cotas y avisa; ahora se ven sobre los nodos. Los valores de la norma siguen pendientes de confirmar.
- [~] **TRZ-12** Pellizco para zoom, dos dedos para panear, asas grandes de arrastre. — Hecho en el código; falta probarlo en una pantalla táctil real.
- [ ] **TRZ-14** Valores típicos, no de norma: tamaños de cada tipo, separaciones mínimas entre disciplinas y límites de ocupación son valores típicos; confirmarlos para cada proyecto contra su norma.
- [ ] **TRZ-15** Alineación entre disciplinas: dos disciplinas de un mismo nivel deben compartir el punto 0,0; avisar o alinear automáticamente.
- [ ] **TRZ-17** Táctil: pellizco y arrastre con dos dedos probados en pantalla táctil real; imán a vértices del fondo probado con un DXF real.
- [ ] **TRZ-18** Teléfono: el encabezado del trazado ocupa casi toda la primera pantalla; plegarlo para que el editor quede a la vista.
- [ ] **TRZ-19** Elegir símbolo con vista previa (biblioteca) y modos por disciplina (botonera propia de cada una).
- [ ] **TRZ-21** Reglas de separación de la empresa: hay API y panel dentro del proyecto, falta la pantalla en Datos de la consola.
- [ ] **TRZ-22** Más disciplinas con perfil propio (comunicaciones, climatización, civil, incendio): hoy solo hay eléctrica y cloacas, así que reglas como "fuerza y datos" no tienen con qué probarse.
- [ ] **TRZ-23** Pasos y aberturas coordinadas: hoy son un pedido con medidas; falta que aparezcan como marca en el plano de las dos disciplinas.
- [ ] **TRZ-24** Pendientes de antes: curvas en cables, elegir nodo intermedio de una ruta, desempate entre rutas iguales, valores de pendiente de cloacas de la norma, verificar el DXF en AutoCAD, GitHub Actions / Docker / migraciones, cobertura baja de los generadores por subproceso (sld, titleblock, mld, dxf).
- [ ] **TRZ-25** Subir `dev` a GitHub (solo cuando el responsable lo pida).
- [~] **TRZ-26** Fase 2, imágenes y PDF escaneado: paredes horizontales y verticales y huecos; sin arcos de puerta.
- [ ] **TRZ-27** Probarlo con planos reales de arquitectura y ajustar los umbrales (`params.json`): hasta ahora solo hay pruebas con planos sintéticos.
- [ ] **TRZ-28** Aceptar, corregir o borrar cada elemento reconocido (hoy se reconoce todo o nada); mostrar la confianza en el editor.
- [ ] **TRZ-29** Imágenes: paredes en diagonal, arcos de puerta (visión clásica) y planos fotografiados o torcidos.
- [ ] **TRZ-30** PDF de varias páginas y formularios anidados; rotación de página.
- [ ] **TRZ-31** Planos con mucho detalle: el fondo que dibuja el motor es simplificado (sin textos ni sombreados); ofrecer mantener el fondo fiel y superponer lo reconocido.
- [ ] **TRZ-32** Reglas de arquitectura para el trazado: avisar si una bandeja atraviesa una pared fuera de una puerta o ventana.
- [ ] **PLG-04** **Probar el agente con un pliego real**: el HVAC de `incoming/` (Parte 4, Especificaciones Particulares) como caso de comparación.

- [ ] **ARQ-39** `epc_arch.author`: ambientes que no son rectángulos (en L), muros de distinto espesor (exterior e interior), puertas dobles y corredizas, y escaleras.
- [ ] **ARQ-40** `epc_arch.review` (qué ambientes une cada puerta; ambientes sin puerta, sin nombre, con código repetido o con área escrita distinta de la medida): mostrarlo en el editor y pasarlo al pipeline como hallazgos de nota.
- [ ] **ARQ-41** Ubicar el tablero contra un muro del ambiente (hoy `{"room": ...}` lo pone en el centro).
- [ ] **ARQ-42** Alzados y secciones (`epc_arch.sections`, hecho 2026-11-15: alzado N/S/E/O, sección por plano x o y, apilado de plantas, lámina y DXF): falta pedir las alturas en el formulario o el editor, muros oblicuos, alturas por muro o por abertura, techos inclinados, escaleras, cotas de nivel y sacarlos como entregables del pipeline (ADR-0032, fase F4).
- [ ] **ARQ-43** Canalizaciones y cañerías en 3D (`epc_plan.solid`, hecho 2026-11-15: sólidos, mallas, escena para visor, isométrica y DXF 3D): falta el visor 3D del navegador (ADR-0032, fase F2), los accesorios (codos, tes, reducciones), dibujar la isométrica en lámina y la salida IFC (fase F5).
- [ ] **ARQ-44** 3D de todo el proyecto y cortes de detalle (hecho 2026-11-15: `epc_arch.model3d` da el edificio con muros abiertos en puertas y ventanas, losas y vidrios; `epc_plan.scene3d` une edificio y servicios, saca el modelo en DXF 3D y OBJ, y corta todo con un plano: sección en DXF 2D con tamaños reales, etiqueta y nivel de cada servicio cortado). Sin interfaz web (decisión del dueño, 2026-11-15). Falta para llegar a LOD 400: soportes y fijaciones, accesorios (codos, tes, reducciones, cajas), luminarias y tomas en 3D, cotas automáticas en la sección, ocultar líneas tapadas en lo que se ve detrás del corte, poner la sección en lámina IRAM con rótulo y sacarla como entregable del pipeline.
- [ ] **ARQ-45** Disciplinas de edificio y de planta en 2D y 3D (hecho 2026-11-15: perfiles nuevos de pluviales, agua fría y caliente y gas; incendio, HVAC, cloacas y mecánica ampliados con montantes, bombas, tanques, equipos, parral de cañerías, ascensores y puente grúa; sus capas en el catálogo; montantes y bajadas como tramos verticales en 3D). Son perfiles de representación: sin cálculo ni valores de norma. Falta: símbolos 2D propios (hoy reutilizan los existentes), reglas de separación entre estas disciplinas (`clash_rules.json`, valores que confirma el ingeniero), estructura (losas, vigas y columnas en 3D desde `civil`), los cálculos de cada una (hidráulica de incendio, pendientes pluviales, caudales de aire) y sus motores, y un tramo vertical dibujado entre dos niveles en vez de un nodo con altura.
- [ ] **ARQ-46** Modelo de fabricación hacia LOD 400 (`epc_plan.detail`, hecho 2026-11-15: tramos rectos con largo de corte, codos a inglete con su ángulo, tes, reducciones, soportes colgados de la losa (trapecio para bandejas y ductos, varilla para caños), cómputo de piezas; el corte escribe etiqueta, tamaño, nivel, nivel de fondo y una cadena de cotas). En el pipeline desde 2026-11-15: con `engine_inputs.model3d` (alturas de cada planta, y opcionalmente separación de soportes y cortes) la etapa 10 escribe `<tablero>_model_3d.dxf`, `<tablero>_section_<nombre>.dxf` y deja el cómputo en sus salidas; la etapa 12 los empaqueta. La separación de soportes y las alturas son datos de entrada, sin valor por defecto. Falta para LOD 400 completo: pedir esos datos en el formulario guiado, el cómputo como planilla entregable (hoy queda en las salidas de la etapa), bridas, uniones y tapas, fijaciones a la estructura, soportes de tramos verticales, partir el tramo principal en una te, codos de radio y piezas de catálogo del fabricante (hoy son geométricos), ocultar líneas tapadas detrás del corte, cotas verticales, la sección en lámina IRAM con rótulo, y las demás disciplinas en la corrida (hoy el pipeline rutea solo la eléctrica; los motores ya dibujan todas).
- [ ] **ARQ-38** **Fotos con OpenCV** (Apache-2.0, `opencv-python-headless`): corregir la perspectiva marcando 4 puntos, detectar líneas en cualquier ángulo (hoy una imagen solo lee muros horizontales, verticales y a 45°), normalizar sombras e iluminación. La escala de una foto sin escala escrita sale de una calibración manual (dos puntos y la distancia real). OCR opcional con Tesseract (Apache-2.0) para cotas y escala escrita. Los clientes entregan fotos, PDF o DWG, casi nunca IFC. (Arquitectura (`epc_arch`))
- [ ] **ESP-01** Exportar a DXF los mapas de lux y el plano de tomacorrientes, y todo lo de optimizar el DXF (decidido el 2026-11-01; ver `ILU-20`).
- [ ] **ESP-02** Modelo único 2D/3D con exportación IFC ([ADR-0032](architecture/decisions/ADR-0032-single-2d-3d-model.md)), fases 1 a 5. DWG no se necesita.
- [ ] **ESP-03** Subir `dev` a GitHub (solo cuando el dueño lo pida).
- [~] **PV-12 · Conectar `epc_pv` a los datos de equipos** (2026-11-20). Hecho: `epc_pv.equipment` (inversores derivados de las 10 fichas, estructuras, formatos y tecnologías de módulos, accesorios, referencias de factibilidad), empaquetado de subcarpetas, `inverter_catalog.json` ya no se lee (doble fuente resuelta), fundación del modelo 3D tomada del registro de la estructura (`structure_id`). Falta: **(Dueño)** aprobar el borrado de `inverter_catalog.json` (hoy queda como archivo sin lectura, con un test que lo compara con los datos derivados); elegir la estructura automáticamente según sitio y módulo (hoy la indica el usuario); usar los accesorios en el cómputo y el pedido de cotización; usar los CAPEX/O&M, LCOE, sombreado y la incertidumbre en el estudio de factibilidad; los inversores con datos ambiguos (Symo, SG110CX, SH10RT, SolarEdge, Enphase, Victron) esperan que una persona confirme la ficha.
- [~] **PV-13 · Detalle 2D y 3D del equipamiento PV desde los JSON** (2026-11-20). Hecho: módulo (marco, caja de conexiones, celdas), inversor (envolvente, bornes, display, interruptor) y postes con el perfil del registro en el 3D, y la hoja de detalle 2D `<nombre>_pv_equipment_detail`; capas `PV-3D-REF-*` por estado del dato. Falta: riostras, ménsulas, abrazaderas y bulonería (los registros no traen posiciones ni largos), sección del marco del módulo y tamaño de celda (no están en ningún registro, se dibuja un valor de referencia marcado), perfil de los postes `not_found`, detalle en los planos de cubierta (`pv_roof`), techos con faldones en el 3D y el nivel de detalle `full` (una cara por celda) como opción de la landing. **(Dueño)** confirmar los datos cuando los considere verificados.
- [ ] **PV-10** Proyecto PV completo (análisis de brechas 2026-11-19, `/mnt/project-files/pv/INFORME_brechas_PV.md`): hecho el paso PVGIS (`epc_pv.weather`), `weather_file` en la etapa 3 y el proyecto PV de la landing (latitud y longitud, 12 etapas). Hecho también: el harness elige inclinación y azimut (`epc_pv.orient`) y coloca los módulos en un faldón de techo (`epc_pv.plan_roof`, un faldón en la landing). Hecho 2026-11-19: planos de cubierta (`epc_drawing.pv_roof`: implantación, conexionado de strings y cableado CC referencial, hoja IRAM en `08_PV`), varios faldones (un arreglo y sus strings por faldón; hasta cuatro en la landing) y lectura del DXF de cubierta (`epc_pv.roofdxf`, `roof_dxf` en la etapa 3, capas `PV-CUBIERTA`, `PV-CUBIERTA-OBST`, `PV-CUBIERTA-DATOS`). Pendiente de PV-10, sin valores inventados: succión del viento y lastre (no hay valor de viento en el registro de normas; cada resultado de cubierta lo dice con el aviso `roof_wind_pending`), faldones que no son rectángulos ni están alineados con los ejes, y la subida del DXF de cubierta desde la landing. Falta, en este orden: sombras de obstáculos, cables CC/CA y caídas, protecciones y aporte de cortocircuito del generador, puesta a tierra PV, generación en la lista de cargas y conexión a red, autoconsumo, documentos PV (memoria, cómputo, pedido de cotización), curva del inversor, sombras, factibilidad económica, plan O&M, puesta en servicio IEC 62446-1, MT. Los valores típicos siguen `pending review` (solo una persona aprueba). Hecho 2026-11-19 (PV-11, formulario mínimo): el usuario solo indica la estructura (techo con faldones, o predio) y la ubicación; el motor llena la estructura con módulos (`layout.fill` en la etapa 3, reglas de `epc_pv.flatroof`), elige el inversor del catálogo (`inverter: auto`, `epc_pv.catalog`), usa módulo por defecto, y la potencia pasa a ser resultado (`target_kwp` solo es un tope). Los strings son enteros: el relleno recorta a strings completos que caben. Supuestos marcados como nota en cada corrida, siempre `pending review`: Isc máx. por MPPT faltante (no se inventa: se limita por la corriente de operación y la corrida avisa que el límite de cortocircuito no se verificó), mesa achicada si no entra en el predio, altura libre de 0,5 m, inversor elegido, auxiliares típicos (1 kW, monofásico, 20 m: una carga mínima es obligatoria, regla IV-01). Huso horario: sale de la ubicación (`epc_pv.timezone`, base offline `timezonefinder`, hora estándar). El cliente pone su propio precio de energía (y opcionalmente su costo de inversión): ahorro = kWh anuales × precio, repago simple = inversión / ahorro; nada se inventa (`economics`). Sim-01 (2026-11-19) corrigió: mesa que no entra, Isc que daba 24 inversores, altura libre en 0 y `tmp/` del repo como carpeta de simulación; el MLD no aplica a una planta sola (solo con ruteo de edificio). Módulo automático (2026-11-19): el harness prueba todos los módulos del catálogo con dimensiones (y mesa vertical u horizontal) y se queda con el que instala más potencia total en la estructura (`epc_pv.modulepick`); 9 módulos del catálogo no tienen dimensiones en la hoja (SunPal y otros) y por eso no compiten, sin inventar medidas. 3D automático (2026-11-19): de la estructura en 2D el harness levanta solo el modelo 3D (`epc_drawing.pv_model3d`, un DXF con caras sólidas: suelo, módulos inclinados, rieles, postes, bases de inversores y estación) en `05_3D` de la transmittal; los postes y rieles son geometría de referencia, sin cálculo de viento ni lastre; falta el 3D de techos con faldones y el tablero. Pendiente: leer la estructura desde un modelo 3D (FreeCAD) como dato de entrada, y probar también el ancho de mesa que mejor llena el espacio. Pendiente: costo estimado y LCOE con las referencias CAPEX/O&M (pendientes de revisión), degradación y aumento de tarifa. Los campos de ajuste quedan plegados en «Avanzado» de la landing. Pendiente: mesas ya definidas (cantidad y tamaño), cocheras y seguidores.
- [x] **PVX-01 · Fixes from the PV stress test (pvmax, 2026-11-20).** `inverter: auto` raised for the MPPT input current now says the installed count and the real DC/AC (`inverters_raised`, en/es; before, `inverter_auto` said 90 units at 1.2 while 112 were installed at 0.96). The landing form has a `structure_id` field (ground or roof structures of `epc_pv.equipment`, checked against the plant kind). The auxiliary load of a plant-only run carries `kind: rcbo` (the only major finding of every run was the missing residual-current device on a TT board). Stage 10 writes the PV 3D model of a plant above 20 000 modules as parts and blocks (a block per distinct table and inverter, a DXF per sector of at most 20 000 modules, a common DXF, and a master DXF that attaches them): 49 MWp 939 MB to 7.7 MB, 206 MWp runs (75 s, 233 MB). Lessons in `docs/lessons/` (LL-0001 to LL-0005).
- [~] **PVX-02 · Stage 10 memory and size on big plants.** Done: the 3D in blocks, sectors and a master (see PVX-01), and a clear bilingual error when the system kills a run (`cli_killed`, 2026-11-20). Left: the 2D sheets of a 206 MWp plant are 19 MB and not split; probe plants beyond 206 MWp to find the real limit; open the master with its parts in AutoCAD, Revit and FreeCAD (only read back with ezdxf).
- [ ] **PVX-03 · Mixed plants (roof and ground in one project).** The `pv` section takes `layout`, `roof` or `flat_roof`, one of them; the form's `mode` is one or the other. Needs several plant areas, each with its own arrays, and the drawings and documents that sum them.
- [x] **PVX-04 · Roof plants: 3D, equipment detail sheet and plant single-line.** Done 2026-11-21: 3D model (`pv_roof_model3d`), equipment detail sheet and plant single-line (`pv_roof._sld`, inverters without positions, library symbol). Left (own item): place the roof planes on a building when its model exists.
- [ ] **PVX-05 · Inverters in the gap between rows (`layout_pad_tight`).** Every plant with 0.5 m clearance and 2.3 m tables warns that the pad does not fit the gap, and the 3D draws the inverters there anyway. Decide where they go (end of the row, outside the field, or a central station) and place them accordingly. Needs a design decision.
- [~] **PVX-06 · The board, the memorandum and the terminal list do not grow with the plant.** A 49 MWp plant with 512 inverters still produces one 3-terminal auxiliary circuit (`E-AUX-01`). Done 2026-11-21: the PV yield study lists modules, strings, inverters, module weight and every placed inverter; the BOQ (`epc_boq.build_boq(equipment=...)`, when the engineer gives the wastage allowance) lists the modules, strings and inverters of each array (`PVE-nnn`). Done 2026-11-21: a plant-only project gets one AC feeder per inverter in the board (`stages/pv_feeders.py`; the plant runs first in stage 3 and its `inverter_ac_kw` feeds the board form), so the board, the cable list, the terminal list and the memorandum grow with the plant and the engine sizes each cable and protection; the form asks phases and run length (`feeder_phases`, `feeder_length_m`, proposals pending review). Not added to a building project (generation is not consumption). Left: DC string cables and DC protections (need norm values recorded `pending review`: nothing is invented), the generation as a line of the load list.
- [x] **PVX-07 · FreeCAD export from the harness model.** Done 2026-11-20: stage 10 writes `<name>_pv_model_3d_freecad.FCMacro` (`epc_drawing.pv_freecad`) in `05_3D`: every distinct table and inverter is one part, every instance an `App::Link`, same faces as the DXF (module detail, structure sections). Not run against FreeCAD in CI (the macro is checked as valid Python and by counts); open it with File > Macro > Execute. Left: STEP/FCStd output and the `full` detail level on the landing.
- [x] **PVX-08 · The time zone needs `timezonefinder`.** Done 2026-11-20: the form says `pv_timezone` (en/es) naming the missing package, or that the point has no zone, and asks for `utc_offset_h`.
- [~] **PVX-09 · The harness compares alternatives and builds the best one (owner request, 2026-11-20).** Done 2026-11-21: a ground plant filled to its site already tried every module, both orientations and the tilts; now it also tries every fixed-table ground structure that states a tilt range (`flatroof.compare_structures`, ranked by modules x kWh/kWp) and the PV study shows the tilts and the structures compared (`Alternatives compared`). The structure of the project stays the one the person gave. Left: compare foundation and cost (needs prices and foundation rules), pick the structure automatically when the person gives none (it implies a foundation), vary the row pitch and the table shape, and the same table for roof plants. The 3D format is the person's choice (`model3d_format`).
- [~] **PVX-10 · Part library from the equipment records (owner request, 2026-11-20).** Done 2026-11-21: `epc_drawing.part_library` draws any record with a `geometry` (50 parts of 85 records today) as DXF blocks and a FreeCAD macro (`python harness/tools/build/part_library.py`); the schemas of inverters, modules and structures accept `features` (dot, box, hole, label); the tilt range of a structure record limits the tilts tried on a flat roof; the PV study states the module weight. Left, and blocked by data: fill `features` and the missing positions and lengths (post embedment, beams, purlins, braces, connector sets in 35 records) from data sheets the owner provides, `pending review` (nothing is invented); the 25 accessories and the 13 module technologies are drawable but no rule selects them for a plant (needs the owner's design rule, e.g. one combiner per N strings); build the plant from the library parts instead of the module and inverter code of `pv_model3d`.
- [ ] **PVX-11 · Minimal web viewer of the part library (owner request, 2026-11-21).** A single local page (in `harness/tools/landing/`) where the author picks a part, sees it rendered in 3D (orbit, zoom, colours by data status, list of skipped elements) and says what to change ("make the dot bigger"); the page reads the part faces that `epc_drawing.part_library.faces` already produces, so the record stays the only source. SVG only as a generated 2D view for review, never as the source (ADR-0012).
- [~] **PVX-12 · Electrical symbols as SVG, parts as JSON (owner decision, 2026-11-21).** 3D parts stay in JSON records (ADR-0012). The IEC 60617 symbol library already has SVG sources converted to DXF blocks (`epc_symbols`, includes `pv_module`, `inverter`, `dc_disconnect`, `spd_varistor`, `fuse`, `energy_meter_kwh`); the PV single-line now draws its inverters with the library symbol. Done 2026-11-21: the PV single-line also draws `pv_module` (strings), `dc_disconnect` (isolator) per inverter and `energy_meter_kwh` at the station. Left: string combiner and AC protections in the single-line (needs the protections the harness does not yet size), and PV-specific symbols the library lacks (combiner box, string).
- [ ] **PVX-13 · Leftovers of the PV work, recorded when the thread closed (2026-11-21).** (a) DC string cables and DC protections (string fuses, DC isolator sizing) need norm values from a source the owner provides, recorded `pending review`; the plant generation as a line of the load list. (b) The FreeCAD macro (PVX-07) is only compiled and counted in tests: run it inside FreeCAD and check the model; STEP/FCStd output. (c) Place the roof planes on a building model when one exists (PVX-04). (d) String combiner and AC protections in the PV single-line (PVX-12). (e) Compare foundation and cost, pick the structure automatically, vary row pitch and table shape (PVX-09). (f) Split the 2D sheets of a 206 MWp plant and probe beyond it (PVX-02). Needs the owner: PVX-03 (mixed plants), PVX-05 (inverters between rows), the accessory selection rule and the data sheets for PVX-10.

- [ ] **AUD-01** (auditoría 2026-11-20, `/mnt/project-files/auditoria/INFORME_auditoria_motores_pipelines.md`, H4 y H5) Las 177 reglas AEA (`config/normative/AR/electrical/aea90364/rules/`) solo las consulta `norm_review.py`; `epc_rules` no tiene llamadores y `epc_aea90364/standards/` está vacío. Decidir (Dueño) si las reglas alimentan la etapa 2 y `calc_check` y unificar con `criteria.json` (`raceway_fill_max_pct`), sin cambiar valores de norma.
- [ ] **AUD-02** (H6) Llamar `epc_documents.document_verifier` desde la etapa 12 (cierre del paquete).
- [ ] **AUD-03** (H7, H8) `epc_pv` aún no lee `row_spacing_kf.json`, `typical_losses_reference.json`, `solar_resource_reference.json`, `tracker_ratio_by_province_ar.json`, `climate_monthly_temp_air_ar.json`, la curva de eficiencia del STP25000 ni `feasibility/*`. Espera al hilo «Conectar epc_pv a los JSON nuevos».
- [ ] **AUD-04** (H9, H10) `catalog_dir` de datasheets no se fija por defecto y no hay hojas de datos de PV; `epc_lighting/data/luminaires.json` y `harness/catalogs/manufacturers` son dos fuentes de la misma clase de dato.
- [ ] **AUD-05** (H13, H14) El MCP `epc` solo expone el pipeline; los bloques `model3d`, `boq`, `datasheets`, `rfq`, `hvac`, `receptacles` de `engine_inputs` no los pide ningún formulario.
- [~] **NAM-01 · File-name convention** (owner, 2026-11-24): `harness/docs/NAMING.md`, gate check `file-names`, legacy list `harness/tools/ci/file_names_legacy.json` (can only shrink). Done: six data files renamed. Pending: rename the rest of the list by batches (PMO scripts, norm-register `code-*.json`, PV inverter files, agents), each with its references.
- [~] **DRW-02 · One drawing engine, called and parallel** (owner, 2026-11-24, ADR-0042 proposed): `epc_draw` with one function per kind of drawing over one kernel; every call receives all its data and returns the drawing as bytes; two calls never share state. Steps: (a) done 2026-11-24 as a static guard: `tests/architecture/test_drawing_purity.py` counts environment, folder, process, temporary-file and clock uses per drawing-engine file (24 in 14 files today) and the baseline only shrinks; still to do: the dynamic test (threads and processes, same bytes as sequential); (b) done 2026-11-24: `epc_dxf.settings` hands the layer and text settings in as data; (c) symbol and title-block inputs as data; (d) writers return bytes, the caller writes; (e) kernel and first drawing kind into `epc_draw`; (f) remove the old engines one by one. Goldens never change; a step that would change one waits for the owner.
- [ ] **INP-01 · Any file in, read by the model** (owner, 2026-11-24): one intake reader per format that hands the model what is in the file. Today only DXF plans are read by the pipeline (`epc_arch`); PDF and spreadsheet reading lives in separate plugins (`standard-ingest`, `intake-analysis`) and Word and images have no reader. Steps: (a) list the formats and who reads each; (b) one `read_input` function per format (DXF, PDF, XLSX and CSV, DOCX, images, plain text) as data in, data out (ADR-0042), with source and page; (c) an unreadable format (for example DWG) answers a bilingual error that names the format to send; (d) the guided form and the agents call it for every file in `inputs/`; (e) copyright: read, never store, extracted data only to `.json`.
