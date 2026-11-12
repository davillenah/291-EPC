# epc_terminal_blocks

Status: **in development**

Quality engine (MIG-39b, PRD section 12 stage 15, "Documents and lists"): builds the terminal-block list (planilla de bornes) of a calculated board. Pure functions, standard library only, no I/O at import and no file output. It has tests but stays `in development`: the terminal size table is generic and pending review, and no document renderer consumes the list yet. Its outputs are drafts (D21).

## Public API
- `build_terminal_list(board_name, circuits, *, start_strip="X1")`: dict `{board, strips: [{strip, rows}], totals, assumptions, norm_records, issues}`. One strip; every row is one circuit: `{circuit, description, device, phases, in_a, conductors, terminals, issues}`; every terminal: `{id ("X1:1", "X1:2", ...), role, section_mm2, terminal_size_mm2, terminal_rated_a, issues}`. `totals` = `{terminals, by_section, by_terminal_size}`.
- `render_rows(terminal_list)`: flat list of dicts, one per terminal (`board, strip, terminal, circuit, description, device, conductors, role, section_mm2, terminal_size_mm2, terminal_rated_a, issue`). No file is written.
- `conductors(circuit)`, `terminal_sizes()`, `accepting_size(section_mm2, table=None)`, `clear_cache()`.

## Input format
`circuits`: a non-empty list, in board order, of objects with keys `tag` (non-empty text, unique), `phases` (1 or 3), `s_mm2` (> 0) and the optional `pe_mm2`, `neutral_mm2`, `in_a` (> 0 or `None`), `description`, `device`. They are the values the calculation stages report for each circuit (stage 8: `s_mm2`, `pe_mm2`, `neutral_mm2`, `in_a`; `fases`, description and device from the engine detail). Unknown keys, duplicate tags and invalid values raise `ValueError` with a clear message.

## Behaviour
- Conductors terminated: `L` (1 phase) or `L1 L2 L3` (3 phases) at `s_mm2`, `N` when `neutral_mm2` is given, `PE` when `pe_mm2` is given. A missing N or PE section adds a note to `issues` (no terminal is invented).
- Terminal ids are sequential over the whole strip in the order given, so the list is deterministic (no clock, no random ids).
- Terminal size: the smallest size of the table whose accepted range contains the section (comparison only). If none does, the terminal has no size and the issue `<tag>/<role>: no terminal size accepts section X mm2` is raised; no size is guessed. If `in_a` is given and the terminal rating of a phase conductor is lower, an issue says so (comparison only).

## Data and provenance
`data/terminal_sizes.json`: generic sizes 2.5, 4, 6, 10, 16, 35 and 70 mm2, each accepting its own section and the standard section below, with placeholder rated currents. Provenance: catalog/convention; no clause located. Review status: **pending review**: verify every value against the chosen manufacturer catalog. Recorded in `norm_register/params.json` (`terminal_blocks.params.terminal_sizes`, status pending). Nothing here is verified.

## Not modelled
Strip splitting or grouping by voltage level, spare terminals, marshalling and shared terminals, accessories, terminal derating, whether a given load really uses a neutral (the calculation reports one for every circuit), sections above 70 mm2 (they appear as issues), any electrical calculation.

## Depends on
Nothing (standard library). It never imports a discipline, the platform or the web.

## Tests
`python -m unittest discover -s tests` from this folder (every engine `src/` on `PYTHONPATH`, as the gate does).
