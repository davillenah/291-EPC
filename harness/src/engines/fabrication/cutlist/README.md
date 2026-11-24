# epc_cutlist

Status: **in development**

Fabrication engine: the one-dimensional cutting plan (cut list) of bars, trays, conduits, profiles, rails or cables. It is generic and holds **no norm value, no catalog and no price**: stock lengths, saw kerf, part lengths and cut angles are inputs. Pure functions, standard library only, no I/O at import and no file output. Its output is a draft (D21).

## Public API
- `build_cutlist(stock, parts, *, kerf_mm)`: dict `{kerf_mm, bars, summary, totals, groups, marks_legend, assumptions, issues}`.
- `render_rows(plan)`: flat list of dicts, one per placed piece (`bar_id, material, stock_length_mm, part_id, index, length_mm, angle_1_deg, angle_2_deg, marks, bar_used_mm, bar_left_mm`). No file is written.
- `CutlistError`: a stable `code` with an English (`en`) and a Spanish (`es`) text (ADR-0039).

## Input format (schema: `src/epc_cutlist/schema/input.schema.json`)
- `kerf_mm`: REQUIRED. The width of each cut in mm; 0 is allowed (cutting cable), negative is rejected, there is no default.
- `stock`: `{material: [length_mm | {length_mm, count}, ...]}`. A `count` limits how many bars of that length exist (a drum on hand); without it the stock is unlimited. Material names are case-insensitive.
- `parts`: a non-empty list of `{id, material, length_mm, quantity?, size?, label?, angle_1_deg?, angle_2_deg?, angle_source?}`. Ids are unique. Angles are signed degrees from a square cut (0), from -90 to 90, and are inputs: the engine never calculates one. `angle_source` is `given` (default), `derived` or `unknown`.

## Behaviour
- Per material, the pieces (one per unit of `quantity`) are sorted from the longest cut size (length plus kerf) to the shortest and placed one by one into the open bar that leaves the least space; if none fits, a new bar of the **shortest** stock length that holds it is opened (respecting `count`). Best fit decreasing is a heuristic, not a proven optimum. Every cut consumes the kerf, including the last one of a bar (conservative).
- The plan is deterministic: the same input gives the same plan, whatever the order of `parts`.
- `groups`: equal parts (material, size, length rounded to 0.1 mm, both angles, angle source) in one line with the total quantity and the ids.
- Marks on the cut angles: `-` both ends cut in the same direction (no need to turn the bar over), `~` an angle derived from another part (check it), `?` the angle could not be determined (reported in `issues`). `marks_legend` carries the text of the marks used, in English and Spanish.
- Errors: the part is longer than the longest stock (`err_part_too_long`), no stock for a material, limited stock used up, invalid values, unknown keys, duplicate ids.

## Data and provenance
No data table and no norm value: there is no norm register file and nothing to review. The method (best fit decreasing, the standard heuristic for one-dimensional cutting stock) is a public algorithm. The design follows the behaviour described in the PRD of the drawing engine (annex 7), written here from scratch.

## Not modelled
Cut direction and the 90-degree rotation mark, length compensation of mitred ends, prices, optimal (exact) packing, two-dimensional nesting, offcut re-use between jobs.

## Depends on
Nothing (standard library). It never imports a discipline, the platform or the web.

## Tests
`python -m unittest discover -s tests` from this folder with `src` on `PYTHONPATH`.
