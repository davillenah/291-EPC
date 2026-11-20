# PV inverters: string, hybrid, micro and optimizer-inverter families (research notes)

Status of all values: `unverified` = taken from a manufacturer datasheet or manual (URL in Sources); `typical` = generic placement or industry value, not sourced; `not_found` = not stated in the sources read. No value is `verified` (only a person can set that). No norm value was approved or changed.

Scope: 10 representative models for 2D/3D modelling. Data is for the owner's modelling pipeline (JSON files under `harness/src/engines/calculation/pv/src/epc_pv/data/pv_inverters/inverters/`). No PDF was stored; facts are short citations with section names.

Access note: all fetches ran on 2026-11-20. Several datasheets were read through third-party mirror copies (noted below) because the manufacturer URL redirected or failed. Where a mirror was used, the value should be confirmed against the manufacturer's current file before a release.

## Comparison table

| Model (id) | Family | Phases / AC | Rated AC | MPPT / PV inputs | Max Vdc | Max I per MPPT | Eff. max | IP | Cooling | W x H x D (mm) | Weight (kg) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SMA Sunny Boy 3.0 family (`sma.sb3-0-1av-41`) | Single-phase string | 1ph, 220/230/240 V, 50/60 Hz | 3.0 kW (SB3.0) to 6.0 kW | 2 (A/B, 2 strings each) | 600 V | 15 A usable, 20 A Isc | 97.0 % | IP65 | Convection | 435 x 470 x 176 | 17.5 |
| Fronius Primo 3.0-1 (`fronius.primo-3-0-1`) | Single-phase string | 1ph, 220/230 V (180-270) | 3.0 kW | 2 | 1000 V | 12 A | 98 % | IP65 | Regulated fans | 432.5 x 642.5 x 205.5 | 19.25 |
| SMA Sunny Tripower 25000TL-30 (`sma.stp25000tl-30`) | Three-phase string C&I | 3ph/N/PE, 220/380, 230/400, 240/415 V (180-280) | 25 kW | 2 (3 strings each) | 1000 V | 33 A | 98.3 % | IP65 | Opticool (passive concept) | 661 x 682 x 264 | 61 |
| Fronius Symo Advanced 20.0-3-M (`fronius.symo-advanced-20-0-3-m`) | Three-phase string | 3~NPE, 400/230 or 380/220 V, 50/60 Hz | 20 kW | 2 | 1000 V | 33.0 or 27.0 (ambiguous) | 98.1 % (may be 98.0) | IP66 | Controlled air | 510 x 725 x 225 | 34.8 or 43.4 (ambiguous) |
| Huawei SUN2000-100KTL-H1 (`huawei.sun2000-100ktl-h1`) | Three-phase string utility/C&I | 3W+PE, **800 V AC** | 100 kW at 40 C | 6 | 1500 V | 22 A (Isc 33 A) | 99.0 % | IP65 | Natural convection, fanless | 1075 x 605 x 310 | 77 (with bracket) |
| Sungrow SG110CX (`sungrow.sg110cx`) | Three-phase string utility/C&I | 3P+N+PE, 400 V | 110 kVA at 45 C (100 kVA at 50 C) | 9 | 1100 V | 26 A (Isc 40 A) | 98.7 % | IP66 | Smart forced air | 1051 x 660 x 362.5 | 85 |
| Sungrow SH10RT (`sungrow.sh10rt`) | Hybrid (PV + battery) | 3/N/PE, 220/380, 230/400, 240/415 V, 50 Hz | 10 kW (backup output 220/230/240 V, peak 12 kW for 5 min on larger models) | 2 PV + battery 150-600 V | 1000 V | 12.5 A and 25 A | 98-98.4 % | IP65 | Natural convection | 460 x 540 x 170 | 27 (family value) |
| Victron MultiPlus-II 48/5000/70-50 230V (`victron.multiplus-ii-48-5000-70-50-230v`) | Battery inverter-charger (no PV input in this datasheet) | 1ph, 230 V +/-2 %, 50 Hz | 5000 VA cont. at 25 C; 3700 W at 40 C | n/a | n/a | n/a | 96 % | IP21 | Fan-assisted | 320 x 565 x 148 | 29 |
| Enphase IQ8PLUS-72-2-US (`enphase.iq8plus-72-2-us`) | Microinverter (one per module) | 240 V split-phase, 60 Hz (US) | 290 VA | 1 per module (MPPT 27-45 V) | 60 V | 12 A continuous, 25 A Isc | 97.7 % (CEC 97 %) | not_found | Natural convection, no fans | 175 x 212 x 30.2 | 1.08 |
| SolarEdge SE3K-SE10K (`solaredge.se10k`) | Three-phase inverter for power optimizers | 3/N/PE, 380/220 or 400/230 V WYE | 3-10 kW (model-dependent) | 2 pairs MC4 (optimizer string) | 900 V | 5-16.5 A (model-dependent) | 98 % | IP65 | Internal fan (source conflict) | 315 x 540 x 191 | 16.4 |

