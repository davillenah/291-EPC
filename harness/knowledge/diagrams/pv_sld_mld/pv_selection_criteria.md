# PV selection criteria: decision tables, conflicts, not found

Decision logic for the PV SLD devices. The machine-readable form is `pv_decision_rules.json` (17 rules, 5 conflicts). Status vocabulary in `pv_sld_mld_conventions.md`. Facts only, sourced on 2026-11-20. Nothing is verified.

## 1. Decision table (readable form)

Read the inputs in order; a `pending review` rule is a value a person must confirm.

| Step | Question | If yes | If no | Rule | Status |
|---|---|---|---|---|---|
| 1 | Can reverse current from parallel strings reach a faulted string? | Protect each string (fuse or breaker) with a load-break isolator in series | No reverse-current device needed (one string or two equal strings) | r01, r04 | unverified |
| 2 | Rating of the string device | Above 1.5 x Isc_module (wiki) or 1.25 x 1.25 x Isc (NEC via IAEI); both kept | - | r02 | pending review (c01) |
| 3 | Is U_OC MAX above 1000 V? | DC isolator and breakers with multiple poles in series, rated for U_OC MAX | Standard DC isolator rated for U_OC MAX | r03 | unverified |
| 4 | Rooftop without external LPS? | DC SPD type 2 at combiner or inverter DC entry | - | r05 | unverified |
| 5 | External LPS present? | DC SPD type 1+2 at relevant entry points | - | r06 | unverified |
| 6 | AC output current known? | AC overcurrent at least 125 % of rated output current, not above the manual maximum | - | r08 | pending review |
| 7 | Transformerless inverter? | Type B external RCD where required (Kostal, citing EN 62109-1); earthing check: no DC pole earthed | Type A or other per inverter manual and local rules | r09, r17 | pending review / unverified |
| 8 | Local rules require an RCD? | Type B, 500 mA or more, one per inverter (SMA) | - | r10 | unverified (c03) |
| 9 | Utility interface protection required? | Relays 27, 59, 81O, 81U, 32R, 67 as utility lists; settings from utility | - | r11 | unverified |
| 10 | Islandable installation? | 4-pole islanding switch (SDFI); IMD on transformer side for long island operation | Grid-tied only | r12 | unverified |
| 11 | Battery present? | Overcurrent device between battery and inverter (DC-coupled); local sources board for AC-coupled | - | r13, r16 | unverified |
| 12 | Rapid shutdown required by a rule? | DC conductors below 30 V within 30 s; array disconnect within 15 s (SMA, US code) | Not needed by IEC text found (not_found) | r14 | pending review |
| 13 | Point of connection | Overcurrent device at the connection to the building installation (not off-grid) | - | r15 | unverified |

## 2. Technology choice (readable summary)

| Need | Choose | Note | Status |
|---|---|---|---|
| Few strings, one inverter, rooftop | String inverter with optional combiner | Scheme `pv_string_inverter_lv` | unverified |
| Utility-scale, MV collection | Central inverter in a station | Scheme `central_inverter_mv_station`; station data repo-only | typical |
| Module-level MPPT, no DC string wiring | Microinverter | Scheme `microinverter_lv`; repo example 290 VA | typical |
| Module-level MPPT, string inverter kept | Power optimizers | Scheme `optimizer_string_lv` | typical |
| Storage on the DC bus | Hybrid DC-coupled | Battery breaker required | typical |
| Storage on the AC bus, existing PV kept | Hybrid AC-coupled | Local sources board, single connection point | typical |
| No grid | Off-grid / islanded | SDFI, IMD; earthing check in island mode | unverified |
| Export limit | Self-consumption, zero injection | 32R where required; control method not_found | typical |

## 3. Conflicts between sources

