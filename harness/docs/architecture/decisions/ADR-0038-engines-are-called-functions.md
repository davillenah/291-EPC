# ADR-0038: Engines are called, not watching (a set of functions that receives its data and answers)

Status: accepted (owner, 2026-11-22). Follows ADR-0012 (one source of truth per datum) and ADR-0037 (relational diagram model).

## Context
Some engines look for their own input: they read workbooks, JSON files and environment variables, or spawn subprocesses that read them again. The SLD, for example, is driven by `SLD_*` environment variables and an Excel file written only to be read back. This costs time, hides what an engine depends on and duplicates data that the caller already holds.

## Decisions
1. **An engine is a set of functions with one public entry point.** A caller hands the entry point all the data it needs and the engine returns its answer. Inside, the engine may have many functions (for the SLD: paginate, draw a sheet, table, export); none of them searches for anything. It stays an engine (its own package, version, tests, schema).
2. **No self-sourced input.** An engine does not read files, workbooks, environment variables or the project folder on its own, and it does not watch for work. Nobody asks for a netlist, the netlist engine does nothing.
3. **Callers hand everything over.** The assembler (single hand-over, ADR-0037) passes the assembled description plus the label slots, board figures, header, title block and layout. Writing the result to disk is the caller's choice, or an explicit output argument.
4. **Command-line entry points stay** as thin adapters that read the inputs and call the function. The adapter holds the I/O, the function holds none.
5. **Same output.** A conversion must give byte-identical files for the same input (checked by the deterministic-design tests) before the old path is removed.
6. **Conversion is engine by engine, SLD first** (`epc_sld.draw(entrada, out_dir, name, maxl, stamp_date)`), then the MLD, then the remaining engines (BACKLOG DGM-16).

## Consequences
- Fewer subprocesses, fewer temporary files and no environment globals; the dependencies of an engine are its arguments.
- Engines are easier to test (a dict in, a result out) and to call from the MCP server.
- Existing engines that still read their inputs are legacy until converted; the backlog tracks them.