Notes for the comparison:
- The owner asked for Argentina/LatAm 220/380 V, 50 Hz. Sourced 220/380 or 230/400 V 50 Hz options: SMA Sunny Boy (1ph 220/230/240), SMA STP25000TL (3ph), Fronius Symo (3~NPE 400/230 or 380/220), SolarEdge SE10K (380/220 or 400/230 WYE), Sungrow SH10RT (3ph 220/380 and 230/400, 50 Hz), Victron MP-II 230 V 50 Hz. Sungrow SG110CX lists 400 V only. Huawei SUN2000-100KTL-H1 is 800 V AC and is not a 380 V model. Enphase IQ8PLUS-72-2-US is 240 V / 60 Hz (US); the IQ8AC/HC international variants are listed at 230 V 50 Hz (see the Enphase entry).
- Argentina's 50 Hz relevance is noted only where a source gives 50 Hz. Frequency for the SG110CX, STP25000TL and Huawei models was not stated in the text read; those cells stay `not_found` in the JSON.

## Per-model notes

### 1. SMA Sunny Boy 3.0 family (SB3.0-1AV-41 to SB6.0), `sma.sb3-0-1av-41`
- Dimensions W x H x D 435 x 470 x 176 mm, weight 17.5 kg, IP65, convection cooling. Source: SMA data sheet, "General data".
- 2 MPP inputs (A and B, 2 strings each). MPPT range differs by model: SB3.0 110-500 V, SB6.0 210-500 V. Max DC 600 V. 15 A usable per input, 20 A max Isc. Source: "Input (DC)".
- Rated AC 3000 W (SB3.0) to 6000 W (SB6.0); 220/230/240 V, 180-280 V range, 50/60 Hz. Max efficiency 97.0 %.
- DC connector SUNCLIX (count `not_found`). AC connector (type `not_found`). No on-device display or LED; the datasheet points to a phone/tablet/laptop app.
- Comms: RS485 and Ethernet listed as standard; WLAN "depending on availability".
- Protections listed: input-side disconnection point, ground fault monitoring, grid monitoring, reverse polarity, AFCI, all-pole residual-current monitoring, I-V/P-V diagnostics. Galvanic isolation is listed as not available (transformerless).
- Wall bracket hole spacing and screw sizes `not_found`.

### 2. Fronius Primo 3.0-1, `fronius.primo-3-0-1`
- Dimensions 432.5 x 642.5 x 205.5 mm, weight 19.25 kg (25.8 kg packed), IP65, regulated fans.
- 2 MPPT, 200-800 V (usable MPP 80-800 V), 1000 V max, 12 A per MPPT, 3000 W, 220/230 V single-phase (180-270 V). Max efficiency 98 %.
- Conflict: the DC table lists both 4x DC+ and 4x DC- and a "2 + 2" connection. Recorded as an open point.
- Screw terminals 2.5-16 mm2 for DC and AC (3-pin AC).
- Comms: RS485 (Modbus RTU SunSpec or meter), Ethernet LAN, WLAN, USB, 2x RS422, digital inputs/outputs.
- SnapINverter mounting: connection area is wall-mounted first, then the power stage set is attached. Hole spacing not stated.
- Protections: DC insulation measurement, DC disconnector, reverse polarity, overload handling.
- Source: Fronius technical data page (en-au). The fronius.com help-center page failed to load.

