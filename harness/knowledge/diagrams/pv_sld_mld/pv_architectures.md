# PV architectures for SLD/MLD

Eight architectures, one `schemes/*.json` each. Status vocabulary in `pv_sld_mld_conventions.md`. Facts only, sourced on 2026-11-20. Nothing is verified.

The existing `../sld_mld/schemes/pv_grid_tie_lv.json` is the short PV grid-tie chain; `schemes/pv_string_inverter_lv.json` extends it with meter, RCD and notes.

## 1. Summary

| Architecture | Scheme file | DC-side protection | AC connection | Battery | Level | Status |
|---|---|---|---|---|---|---|
| String inverter, LV | `pv_string_inverter_lv` | String fuses or breakers (combiner), DC SPD, DC isolator | Inverter AC isolator, AC overcurrent, board | No | LV | unverified |
| Central inverter, MV station | `central_inverter_mv_station` | DC combiners, DC isolator | Station transformer, MV switchgear, utility meter | No | MV | typical |
| Microinverter (AC module) | `microinverter_lv` | None on DC (module-level) | AC trunk, trunk isolator, overcurrent | No | LV | typical |
| Power optimizer + string inverter | `optimizer_string_lv` | Optimizer per module; DC isolator at inverter | Inverter AC isolator, overcurrent | No | LV | typical |
| Hybrid, DC-coupled battery | `hybrid_dc_coupled` | Strings fused, DC SPD, DC isolator, battery breaker | Hybrid inverter AC side, overcurrent | Yes, on DC bus | LV | typical |
| Hybrid, AC-coupled battery | `hybrid_ac_coupled` | PV inverter as string | Battery inverter and PV inverter on one AC bus | Yes, on AC bus | LV | typical |
| Off-grid / islanded | `off_grid_island` | DC isolator, battery breaker | 4-pole islanding switch, IMD | Yes | LV | unverified |
| Self-consumption, zero injection | `self_consumption_zero_injection` | String protection as string inverter | Bidirectional meter, reverse-power relay 32R | Optional | LV | typical |

## 2. String inverter (LV)

- Strings join at a combiner (optional for one or two strings) with string fuses and a DC SPD. The DC isolator sits at the inverter input.
- The inverter has a DC load-break switch as the input-side disconnection point and a short-circuit diode for reverse polarity (SMA, `sma_stp_protective`, unverified). Its DC overvoltage arrester is optional (type 1+2 or 2; `sma_stp_protective`).
- Combiner models in the Phoenix Contact list take 1 or 2 strings per model, with 1000 V DC MPP rating on every listed model (`phoenix_combiners`, unverified). Fuse ratings are not on the list page.
- The repo's 16-string combiner (Phoenix SCB SOL SC16ST) is rated 1500 V MPP with fuses 15/16/20/25/30/32 A and a T2 SPD (`repo_inverters_central`, unverified; repo research, not re-fetched).
- Maximum output overcurrent: SMA lists 60 A on the STP US model (`sma_stp_protective`, unverified). Fronius lists a maximum AC fuse of 25 A on its three-phase range (`fronius_symo_manual`, unverified). Huawei SUN2000-L1 recommends 16 to 32 A single-phase AC breakers (`huawei_l1_cables`, unverified). Model per datasheet.

## 3. Central inverter, MV station (MV)

- Repo station data (`repo_inverters_central`, unverified, preliminary for some models): SMA MVPS 5860/6120-S4-US, 40 ft container, 5866/6134 kVA, 34.5 kV, 60 Hz; MV switchgear of 3 panels (2 cable with load-break, 1 transformer with breaker), IAC A FL 25 kA 1 s.
- SMA MVPS 8000/9200: 6900 to 7920 kVA nominal, IAC A FL 20 kA 1 s.
- Sungrow MVS3200-US skid: 3200 kVA at 40 C, LV 0.8 kV, MV 12.47 to 34.5 kV, 60 Hz (repo, unverified).
- Not found: MV transformer kV ratings, named RMU model, internal positions in the container (`not_found`).
- Container envelope is given in the repo in two orders. See conflict c04 in `pv_decision_rules.json`.
- Interface relays on the MV breaker: 27, 59, 81, 32R, 67 as the utility lists them (`oeb_der_protection`, unverified; settings not stated).

## 4. Microinverter (LV)

