# Bridge: research data -> drawing engine (data only)

Nothing here changes the repo. It reads `harness/src/engines/cad/symbols` (library `_catalog.json`, which already has ports and label slots) and links it to the research JSON.

- `device_symbol_map.json`: 57 research devices -> library symbol ids (+ MLD 1p-4p variants, ports). 51 mapped (exact or close name match, all `unverified`; "close" ones need a person to confirm), 6 without a symbol (`not_found`): IMD, blocking diode, power optimizer, rapid shutdown device, RCMU, string combiner box.
- `netlist.schema.json`: proposed contract for a project netlist: instances (IEC 81346 tag, device id, symbol id, label values from an engine) and connections `TAG:PORT -> TAG:PORT`.
- `netlists/example_pv_strings_sld.json`: example validated against the schema; every symbol id and port exists in the library catalog.

Open points (not decided here): how the SLD/MLD engines receive inputs today (`SLD_CALC_JSON`), where the netlist would be produced, and whether the drawing engine would take it directly. Numbers in `labels` must come from engines, never by hand.

## Derived netlists (17)
`netlists/netlist_<scheme>.json` are generated from the `chain` of each research scheme (9 LV/MV + 8 PV). Limits: the chain is linear, so shunt devices (SPD, surge arresters, metering taps, earthing) are wired in series; tags are assigned by device kind (IEC 81346 letter, typical); devices with no library symbol keep `symbol: null`. They prove the contract works; a person or the project netlist step must fix branching before drawing. Validate everything with `python3 -I ../validate_all.py`.