### 3. SMA Sunny Tripower 25000TL-30, `sma.stp25000tl-30`
- Dimensions 661 x 682 x 264 mm, weight 61 kg, IP65, Opticool (transformerless, passive concept). Fan `not_found`.
- 2 MPP inputs (A/B, 3 strings each). MPPT range 390-800 V for 25 kW (rated input 600 V). Max DC 1000 V, 33 A per input.
- AC 25 kW, 3/N/PE 220/380, 230/400, 240/415 V (180-280 V), 3 feed-in phases. Max efficiency 98.3 % (98.4 % for 15/20 kW models).
- DC SUNCLIX (count `not_found`). AC spring-cage terminal. Display optional. Ethernet "not explicitly stated"; Speedwire/Webconnect standard; RS485 optional.
- Optional Type II DC SPD. Grounding terminal not stated. Wall bracket spacing not stated.
- Catalog check: `inverter_catalog.json` entry `sma.stp25000tl-30` agrees on MPPT min 390 V, max 800 V, 2 MPPT, 3 strings per MPPT, 33 A per input, and max efficiency 98.3 %. Its `isc_max_input_a` is null, which matches "not found" here. Its `ac_max_current_a` 36.2 A is not in the text read. The catalog cites file DES1742; this entry uses DEN1622 (same product family, see Sources).

### 4. Fronius Symo Advanced 20.0-3-M, `fronius.symo-advanced-20-0-3-m`
- Dimensions 510 x 725 x 225 mm, IP66, controlled air cooling (fan count `not_found`).
- Weight: the source lists 34.8 kg or 43.4 kg for the table; the value for 20.0-3-M is not assigned. Both values are recorded as ambiguous.
- 2 MPPT, 200-800 V, max 1000 V. Current per MPPT 33.0 A or 27.0 A (column layout ambiguous). 20 kW, 3~NPE 400/230 V or 380/220 V (+20 %/-30 %), 50/60 Hz.
- Efficiency 98.1 % (98.0 % may apply to another model).
- DC screw terminals 6x DC+ and 6x DC-. AC 5-pole screw terminals 2.5-16 mm2.
- Comms: RS485 (Modbus RTU, SunSpec, meter), Ethernet, WLAN.
- Certifications include OVE/OENORM E 8001-4-712, VDE AR N 4105, IEC 62109-1/-2, IEC 62116, IEC 61727, AS 4777-2/-3, CEI 0-16/0-21, NRS 097.
- Source is a Danish-language PDF (Fronius file SE_DS_Fronius_Symo_DA). Field labels were read as numeric values; confirm the column mapping against the Spanish or English datasheet before use.

### 5. Huawei SUN2000-100KTL-H1, `huawei.sun2000-100ktl-h1`
- Dimensions 1075 x 605 x 310 mm, weight 77 kg including mounting bracket, IP65, fanless natural convection.
- 6 MPPT, 600-1500 V range, 1500 V max input, 22 A per MPPT, 33 A Isc per MPPT. Amphenol UTX DC connectors.
- Rated AC 100 kW at 40 C. AC 800 V, 3W+PE. **Not a 380/220 V grid model.** Kept as the family representative of 100 kW string inverters; the 380 V model needs its own datasheet (not found in this session).
- Max efficiency 99.0 %. Cable gland plus AC screw terminal. LED indicators, Bluetooth + app.
- Comms: RS485 and PLC listed; Ethernet and WLAN `not_found`.
- Protections: input-side and DC-side disconnect devices, reverse polarity, AC overcurrent, string monitoring, insulation and residual-current monitoring, island detection, Type II DC and AC surge protection.

### 6. Sungrow SG110CX, `sungrow.sg110cx`
- Dimensions 1051 x 660 x 362.5 mm, weight 85 kg, IP66, smart forced air cooling (fan count `not_found`).
- 9 MPPT, 200-1000 V full range (550-850 V nominal power range), 1100 V max. Per MPPT 26 A and 40 A Isc (the "26 A * 9" layout was read as per-MPPT). MC4 connectors up to 6 mm2 (count `not_found`).
- Rated 110 kVA at 45 C, 100 kVA at 50 C (the source gives kVA only). 400 V 3P+N+PE. Max efficiency 98.7 %.
- AC OT terminal up to 240 mm2. LED, Bluetooth + app. RS485; Ethernet and WLAN optional.
- Certifications include IEC 62109, IEC 61727, VDE-AR-N 4110/4120, EN 50438, AS/NZS 4777.2, CEI 0-21.
- Source is a Shopify-hosted copy of the Sungrow datasheet (V14). The official Sungrow URL redirected to a white-paper page.