These are kept open. A person (or the project's norm) decides. None is resolved in this research.

| Id | Topic | Sources | What differs | Status |
|---|---|---|---|---|
| c01 | String overcurrent multiplier | `ei_pv_safety`, `iaei_oc` | Wiki: above 1.5 x Isc_module. NEC via IAEI: 1.25 x 1.25 x Isc, and 2 x 1.25 x 1.25 x Isc for two-string fuse sizing. Not reconciled | pending review |
| c02 | Voc temperature correction | `sma_voc_article`, `ei_pv_safety` | SMA gives the coefficient method only. A reader comment on the same page cites a 1.14 factor for -10 C and says the article subtracts in the wrong order. Use the method; the comment's value is not used | pending review |
| c03 | RCD type for transformerless inverters | `sma_rcmu`, `fronius_symo_manual`, `kostal_piko_rcd` | SMA: type B >= 500 mA only where local rules require. Fronius: type A generally sufficient, RCD for frequency converters, >= 100 mA. Kostal, citing EN 62109-1: type B for unisolated inverters. Not reconciled | pending review |
| c04 | MV station container envelope | `repo_inverters_central` | Repo gives 12192 x 2438 x 2896 in one table and 12192 x 2896 x 2438 mm in another. Internal inconsistency; verify on datasheet | unverified |
| c05 | Rapid shutdown scope | `iec60364_7_712_preview`, `sma_stp_interfaces` | IEC preview lists no rapid-shutdown topic. The 30 V / 30 s limit is SMA's UL 1741 PVRSE description (US code). Scope differs | pending review |

Other differences noted but not conflicts (different products or sizes):

- String fuses: Fronius Eco 15 A (max 20 A per terminal) and Phoenix repo combiner 15 to 32 A are different products.
- DC switch: Huawei L1 family recommends a DC breaker of at least 600 V / 20 A; repo NHP NL432PV is 1500 V / 32 A (repo example, different product).
- AC breaker: Huawei single-phase 16 to 32 A; Fronius three-phase fuse 10 to 25 A (different ranges).

## 4. Not found (never guessed)

| Item | Where it was looked for | Status |
|---|---|---|
| Uc, Up and In numerical selection rules for PV SPD | `viox_spd`, `phoenix_combiners`, `iec60364_7_712_preview` | not_found |
| gPV fuse DC voltage and current ratings (generic) | fetched vendor pages | not_found (`fuse_gpv` record) |
| IEC 62548-1 design rules | publisher page only | not_found (text not fetched) |
| AEA 90364-7-712 text | search results only | not_found |
| NEC 690.12 rapid-shutdown text | short citation only | not_found (text) |
| IEC 60364-7-712 rapid shutdown | ed.3.0 preview topic list | not_found |
| Interface relay trip thresholds (27, 59, 81O, 81U, 32R, 67) | `oeb_der_protection`, `sma_stp_interfaces` | not_found |
| Zero-injection control method and export-limit device | `ei_self_consumption` and others | not_found |
| MV transformer kV ratings (station) | repo | not_found |
| Ride-through time (SMA) | `sma_stp_interfaces` | not_found |
| IMD alarm threshold (external) | `ei_prosumer` | not_found |
| Diode ratings (reverse-polarity) | `sma_stp_protective` | not_found |
| DC breaker breaking capacity | fetched vendor pages | not_found |
| Meter bidirectional capability | repo rows | not_found |
| Module Voc temperature coefficient for a real design | not a sourced value; from the module datasheet | not_found |

## 5. Scope limits

- No norm value is verified. Every norm-quoted number is `pending review` and needs a person.
- Sizing (cable, voltage drop, short-circuit) is outside this research; it belongs to the calculation engines.
- Device ratings for real projects come from the chosen product datasheet, not from this research.

## 6. Sources

- `ei_pv_safety`: https://www.electrical-installation.org/enwiki/PV_System:_how_to_ensure_safety_during_normal_operation
- `ei_prosumer`: https://www.electrical-installation.org/enwiki/Specific_protection_of_prosumer_electrical_installations
- `iaei_oc`: https://iaeimagazine.org/columns/photovoltaic/photovoltaic-power-system-overcurrent-protection-why-how-and-where/
- `iaei_ac`: https://iaeimagazine.org/columns/photovoltaic/conductors-currents-and-circuit-protection-the-ac-side/
- `sma_rcmu`: https://manuals.sma.de/SMAStorageXLPackage/en-US/17058314251.html
- `sma_stp_interfaces`: https://manuals.sma.de/STPxx-US-41/en-US/391139595.html
- `sma_stp_protective`: https://manuals.sma.de/STPxxUS50/en-US/12078896395.html
- `sma_voc_article`: https://sma-sunny.com/us/?p=116684
- `fronius_symo_manual`: https://manuals.fronius.com/html/4204260172/en.html
- `huawei_l1_cables`: https://support.huawei.com/enterprise/en/doc/EDOC1100136173/d7e21771/preparing-cables
- `kostal_piko_rcd`: https://www.kostal-solar-electric.com/fileadmin/downloadcenter/kse/1210_HE-RCD-RCM.pdf
- `oeb_der_protection`: https://www.oeb.ca/sites/default/files/DER-wg3-Sample%20Protection%20Philosophy.pdf
- `viox_spd`: https://viox.com/how-to-choose-the-right-spd-for-your-solar-power-system/
- `phoenix_combiners`: https://www.phoenixcontact.com/en-sk/products/surge-protection/string-combiner-boxes-for-photovoltaic-systems
- `iec60364_7_712_preview`: https://assets.vde-verlag.de/iec-normen/preview-pdf/info_iec60364-7-712%7Bed3.0%7Db.pdf
- `repo_inverters_central`: repo://harness/docs/pv/inverters/central_inverters_and_accessories.md
