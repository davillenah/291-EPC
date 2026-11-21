# MV switchgear and protection relays (ANSI numbers)

Research for the harness SLD/MLD generator. Facts only, sourced on 2026-11-20. Status vocabulary in `sld_mld_conventions.md`. Each device has a JSON record in `devices/<id>.json`.

## 1. Switchgear family used as reference

The fetched MV data comes from ABB SafeRing and SafePlus (SF6 gas-insulated ring-main and secondary switchgear, 12-24 kV). Product modules are the reference set. Values come from the 2022 catalogue (`abb_safering_cat`) and the product document (`abb_safering_doc`). Where the two disagree, both values are recorded.

| Module | Function | JSON id | Status |
|---|---|---|---|
| C | Cable switch (load-break) | `mv_load_break_switch_c` | unverified |
| V | Vacuum circuit breaker | `mv_vacuum_circuit_breaker` | unverified |
| F | Switch-fuse-disconnector | `mv_switch_fuse_f` | unverified |
| CB | Circuit-breaker module with relay | `mv_circuit_breaker_relay_module` | unverified |
| (earthing) | Earthing switch | `mv_earthing_switch` | unverified (F-module value); generic making capacity not_found |

Other SafeRing and SafePlus functions named in the sources (not modelled as devices yet): D (direct cable connection), M (metering, air-insulated), Sl and Sv (busbar sectionaliser), De and Be (earthing only).

## 2. Ratings by module

### 2.1 Common ratings (ABB SafeRing / SafePlus, unverified)

| Parameter | Value | Note |
|---|---|---|
| Rated voltage Ur | 12 / 15 / 17.5 / 24 kV | Some functions only at 12 / 17.5 / 24 kV (`abb_safering_doc`) |
| Power-frequency withstand | 28 kV (12 kV), 38 kV (17.5 kV), 50 kV (24 kV) | catalogue (`abb_safering_cat`) |
| Impulse withstand | 95 kV (12 kV), 95 kV (17.5 kV), 125 kV (24 kV) | catalogue |
| Insulation | SF6 in sealed stainless steel tank; leakage below 0.1 % per year | `abb_safering_doc` |
| IP | Tank IP67; operating mechanisms IP2X | `abb_safering_doc` |

### 2.2 C module (cable switch)

| Parameter | Value (catalogue) | Value (product doc) | Status |
|---|---|---|---|
| Rated normal current | 630 A | 630 A | unverified |
| Making capacity | 62.5 kA (12 kV), 52.5 kA (17.5/24 kV) | SafePlus C: 62.5 kA (12 kV), 52.5 kA (15 kV), 50 kA (17.5/24 kV); SafeRing C: 52.5 kA (12/15 kV), 40 kA (17.5/24 kV) | unverified; **conflict** at 17.5/24 kV (52.5 vs 50 vs 40 kA) |
| Short-time withstand 3 s | 21 kA (12-24 kV) | SafePlus C 21 kA (3 s); SafePlus C 25 kA (1 s, 12 kV only) | unverified |

### 2.3 V module (vacuum circuit breaker)

| Parameter | Value | Status |
|---|---|---|
| Rated normal current | 630 A, or 200 A depending on bushing | unverified |
| Breaking current | 21 kA (12 kV), 16 kA (17.5 and 24 kV) | unverified (catalogue); SafeRing V quoted as 16 kA (doc) |
| Making capacity | 52.5 kA (12 kV), 40 kA (17.5 and 24 kV) | unverified |
| Short-time withstand 3 s | 21 kA (12 kV), 16 kA (17.5 and 24 kV) | unverified |
| V20/V25 variant | 25 kA (12 kV), 20 kA (17.5 and 24 kV) breaking; 25 kA (12 kV) 3 s withstand | unverified |

### 2.4 F module (switch-fuse-disconnector)

| Parameter | Value | Status |
|---|---|---|
| Rated normal current | 200 A (switch-fuse-disconnector) | unverified |
| Fuse-links | max 125 A CEF at 12 kV; max 63 A CEF at 24 kV | unverified (fuse tables are in a separate chapter, not fetched) |
| Off-load transformer breaking | 20 A | unverified |
| Downstream earthing switch | 5 kA, 1 s (all voltages) | unverified |
| Making capacity | limited by the HV fuse-links | unverified (doc) |

Use: MV transformer protected by fuse-links only. Not for fault breaking with relay coordination (use the V module).

### 2.5 CB module (circuit breaker with relay)

| Parameter | Value | Status |
|---|---|---|
| Rated normal current | 630 A or 1250 A (1250 A variant cannot use combisensors) | unverified |
| Breaking current | 25 kA (12 kV), 20 kA (17.5 and 24 kV) | unverified |
| Making capacity | 62.5 kA (12 kV), 50 kA (17.5 and 24 kV) | unverified |
| Short-time withstand | 25 kA (12 kV) and 20 kA (17.5 and 24 kV), 2 s at 630 A; 3 s at 1250 A | unverified |
| Mechanical operations | 30,000 close/open cycles | unverified |
| Operating sequence | O - 0.3 s - CO - 15 s - CO | unverified |