### 7. Sungrow SH10RT (hybrid), `sungrow.sh10rt`
- Dimensions 460 x 540 x 170 mm, weight 27 kg, IP65, natural convection. These are family values for SH5.0RT to SH10RT.
- 2 PV MPPT (SH10RT): 12.5 A and 25 A per input (37.5 A total). PV range 200-950 V, max PV 1000 V.
- Battery input 150-600 V, 30 A max, Evo2 compatible.
- Rated AC 10 kW, 3/N/PE 220/380, 230/400, 240/415 V, 50 Hz. Backup output 220/230/240 V, 50/60 Hz, switch time under 20 ms, peak up to 12 kW for 5 min on larger models.
- Efficiency 98-98.4 % depending on model. MC4 for PV; plug-and-play AC connector; LED.
- Comms: RS485, WLAN, Ethernet, CAN; 4 digital inputs and 1 digital output. Bluetooth `not_found`.
- Source is a third-party brochure copy (sparkydirect). The official Sungrow fact sheet URL redirected.

### 8. Victron MultiPlus-II 48/5000/70-50 230V, `victron.multiplus-ii-48-5000-70-50-230v`
- This is a battery-side inverter-charger, not a PV string inverter. The datasheet lists no PV input.
- Dimensions 320 x 565 x 148 mm, weight 29 kg, IP21, fan-assisted cooling.
- DC: 48 V nominal, 38-66 V input range, charge current 70 A, M8 bolts.
- AC output 5000 VA continuous at 25 C; 4000 W at 25 C; 3700 W at 40 C. 230 V +/-2 %, 50 Hz (adjustable to 60 Hz). AC input 187-265 V, 45-65 Hz, max 50 A. Max efficiency 96 %.
- AC screw terminals up to 13 mm2 (6 AWG). GX model: 2x16 character display, VE.Direct, Ethernet. VE.Bus on both models. Bluetooth via optional dongle. WLAN `not_found`.
- Wall mounting holes and grounding `not_found`.

### 9. Enphase IQ8PLUS-72-2-US, `enphase.iq8plus-72-2-us`
- Dimensions (H x W x D) 212 x 175 x 30.2 mm, weight 1.08 kg, natural convection, no fans.
- 240 V split-phase (L-L 180 deg), 60 Hz nominal (47-68 Hz extended), range 211-264 V. Max continuous output 290 VA. Peak efficiency 97.7 %, CEC 97 %.
- DC: MC4 with a Q-DCC-2 adapter cable; MPPT 27-45 V; max DC 60 V; 12 A continuous; 25 A Isc. Array is ungrounded; AC side needs max 20 A branch protection.
- AC: Enphase AC connector (IQ cabling). Communication: power line (PLC). LED, WiFi and Bluetooth `not_found`.
- IP: the US datasheet gives "NEMA 6" and "Outdoor" but no IP number. The international IQ8AC/IQ8HC datasheet (230 V, 50 Hz) states IP67, but that is a different model and is **not** applied to the US model here.
- Certifications: CA Rule 21 (UL 1741-SA), UL 62109-1, IEEE 1547:2018 (UL 1741-SB), FCC Part 15 Class B, NEC 690.12 rapid shutdown.
- The US variant is not the 230 V / 50 Hz variant needed for Argentina; the IQ8AC-72-M-INT listed in the second source (230 V nominal, 50 Hz, 366 VA max apparent) is the closer match. Not created as a separate JSON in this round.

### 10. SolarEdge SE3K-SE10K (three-phase, power-optimizer system), `solaredge.se10k`
- Dimensions 315 x 540 x 191 mm (source lists HxWxD 540 x 315 x 191), weight 16.4 kg, IP65.
- Cooling conflict: the installation specification states an internal fan, the front page says "no external fan". Recorded as an open point.
- 2 pairs of MC4 DC inputs. Max DC 900 V. Current 5-16.5 A per model. Rated 3-10 kW (model-dependent).
- AC 3/N/PE 380/220 or 400/230 V WYE. Max efficiency 98 %. AC cable gland 15-21 mm. Ground-fault detection 700 kOhm.
- Comms: RS485 and Ethernet standard; WLAN, cellular and ZigBee optional. A mounting bracket is provided (spacing `not_found`).
- Designed to work with power optimizers. One variant (SE3K-RW010BNN4) connects to exactly 10 P404/P405/P485/P505 optimizers (footnote). The optimizer datasheet is not in this entry.
- Source is a shopify-hosted copy of the SE3K-SE10K datasheet. The EU version is cited, so Argentina-specific grid codes are not confirmed.

