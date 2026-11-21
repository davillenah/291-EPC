# PV DC-side protection: strings, fuse vs breaker, isolation, DC SPD, Voc

DC side of the PV array to the inverter input. Status vocabulary in `pv_sld_mld_conventions.md`. Facts only, sourced on 2026-11-20. Nothing is verified. Norm-quoted values are `pending review`.

## 1. When a string needs overcurrent protection

| Case | Requirement | Status | Source |
|---|---|---|---|
| One string | No reverse-current protection needed | unverified | `ei_pv_safety` |
| Two strings with equal module counts | No reverse-current protection needed | unverified | `ei_pv_safety` |
| More parallel strings that can feed a faulted string | Protection needed; compare the module reverse current (IRM) with the current from the other strings | unverified | `ei_pv_safety` |
| Inverter cannot backfeed into the DC wiring | Two strings may share one input without an overcurrent device | unverified | `iaei_oc` (NEC 690.9(A) and 690.8(D), short citation) |
| Current-limited source (inverter) | Overcurrent protection at the source for parallel strings | unverified | `iaei_oc` |

Rule: the reverse-current criterion decides whether string fuses or breakers are needed. Rule `r01` in `pv_decision_rules.json`.

## 2. Rating of the string overcurrent device (conflict c01)

Two bases are in the sources and they do not agree. Both are kept, status `pending review`.

| Basis | Multiplier | Source | Status |
|---|---|---|---|
| Wiki | Above 1.5 x Isc_module and below 2.4 x Isc_module (string); above 1.25 x Isc of the sub-array, below 2.4 x (sub-array) | `ei_pv_safety` | unverified |
| NEC citation via IAEI | 1.25 (irradiance above STC, about 1250 W/m2) x 1.25 (continuous-load factor, NEC 690.9(B)): 1.25 x 1.25 x Isc = 1.5625 Isc | `iaei_oc` | pending review |
| NEC citation via IAEI, two-string case | 2 x 1.25 x 1.25 x Isc for two-string fuse sizing (690.8(D), as stated in the article) | `iaei_oc` | pending review |

The wiki's 1.5 and the NEC 1.5625 are close; the two-string 2 x factor from IAEI is not reconciled with the wiki. Use the project's norm and a person to choose. The rating must also avoid nuisance tripping at temperature (wiki).

Module datasheet Isc is the input value for both bases. Values from a datasheet are not in this research.

## 3. Fuse or breaker

| Device | Points stated | Status | Source |
|---|---|---|---|
| Fuse (gPV) | Does not load-break; needs a load-break switch in the circuit to replace the cartridge | unverified | `ei_pv_safety` |
| Breaker | Can be finely adjusted; suits smaller sub-array cables | unverified | `ei_pv_safety` |
| Fuse and breaker of the same rating | Equivalent, interchangeable unless the code or device manual says otherwise | unverified | `iaei_oc` |
| DC PV overcurrent devices | Must be listed for PV use (NEC 690.9(D), short citation) | pending review | `iaei_oc` |
| Listed PV fuses | Limited to 50 C; non-PV fuses to 40 C (rooftop exposure can exceed) | pending review | `iaei_oc` |

Fuse data in sources (repo and vendors; no rating of the gPV fuse itself found in fetched pages):

| Item | Value | Status | Source |
|---|---|---|---|
| Fronius Eco string fuses | 6 x 15 A on DC+, 10 x 38 mm, 1000 V; max 20 A per terminal; 15 A MPP current per string | unverified | `fronius_symo_manual` |
| Phoenix Contact combiner 16 strings (repo) | Fuses 15/16/20/25/30/32 A, 10.3 x 85 mm | unverified | `repo_inverters_central` |
| gPV fuse (generic) | Rated DC voltage and current not found | not_found | `fuse_gpv` (existing device record) |

## 4. DC isolation

| Point | Status | Source |
|---|---|---|
| Fuses and DC breakers do not give protection against electric shock (no automatic disconnect) | unverified | `ei_pv_safety` |
| DC side enclosures provide double insulation | unverified | `ei_pv_safety` |
| DC breakers and switches must break at U_OC MAX; 1000 V systems need four poles in series (for that breaker type) | unverified | `ei_pv_safety` |
| Pollution degree 2 switchgear: enclosure at least IP5x | unverified | `ei_pv_safety` |
| DC switch in SMA inverter: DC load-break switch as the input-side disconnection point | unverified | `sma_stp_protective` |
| Fronius: DC main switch de-energises the power stage only; the connection area stays live | unverified | `fronius_symo_manual` |
| Repo DC switch-disconnector NHP NL432PV: 1500 V DC, 32 A, 4P, IP66 | unverified | `repo_inverters_central` |
| Huawei SUN2000-L1 recommended DC breaker: at least 600 V DC, 20 A | unverified | `huawei_l1_cables` |