The sources state the CB module needs a protection relay.

### 2.6 Earthing switch

- Earthing switch on the cable or transformer side, interlocked with the disconnector (C, V, Sl, Sv modules have a disconnector with earthing switch; De and Be have earthing only). Source: `abb_safering_doc`, unverified.
- Making capacity of a generic earthing switch: not_found (the F-module downstream earthing switch is 5 kA, 1 s).
- Interlock rules and standard IEC 62271-102 are cited, not quoted.

### 2.7 IAC arc classification (as seen in an earlier repository research, not fetched here)

Not used in this research. The repository research on central PV stations lists IAC A FL 25 kA 1 s for a station switchgear. That is a different product and is recorded only as context.

## 3. Protection relays (ANSI/IEEE device numbers)

Source for the numbering: `control_ansi` (unverified), a third-party textbook list. Standard reference: ANSI/IEEE C37.2. Relay setting ranges were not found in any source; all setting ranges are `not_found`.

| Number | Function (as cited) | JSON id | Status |
|---|---|---|---|
| 27 | Undervoltage | `relay_ansi_27` | unverified |
| 49 | Thermal (machine or transformer) | `relay_ansi_49` | unverified |
| 50 | Instantaneous overcurrent | `relay_ansi_50_51` | unverified |
| 51 | Time overcurrent | `relay_ansi_50_51` | unverified |
| 50N / 51N | Earth overcurrent | `relay_ansi_50n_51n` | typical (the cited list gives 50G and 51G; 50N and 51N is the common naming) |
| 52 | AC power circuit breaker | (device `mv_vacuum_circuit_breaker`) | unverified |
| 59 | Overvoltage | `relay_ansi_59` | unverified |
| 63 | Pressure switch (cited); Buchholz use for oil transformers | `relay_ansi_63` | unverified (63 definition); typical (Buchholz use) |
| 81 | Frequency, over (81H) and under (81L) | `relay_ansi_81` | unverified |
| 86 | Lockout (auxiliary) relay | `relay_ansi_86` | unverified |
| 87 | Differential | `relay_ansi_87` | unverified |

Other numbers in the cited list, not modelled as devices: 21 (distance), 24 (V/Hz), 25 (synchronism check), 32 (directional power), 40 (loss of excitation), 46 (current unbalance), 47 (phase reversal), 63 (pressure), 67 (directional overcurrent), 27/59 are listed separately (no combined code). 94 is not in the cited list. 50N/51N and 94 are not listed as such in that source.

### 3.1 Typical MV protection set (typical)

| Application | Functions |
|---|---|
| MV feeder | 50/51, 50N/51N |
| Oil-immersed transformer | 50/51, 50N/51N, 63 (Buchholz), 87 for critical installations |
| Generator or islanding | 81, 27, 59, 87 (generator differential) |
| Critical installation with lockout | add 86 |

These sets are `typical` (no fetched source for the full set). Use with the relay manufacturer's manual.

## 4. Instrument transformers

| Device | Function | Ratio and class | Status |
|---|---|---|---|
| CT (TC) | Current for metering and protection | not found | not_found |
| VT (TT) | Voltage for metering and 27/59/81 relays | not found | not_found |

The symbol identifiers for TC and TT were not found on the public IEC 60617 page. Standards IEC 61869-2 and IEC 61869-3 are cited only.

## 5. MV design notes (typical)

- Choose the function that matches the load: C for cable switching, V for fault breaking, F for fuse-protected transformer, CB for relay-protected breaker feeders.
- Earthing switches must be interlocked with the disconnector (`typical`).
- Check the short-time withstand and making capacity against the calculated fault at the point. The fault calculation is outside this research.

## 6. Gaps

1. Transformer data (kVA, impedance, vector group) for a generic MV/LV transformer: not_found. The repository PV research mentions Dyn11, YNd11 and YNy0 as vector groups for station transformers (`repo_pv_inverters`, unverified).
2. Relay setting ranges and CT ratios: not_found.
3. Protection coordination between MV relays: not fetched (the wiki page on MV network protection returned an error). Only the function list is recorded.
4. Conflicts between catalogue and product document for the C module making capacity (section 2.2).

## 7. Sources

- `abb_safering_cat`: 1VDD006104 catalogue, https://library.e.abb.com/public/bb38f74c9b404b4b89745cde2a4b0dba/1VDD006104_Catalogue_SR-SP_12-24kV_EN_07-2022.pdf
- `abb_safering_doc`: SafeRing SafePlus 12-24 kV, https://library.e.abb.com/public/207cafdaa3d4bfc2482578070000fce2/12-24kV_SafeRing_SafePlus_EN.pdf
- `control_ansi`: ANSI/IEEE Function Number Codes, https://control.com/textbook/electric-power-measurement-and-control/ansiieee-function-number-codes/
- `iec60617_db`: IEC 60617 public page, https://std.iec.ch/iec60617
- `repo_pv_inverters`: EPC-291 repository, harness/docs/pv/inverters/central_inverters_and_accessories.md (internal)