## Coverage gaps (not_found or not read)
- Enphase IQ8PLUS-72-2-US IP rating (not stated in the US datasheet).
- Huawei 380 V model (SUN2000-100KTL-M1 or similar) not fetched; the H1 is 800 V AC.
- Fronius Primo DC terminal count (source conflict 4+4 vs 2+2).
- Fronius Symo Advanced weight and per-MPPT current (ambiguous columns).
- Wall-mount hole spacing and screw sizes: not stated in any source read. Mounting holes are therefore not positioned in the 3D geometry; they are listed as `not_found` parts.
- Grounding terminal positions: not stated in most sources.
- Display and LED details: not stated for most models.
- Fan counts for Fronius Primo/Symo, Sungrow SG110CX and SolarEdge SE10K.
- Cable and DC connector counts for SUNCLIX (SMA) and MC4 (Sungrow SG110CX) not stated.
- Microinverter families not included in this set: APsystems DS3, Hoymiles HMS, and the Growatt and GoodWe ranges.

## Geometry conventions (for 2D/3D)
- `module_dimensions_mm` = [W, H, D] of the inverter envelope (here width, height, depth, not a PV module).
- Coordinate system in each JSON: x = width, y = height (0 = bottom), z = depth (0 = wall, D = front cover). Origin at bottom-left-wall corner.
- Enclosure element: status `unverified` (datasheet W x H x D). All other elements: status `typical`, generic placements (not sourced coordinates), described in each element note.

## Sources
Each JSON file carries its own `sources` block with the same ids.

- sma_sb30_ds: SMA Sunny Boy 3.0/3.6/4.0/5.0/6.0 data sheet (SB30-60-DS-en-61). https://files.sma.de/assets/278585.pdf (redirects to a CloudFront copy of the same document; accessed 2026-11-20).
- sma_stp25_ds: SMA Sunny Tripower 15000TL/20000TL/25000TL data sheet (STP 25000TL-30, DEN1622 v30). https://www.pv.de/media/stp25000tl-30-den1622-v30web.pdf (accessed 2026-11-20).
- fronius_primo_tech: Fronius Primo 3.0-1 technical data (en-au installers page). https://www.fronius.com/en-au/australia/solar-energy/installers-partners/technical-data/all-products/inverters/fronius-primo/fronius-primo-3-0-1 (accessed 2026-11-20).
- fronius_symo_adv_ds: Fronius Symo Advanced data sheet, Danish-language PDF (SE_DS_Fronius_Symo_DA). https://fronius.com/~/downloads/Solar%20Energy/Datasheets/SE_DS_Fronius_Symo_DA.pdf (accessed 2026-11-20).
- huawei_sun2000_h1_ds: SUN2000-100KTL-H1 data sheet (de). https://solar.huawei.com/~/media/Solar/attachment/pdf/de/datasheet/SUN2000-100KTL-H1.pdf (accessed 2026-11-20).
- sungrow_sg110cx_ds: SG110CX data sheet, V14 (mirror copy). https://cdn.shopify.com/s/files/1/0017/8847/7489/files/sungrow_SG110CX-Datasheet.pdf (accessed 2026-11-20). Official URL redirected: https://en.sungrowpower.com/upload/documentFile/DS_SG110CX%20Datasheet_V14_EN.pdf.pdf.
- sungrow_sh10rt_fs: SH5.0RT-SH10RT fact sheet (brochure mirror). https://www.sparkydirect.com.au/assets/brochures/SH10RT.pdf (accessed 2026-11-20). Official URL redirected: https://en.sungrowpower.com/upload/file/20210119/EN%20FS%20SH10RT%20Fact%20Sheet.pdf.pdf.
- victron_mp2_ds: MultiPlus-II inverter/charger datasheet, 3K/5K off-grid (EN AUS). https://www.victronenergy.com/upload/documents/Datasheet-MultiPlus-II-inverter-charger-3K-3K-GX-5K-5K-GX-off-grid-EN-AUS-.pdf (accessed 2026-11-20).
- enphase_iq8_us_ds: IQ8+ microinverter datasheet, US 240 V (mirror copy). https://krannich-solar.com/fileadmin/user_upload/US/Datasheets/Inverters/Enphase/iq8_plus_made_in_usa.pdf (accessed 2026-11-20).
- enphase_iq8_ac_ds: IQ8 series microinverter datasheet, IQ8AC/IQ8HC international (mirror copy). https://www.solarquotes.com.au/wp-content/uploads/2023/06/enphase-iq8-datasheet.pdf (accessed 2026-11-20). Used only for the comms note and mounting plate; its IP67 value does not apply to the US model.
- solaredge_se10k_ds: SE3K-SE10K three-phase inverter data sheet (mirror copy). https://cdn.shopify.com/s/files/1/0017/8847/7489/files/SE3K_-SE10K-datasheet.pdf (accessed 2026-11-20).

