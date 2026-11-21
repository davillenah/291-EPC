# PV SLD and MLD: definitions, minimum content, drawing conventions

Research for the harness PV single-line (SLD) and multi-line (MLD) generator, LV and MV. Facts only, sourced on 2026-11-20. No PDF or protected text is stored; short citations and URLs only.

Status vocabulary: `unverified` = sourced, not checked by a person; `typical` = generic industry practice without a source; `not_found` = not found in the fetched sources, never guessed; `pending review` = value quoted from a norm, waits for a person. Nothing is `verified`.

Machine-readable data: `schemes/*.json` (8 architectures), `devices/*.json` (14 new PV devices), `pv_decision_rules.json` (17 rules, 5 conflicts). Schema: `schema/pv_sld_mld.schema.json`. Existing SLD/MLD ids (`fuse_gpv`, `spd_type2`, `rcd_type_b`, `switchboard_tgbt`, ...) are reused from `../sld_mld/devices/`.

## 1. What each diagram is

| Diagram | Meaning | Lines drawn | PV use |
|---|---|---|---|
| SLD (unifilar) | One line stands for all phases and the DC pair | Single line with device symbols and ratings | Power path: strings, combiner, inverter, AC board, point of connection |
| MLD (multifilar) | Each phase, neutral and earth drawn separately; DC drawn as + and - | Three phase lines, N and PE; DC+ and DC- | Detail of inverter connection, earthing, RCD and SPD wiring, islanding switch |

The MLD definition is `typical` (generic practice). No fetched source defined the MLD in this run. The SLD content list is in section 2.

## 2. Minimum content of a PV SLD

Typical minimum for a grid-tied PV SLD (`typical`, consistent with the sources in the other files):

1. PV array: strings, with module count and Voc / Isc per string (value from the module datasheet, not from this research).
2. String protection: string fuses or overcurrent breakers where reverse current is possible (see `pv_dc_protection.md`).
3. DC SPD at the DC entry (type 2 at combiner or inverter; type 1+2 where an external LPS requires it).
4. DC isolator (load-break, rated for U_OC MAX). Fuses are not isolation.
5. Inverter, with its DC and AC ratings and its internal RCMU.
6. AC isolator (switch-disconnector) between inverter and board.
7. AC overcurrent device at the inverter output (and at the point of connection).
8. RCD where local rules require it (type per `pv_ac_protection_and_interconnection.md`).
9. Bidirectional meter at the point of connection (`typical`: utility sets the model).
10. Point of connection to the LV board, with its overcurrent device.
11. Earthing system indicated (TT, TN-S, TN-C-S, IT), and whether the inverter is transformerless (`unverified`, `ei_pv_safety`).
12. Interface relays where the utility requires them (ANSI 27, 59, 81O/81U, 32R, 67; `unverified`, `oeb_der_protection`).
13. Monitoring (`typical`): communication to the datalogger, shown as a dashed line.

Items not sourced and therefore `not_found` or `typical` without value: cable sections and lengths (calculation, out of scope), the earth-leakage setting in mA beyond the cited figures, and the battery DC current rating.

## 3. Naming, tags and labels

- Each device carries a tag that links to its schedule and datasheet. Project-specific format; `typical` examples: `QF-DC-01` for the DC isolator, `QF-AC-01` for the AC breaker, `SPD-DC-01`, `INV-01`, `MP-01` for the meter.
- String labels: `S<inverter>.<string>` (for example `S1.3`) and cable tags per run (`typical`). Use one tag per cable.
- Label each device with its rating (V, A, kA, curve or type). Label each string with its module count and, if the design needs it, Voc at minimum temperature.
- ANSI / IEEE function numbers identify protective functions (for example 27, 59, 81O, 81U, 32R, 67). The project legend controls their meaning (`oeb_der_protection`, `unverified`).

## 4. DC and AC presentation

| Convention | Status | Source |
|---|---|---|
| Source (PV array) at the top, loads and board at the bottom | `typical` | Same as the PV grid-tie scheme already in `../sld_mld/schemes/pv_grid_tie_lv.json` |
| DC side drawn left to right, AC side drawn top to bottom | `typical` | Generic practice |
| Show DC isolation and AC isolation as separate devices on each side | `unverified` | `ei_pv_safety` (DC and AC disconnection both required) |
| Show the inverter as one block with its DC input, AC output and RCMU | `typical` | Manufacturer manuals describe RCMU as inside the inverter (`sma_rcmu`) |
| Show the islanding switch (4P) and the IMD only where the design is islandable | `unverified` | `ei_prosumer` |
| Show the earthing scheme on the same sheet as the AC board | `typical` | `ei_prosumer` (earthing tables by island mode) |

Symbols per IEC 60617: the public IEC 60617 page lists no identifiers for the PV items (`iec60617_db`, `not_found`). PV symbol identifiers are `not_found`; the harness uses the project legend.

## 5. What is not covered

- The IEC 62548-1 design rules (the publication page was found, the text was not fetched; `iec62548_1_webstore`, content `not_found`).
- The AEA 90364-7-712 text (Argentine PV installation chapter). It was not reached in this run; its values are `not_found`.
- The IEC 60364-7-712 full text. Only the publisher preview (ed.3.0, 2025-10) was read: scope and clause index, no values.
- IEC 61082-1 and IRAM title-block rules (see the earlier SLD research).

## 6. Sources

- `iec60364_7_712_preview`: IEC 60364-7-712 ed.3.0 publisher preview, https://assets.vde-verlag.de/iec-normen/preview-pdf/info_iec60364-7-712%7Bed3.0%7Db.pdf
- `ei_pv_safety`: https://www.electrical-installation.org/enwiki/PV_System:_how_to_ensure_safety_during_normal_operation
- `ei_prosumer`: https://www.electrical-installation.org/enwiki/Specific_protection_of_prosumer_electrical_installations
- `oeb_der_protection`: https://www.oeb.ca/sites/default/files/DER-wg3-Sample%20Protection%20Philosophy.pdf
- `sma_rcmu`: https://manuals.sma.de/SMAStorageXLPackage/en-US/17058314251.html
