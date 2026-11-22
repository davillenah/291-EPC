# epc-symbols

IEC 60617 symbol library for single-line (SLD) and multi-line (MLD) diagrams, LV and MV: SVG and DXF blocks with catalogs.
`epc_symbols.library_dir(kind)` gives the folder of a library. Build scripts for the library: `tools/symbols/`. Depends on nothing.

## API (SYM-01, `epc_symbols.registry`)

Engines ask for a symbol by id and view; they never open a symbol file or build a file name (PRD `docs/prsad/PRD-symbols.md`).

- `resolve(symbol_id, view=None)` gives a `SymbolRecord` (qualified id `<domain>.<catalogue id>`, domain, view, titles in English and Spanish, size, terminals, label slots, SVG and DXF files, block name). It accepts the catalogue id, the qualified id and the file name with or without extension. A missing symbol raises `UnknownSymbol` (message in English and Spanish), never a stand-in; an id that exists in more than one view raises `AmbiguousSymbol` until the view is given.
- `list_ids(domain=None, view=None)`, `terminals(id, view)`, `svg_fragment(id, view)`, `dxf_block(id, view)` (file and block name) and `insert(doc, id, view, at, scale, layer, attribs)` (one INSERT, one block definition per document; needs `ezdxf`, imported only when called).
- Domains and views: `electrical-lv` (`sld`, `mld`), `electrical-mv` (`sld`, `mld`, `ssd`). The catalogue schema is `schema/symbol_catalog.schema.json`.