Search results were used only to locate these documents. Cited sections: "General data", "Input (DC)", "Output (AC)", "Efficiency", "Equipment", "Certificates and approvals", "Protective devices", "Mechanical data", "Installation specifications", "Standard compliance" as named in each source.

## Unverified items (summary)
1. All numeric values: datasheet-sourced, not yet checked against manufacturer originals (mirrors used for 5 sources).
2. Fronius Primo DC terminal count (4+4 vs 2+2 conflict).
3. Fronius Symo Advanced weight, per-MPPT current and efficiency (ambiguous columns in the Danish PDF).
4. SolarEdge SE10K fan (internal vs no external fan).
5. Sungrow SG110CX per-MPPT current reading ("26 A * 9").
6. Enphase IQ8PLUS-72-2-US IP rating and LED/WiFi/Bluetooth.
7. Huawei SUN2000-100KTL-H1 is 800 V AC; the 380 V model is not in this set.
8. Victron MultiPlus-II is a battery inverter-charger without PV input; not a string inverter in the strict sense.
9. Sungrow SH10RT dimensions and weight are family values for SH5.0RT to SH10RT.
10. Mounting-hole spacing, screw sizes and grounding terminal positions: not stated for any model.
11. Generic element placements (all elements except the enclosure) are `typical`, not sourced.

## Resumen en español

Se investigaron 10 modelos representativos de inversores fotovoltaicos: monofasicos de cadena (SMA Sunny Boy 3.0, Fronius Primo 3.0-1), trifasicos de cadena para C&I (SMA Sunny Tripower 25000TL-30, Fronius Symo Advanced 20.0-3-M, Huawei SUN2000-100KTL-H1, Sungrow SG110CX), hibridos y de bateria (Sungrow SH10RT, Victron MultiPlus-II 48/5000 230 V), microinversor (Enphase IQ8PLUS-72-2-US) e inversor con optimizadores (SolarEdge SE3K-SE10K).

Puntos clave:
- Para la red argentina de 220/380 V, 50 Hz, las opciones con dato de ficha son: SMA Sunny Boy (1F 220/230/240 V), SMA STP25000TL (3F 220/380 V), Fronius Symo (3~NPE 400/230 o 380/220 V), SolarEdge SE10K (380/220 o 400/230 V), Sungrow SH10RT (3F 220/380 y 230/400 V, 50 Hz) y Victron MP-II (230 V, 50 Hz).
- El Huawei SUN2000-100KTL-H1 tiene salida de 800 V CA y no sirve para red de 380 V; se mantiene solo como representante de familia.
- El Enphase IQ8PLUS-72-2-US es la variante US de 240 V / 60 Hz; la IP no figura en su ficha (la IP67 de las variantes IQ8AC/HC no se aplica a este modelo).
- Cuatro conflictos de ficha quedan abiertos: terminales DC del Fronius Primo, pesos y corriente por MPPT del Fronius Symo, ventilador del SolarEdge, y la lectura "26 A * 9" del SG110CX.
- Se encontraron 59 marcas `not_found` en el conjunto (partes y valores); los agujeros de fijacion y los terminales de puesta a tierra no estan en ninguna ficha leida.
- Las fichas de Sungrow, SolarEdge, Enphase y SMA (familia SB) se leyeron desde copias de terceros porque el enlace del fabricante redirigio; deben confirmarse antes de usarlas en un entregable.
- Ningun valor esta marcado como verificado; no se aprobo ni cambio ningun valor normativo.

Archivos JSON: `/home/user/291-EPC/harness/src/engines/calculation/pv/src/epc_pv/data/pv_inverters/inverters/<id>.json` (10 archivos, validados con jsonschema Draft 2020-12).