Hence the DC isolator is drawn as a separate device, not a fuse (`pv_dc_switch_load_break`).

## 5. Voc at minimum temperature (maximum system voltage)

Method (SMA, `sma_voc_article`, unverified):

1. Temperature difference = 25 C (STC) minus the record-low ambient temperature.
2. Voc increase per module = temperature difference x temperature coefficient of Voc x module Voc.
3. Voc max per module = module Voc + that increase.
4. Maximum modules per string = inverter maximum DC input voltage / Voc max per module (round down).

The article's worked example: Voc 39.4 V, coefficient -0.30 %/C, record low -10 C, inverter maximum 600 V, gives 13 modules per string (the article's own result). This is an example in the source, not a value for this design.

Notes:

- The article cites NEC 690.7(A): the listed Voc coefficient may replace Table 690.7 (`sma_voc_article`).
- A reader comment on the same page cites a Table 690.7 correction factor of 1.14 for -10 C and says the article subtracts in the wrong order (the correction should increase Voc). Status `pending review`, not used as a value (conflict c02).
- Use the module datasheet coefficient and the site's record-low temperature (not in this research).

## 6. DC SPD

| Point | Status | Source |
|---|---|---|
| Install a DC SPD at the DC entry (combiner or inverter) | unverified | `viox_spd`, `sma_stp_protective` |
| Rooftop PV without external LPS: type 2 commonly evaluated | unverified | `viox_spd` |
| Where an external LPS exists: type 1 or 1+2 at relevant entry points | unverified | `viox_spd` |
| Commercial rooftop with combiners: "Type 2 at documented DC entry points; Type 1+2 where LPS/exposure requires" | unverified | `viox_spd` |
| Uc chosen for the cold-weather string Voc, at maximum normal PV voltage | unverified | `viox_spd` |
| Up coordinated so that transients stay below the withstand of the protected equipment; lead length adds to the voltage | unverified | `viox_spd` |
| In and Imax: read from the product declaration (no numeric values in the source) | not_found | `viox_spd` |
| Repo ABB OVR PV T2: 1000/1500 V, In 20/15 kA, Up 4/5 kV (IEC 61643-31) | unverified | `repo_inverters_central` |
| Phoenix Contact combiners: T1/T2 or T2 by model, no Uc/Up/In on the list page | unverified | `phoenix_combiners` |
| SMA: surge arresters type 1 and 2 slots on AC and DC sides, retrofittable | unverified | `sma_stp_interfaces` |
| IEC 60364-7-712 ed.3.0 surge sections 712.443 and 712.534, with IEC 61643-31 cited | unverified (clause index only) | `iec60364_7_712_preview` |

Uc, Up and In numerical selection rules are `not_found`: the sources give the principles, not a multiplier.

## 7. Reverse polarity, string diodes and monitoring

- SMA inverter: DC reverse-polarity protection by a short-circuit diode (`sma_stp_protective`, unverified). Diode ratings: `not_found`.
- String-failure detection in SMA is deactivated by default; it compares input currents with mean values and a settable tolerance (`sma_stp_interfaces`, unverified).
- AFCI (arc-fault detection): SMA lists type 1, UL 1699B Ed.1 (`sma_stp_interfaces`, unverified). IEC arc-fault requirements: `not_found`.

## 8. What is not covered

- Module Isc and Voc values, and the temperature coefficient: from the module datasheet.
- DC cable sizing and voltage drop: calculation workflow, out of scope.
- IEC 62548-1 design rules: `not_found` (text not fetched).

## 9. Sources

- `ei_pv_safety`: https://www.electrical-installation.org/enwiki/PV_System:_how_to_ensure_safety_during_normal_operation
- `iaei_oc`: https://iaeimagazine.org/columns/photovoltaic/photovoltaic-power-system-overcurrent-protection-why-how-and-where/
- `sma_voc_article`: https://sma-sunny.com/us/?p=116684
- `viox_spd`: https://viox.com/how-to-choose-the-right-spd-for-your-solar-power-system/
- `fronius_symo_manual`: https://manuals.fronius.com/html/4204260172/en.html
- `sma_stp_protective`: https://manuals.sma.de/STPxxUS50/en-US/12078896395.html
- `huawei_l1_cables`: https://support.huawei.com/enterprise/en/doc/EDOC1100136173/d7e21771/preparing-cables
- `iec62548_1_webstore`: https://webstore.iec.ch/publication/64171 (title only)
