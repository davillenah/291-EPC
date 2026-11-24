# ADR-0042: One drawing engine, called as a function and safe to run in parallel

Status: proposed (owner request, 2026-11-24). Builds on ADR-0038 (engines are called, not watching), ADR-0040 (single entry points) and BACKLOG DRW-01 / OPT-05.

## Context
Drawing is split in eight engines (`dxf`, `symbols`, `titleblock`, `plan`, `arch`, `sld`, `mld`, `drawing`). Audit of 2026-11-24 over their `src/`:

| engine | lines | environ | file I/O | module state / cache | cwd, tmp, processes |
|---|---|---|---|---|---|
| dxf | 1812 | 3 | 12 | 6 | 2 |
| symbols | 208 | 0 | 3 | 0 | 0 |
| titleblock | 1334 | 0 | 8 | 0 | 4 |
| plan | 3118 | 0 | 10 | 0 | 2 |
| arch | 7775 | 3 | 27 | 2 | 7 |
| sld | 1075 | 2 | 7 | 0 | 3 |
| mld | 502 | 2 | 6 | 0 | 0 |
| drawing | 3494 | 2 | 35 | 1 | 14 |

`epc_dxf` still reads layer, text-style and sheet settings from environment variables (`EPC_LAYERS_JSON` and two more). `epc_sld.draw` still takes paths of files (`xlsx`, `calc_json`, ...) and not the data itself. Several engines write their result to disk inside the call.

## Decision
1. **One drawing engine** (`epc_draw`) with one function per kind of drawing (`draw_sld`, `draw_mld`, `draw_plan`, `draw_pv`, `draw_arch`...), over one kernel (DXF writing, symbols, title block, layers). The other modules of the project call it; it calls nothing outside itself.
2. **Called, never searching.** Every function receives all its data (the model, the symbols it needs, the layer and style tables, the title-block data, the date) and returns the drawing as data: the document in memory plus the list of its files (name, bytes). It reads no file, no environment variable, no clock and no folder; the caller writes the bytes where it wants (ADR-0038).
3. **Parallel by construction.** No module-level state that a call changes, no caches that depend on the process, no current-directory use, no temporary file with a shared name, no subprocess. Two calls with the same input give the same bytes whatever else is running. This is checked by a gate test that runs the same jobs in threads and in processes and compares the bytes with a sequential run.
4. **Same bytes.** A conversion step keeps every golden file byte for byte. A step that cannot is stopped and put to the owner.
5. **Order, smallest risk first:** (a) the parallel-safety test, as a measurement, listing what fails; (b) the settings that travel as data (layers, text style, sheet format): `epc_dxf` stops reading the environment; (c) the symbol and title-block inputs as data; (d) the writer returns bytes and the caller writes; (e) the kernel and the first drawing kind move into `epc_draw` (SLD, then MLD, plan, PV, arch), each behind its old public function until the callers move; (f) the old engines are removed one by one.

## Consequences
- Fewer packages to register and a single place for a drawing rule (layer, size, text).
- A drawing job can be sent to a pool of workers; the number of workers is the caller's choice.
- Steps (b) to (d) change no behaviour and are done first; (e) and (f) are large and each is its own pull request.
