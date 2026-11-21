# Typical single-line schemes (SLD)

Nine typical schemes. Each one is a JSON record in `schemes/<id>.json` with an ordered `chain` of devices that exist in `devices/`. Topology is `typical` for all schemes (generic arrangement, not a project design). Sources cited per scheme are for the individual device facts, not for the layout.

Symbols: no IEC 60617 identifiers were found on the public page (`iec60617_db`), so symbol references are `not_found` in every device record.

| # | Scheme (JSON id) | Voltage | Purpose |
|---|---|---|---|
| 1 | MV utility intake to LV board (`mv_utility_intake`) | MV | Metering, MV cell, transformer, LV board |
| 2 | MV ring-main cell arrangement (`mv_ring_main_cell`) | MV | Cable cells C, C, F with transformer |
| 3 | MV/LV transformer substation (`mv_lv_transformer_substation`) | MV/LV | MV protection, transformer, LV incomer |
| 4 | Main LV board with surge protection (`tgbt_main_board`) | LV | Incomer, SPD type 2, outgoing MCCB/MCB, RCD |
| 5 | Sectional LV board (`sectional_board`) | LV | MCB, RCD group, final circuits, RCBO |
| 6 | Standby generator with ATS (`genset_ats_standby`) | LV | Utility and generator to main board |
| 7 | UPS with bypass for critical loads (`ups_critical`) | LV | UPS input, UPS, critical output |
| 8 | PV grid-tie inverter on LV board (`pv_grid_tie_lv`) | LV | DC strings, gPV, SPD, DC and AC switches, inverter |
| 9 | LV capacitor bank (`capacitor_bank_lv`) | LV | Isolation, fuse, contactor, capacitor bank |

## 1. MV utility intake to LV board

Chain: utility metering (`utility_metering_mv`) → MV incoming cell C (`mv_load_break_switch_c`) → MV protection cell CB with relay (`mv_circuit_breaker_relay_module`) → MV/LV transformer (`transformer_mv_lv`) → main LV board (`switchboard_tgbt`).

- The CB cell carries overcurrent 50/51 and earth-fault 50N/51N relays with CTs (typical set).
- Show CT and VT ratios at the metering point. Ratios not found.
- The transformer data (kVA, vector group, impedance) are project data.

## 2. MV ring-main cell arrangement

Chain: incoming cable cell C → outgoing cable cell C → transformer cell F (`mv_switch_fuse_f`) with downstream earthing switch (`mv_earthing_switch`) → transformer (`transformer_mv_lv`).

- F module: 200 A switch-fuse, fuse-links max 125 A at 12 kV or 63 A at 24 kV, downstream earthing switch 5 kA 1 s (`abb_safering_cat`, unverified).
- Show interlocks between the disconnector and the earthing switch.

## 3. MV/LV transformer substation

Chain: MV breaker with relay (`mv_circuit_breaker_relay_module`) → transformer (`transformer_mv_lv`) → LV incomer (`acb` or `mccb`) → main LV board (`switchboard_tgbt`).

- ACB above 1600 A, MCCB otherwise (`viox_breaker_sizes`, unverified).
- Oil transformer: add Buchholz 63 and differential 87 for critical installations (typical).

## 4. Main LV board with surge protection

Chain: incomer MCCB (`mccb`) → SPD type 2 on busbar (`spd_type2`) → outgoing MCCB to sub-board (`mccb`) → outgoing MCB for final circuit (`mcb`, curve C default) → RCCB 30 mA for sockets and lighting (`rccb`).

- Type 1 at service entrance only if a lightning protection system exists (pending review).
- Label the busbar with voltage and current rating (`viox_sld`).

## 5. Sectional LV board

Chain: feeder MCB (`mcb`) → RCCB for a group of MCBs (`rccb`) → final circuit MCB (`mcb`) → RCBO for a circuit needing its own RCD (`rcbo`).

- One RCCB per group of circuits: economical. RCBO for a single circuit with a separate RCD need (typical).

## 6. Standby generator with ATS

Chain: standby generator (`generator_set`) → ATS (`ats`) → main LV board (`switchboard_tgbt`).

- Show utility and generator inputs to the ATS, each with its breaker.
- ATS transition mode (open, closed, delayed) is chosen per load (unverified, Kohler brochure).

## 7. UPS with bypass for critical loads

Chain: UPS input breaker (`mccb`) → UPS (`ups`) → critical output MCB (`mcb`).

- Show the static bypass path (typical; not sourced in this run).

## 8. PV grid-tie inverter on LV board

Chain: string fuses gPV (`fuse_gpv`) → DC SPD type 2 (`spd_type2`) → DC switch-disconnector (`switch_disconnector`) → inverter (`pv_inverter_grid_tie`) → AC switch-disconnector (`switch_disconnector`) → LV board (`switchboard_tgbt`).

- The combiner, DC switch, DC SPD and AC disconnect ratings are in `repo_pv_inverters` (internal research, unverified).
- The inverter rating is project-specific.

## 9. LV capacitor bank

Chain: isolation switch-disconnector (`switch_disconnector`) → fuse gG (`fuse_gg`) → contactor (`contactor`) → capacitor bank (`capacitor_bank`).

- Contactor switches the bank; fuse gives overcurrent back-up (typical).
- Harmonic-rich loads without detuning: resonance risk (typical). Detuning is not covered by the sources.

## Drawing conventions shared by all schemes

1. Source at top, loads at bottom, read upstream to downstream (`viox_sld`, unverified).
2. Each device carries a tag (for example QF-101) and rating (A, kA, curve) (`viox_sld`).
3. Each feeder is labelled with conductor count, size and material where notated.

## Sources

- `viox_sld`: https://viox.com/how-to-read-a-single-line-diagram/
- `abb_safering_cat`: https://library.e.abb.com/public/bb38f74c9b404b4b89745cde2a4b0dba/1VDD006104_Catalogue_SR-SP_12-24kV_EN_07-2022.pdf
- `ei_spd`: https://www.electrical-installation.org/enwiki/The_Surge_Protection_Device_(SPD)
- `ei_rcd`: https://www.electrical-installation.org/enwiki/Protection_of_circuits_by_RCD
- `kohler_ats`: https://resources.kohler.com/power/kohler/industrial/pdf/ATS_Brochure.pdf
- `viox_fuse`: https://viox.com/iec-60269-low-voltage-fuse-selection-guide-gg-am-nh/
- `repo_pv_inverters`: harness/docs/pv/inverters/central_inverters_and_accessories.md (internal)
- `iec60617_db`: https://std.iec.ch/iec60617