- One microinverter per module, AC trunk to the board. Repo example Enphase IQ8PLUS-72-2-US: 290 VA rated AC, 60 V max DC, 240 V split-phase 60 Hz US (`repo_micro_hybrid`, unverified). IP rating not found.
- No DC string wiring, so no string fuses or DC isolator per module (typical).

## 5. Power optimizer with string inverter (LV)

- DC-DC optimizer per module, string to the inverter. Repo examples: SolarEdge P400 input 80 V, output 15 A, 99.5 %; Tigo TS4-A-O input 80 V, Isc 22 A (`repo_inverters_central`, unverified).
- Inverter examples in the repo: SolarEdge SE3K-SE10K, 900 V max, internal fan (`repo_micro_hybrid`, unverified).

## 6. Hybrid with battery, DC-coupled (LV)

- Strings and battery on the DC side of the hybrid inverter. The battery needs an overcurrent device between battery and inverter. The wiki states that storage follows the solar-inverter rules plus this device (`ei_prosumer`, unverified).
- Huawei SUN2000-L1 recommends a DC circuit breaker of at least 600 V DC, 20 A, for the battery switch (`huawei_l1_cables`, unverified; model-specific).
- Repo hybrid example: Sungrow SH10RT, 10 kW rated AC, PV max 1000 V, battery 150 to 600 V DC (`repo_micro_hybrid`, unverified).

## 7. Hybrid with battery, AC-coupled (LV)

- The battery inverter sits on the AC bus with the PV string inverter. Both connect to a local sources switchboard, which joins the main LV board at a single point (`ei_local_sources`, unverified). The same page says the secondary LV board shall not be used for islandable prosumer installations.
- Repo example: Victron MultiPlus-II 48/5000/70-50 230 V, 5000 VA, no PV input (`repo_micro_hybrid`, unverified).

## 8. Off-grid or islanded

- A 4-pole islanding switch (SDFI) disconnects lines and neutral; a separate switching device may be needed for the system referencing conductor (`ei_prosumer`, unverified).
- An insulation monitoring device (IMD) on the transformer side is suggested where the grid-side transformer stays energized for long periods (`ei_prosumer`, unverified). Trip thresholds for the IMD: `not_found`.
- Earthing (TT, TN-S, TN-C-S, IT) must be re-checked for automatic disconnection in island mode, where earth-fault current is lower (`ei_prosumer`, unverified).

## 9. Self-consumption with zero injection

- Architecture: bidirectional meter at the point of connection, reverse-power relay 32R where the utility or design requires export control (`oeb_der_protection`, unverified).
- The zero-injection control method and the export-limit device are `not_found` in the sources. The wiki states no rule for zero injection (`ei_self_consumption`).

## 10. Points of connection (all LV architectures)

- An overcurrent device must sit at the point where the PV system connects to the building installation, to keep the PV feeder fault from tripping the main breaker. Coordination may be hard when PV capacity approaches building power; options listed are oversizing the main breaker, splitting the PV system, or time selectivity above 630 A (`ei_prosumer`, unverified).
- Some national rules forbid connecting a 3-phase-plus-neutral local source to the LV network (the wiki cites NFC 15-400 as an example; `ei_prosumer`, unverified).

## 11. Sources

- `repo_inverters_central`: repo://harness/docs/pv/inverters/central_inverters_and_accessories.md
- `repo_micro_hybrid`: repo://harness/docs/pv/inverters/string_hybrid_micro_inverters.md
- `ei_prosumer`: https://www.electrical-installation.org/enwiki/Specific_protection_of_prosumer_electrical_installations
- `ei_local_sources`: https://www.electrical-installation.org/enwiki/Architectures_for_integration_of_local_sources
- `ei_self_consumption`: https://www.electrical-installation.org/enwiki/Photovoltaic_for_self-consumption_-_architecture_and_equipment_requirements
- `sma_stp_protective`: https://manuals.sma.de/STPxxUS50/en-US/12078896395.html
- `fronius_symo_manual`: https://manuals.fronius.com/html/4204260172/en.html
- `huawei_l1_cables`: https://support.huawei.com/enterprise/en/doc/EDOC1100136173/d7e21771/preparing-cables
- `phoenix_combiners`: https://www.phoenixcontact.com/en-sk/products/surge-protection/string-combiner-boxes-for-photovoltaic-systems
- `oeb_der_protection`: https://www.oeb.ca/sites/default/files/DER-wg3-Sample%20Protection%20Philosophy.pdf
