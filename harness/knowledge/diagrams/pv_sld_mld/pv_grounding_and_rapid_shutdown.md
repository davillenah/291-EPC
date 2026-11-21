# PV earthing, insulation monitoring and rapid shutdown

Earthing scheme of the PV installation, the transformerless effect on DC poles, IMD, and rapid shutdown. Status vocabulary in `pv_sld_mld_conventions.md`. Facts only, sourced on 2026-11-20. Nothing is verified. Norm-quoted values are `pending review`.

## 1. Earthing and galvanic separation

| Point | Status | Source |
|---|---|---|
| Without galvanic separation (transformerless), one DC pole cannot be earthed (wiki: "impossible to earth one pole") | unverified | `ei_pv_safety` |
| With galvanic separation, earthing depends on cell technology: direct earthing, resistance earthing, or an insulation monitoring device with no earthed conductor | unverified | `ei_pv_safety` |
| Without galvanic separation, AC protection can detect insulation faults | unverified | `ei_pv_safety` |
| PE, FE (functional earth) and functional earthing: not explicitly addressed in the fetched wiki page | not_found | `ei_pv_safety` |
| IEC 60364-7-712 ed.3.0 earthing: section 712.54 covers earthing arrangements and protective conductors (clause index only) | unverified (clause index) | `iec60364_7_712_preview` |
| Earthing scheme in island mode: TT, TN-S, TN-C-S, IT combinations; check automatic disconnection in island mode (earth-fault current lower) | unverified | `ei_prosumer` |
| Artificial-neutral IT arrangement: first-fault disconnection can still rely on RCD protection (no type or sensitivity given) | unverified | `ei_prosumer` |

Use: the SLD must show the earthing system and, for transformerless inverters, that no DC pole is earthed. Rule `r17` in `pv_decision_rules.json`.

## 2. Insulation monitoring

| Item | Value or rule | Status | Source |
|---|---|---|---|
| SMA ground-fault insulation monitoring | Riso above 100 kOhm | unverified | `sma_stp_protective` |
| IMD on the transformer side, for long islanded operation where the grid-side transformer stays energized | Suggested by the wiki; threshold not stated | unverified | `ei_prosumer` |
| External IMD alarm threshold | Not found | not_found | - |

The IMD device record is `devices/imd_insulation_monitor.json`.

## 3. Rapid shutdown

Rapid shutdown is a US-code requirement and a manufacturer feature in the sources read. IEC text was not found.

| Point | Value or rule | Status | Source |
|---|---|---|---|
| Initiation | Disconnect the inverter from AC grid voltage (SMA, UL 1741 PVRSE) | unverified | `sma_stp_interfaces` |
| DC conductors | Limited to below 30 V within 30 s | pending review (code value quoted by SMA) | `sma_stp_interfaces` |
| Array disconnect | PV array disconnect switches disconnect within 15 s of initiation | unverified | `sma_stp_interfaces` |
| SunSpec-signal setup | Sum of standby voltages per string above 3.6 V and below 30 V | unverified | `sma_stp_interfaces` |
| DC line length per string | Not more than 300 m (1000 ft) recommended | unverified | `sma_stp_interfaces` |
| SMA default | Rapid shutdown disabled by default; enabling without disconnect switches can damage the inverter | unverified | `sma_stp_interfaces` |
| NEC 690.12 | Rapid shutdown requirement (short citation only, not fetched) | not_found (text) | - |
| IEC 60364-7-712 ed.3.0 | Rapid shutdown is not in the preview's topic list | not_found | `iec60364_7_712_preview` |
| Repo rapid-shutdown reference (JMS-F-type): Voc 60 V, 15 A, Type 4X | Repo notes an identity mismatch, not confirmed | unverified | `repo_inverters_central` |
| Module-level optimizers and microinverters | Give module-level DC shutdown by design (typical) | typical | - |

Rule `r14` in `pv_decision_rules.json`: apply only where a rule requires rapid shutdown. Conflict c05 notes the IEC and US sources differ in scope.

Device: `devices/pv_rapid_shutdown_device.json`.

## 4. Ride-through and other inverter functions

- SMA: the inverter stays connected for a defined ride-through time during a grid dip and waits for voltage recovery. The time is not stated on the page (`sma_stp_interfaces`, unverified; value `not_found`).
- SMA ShadeFix (enabled by default) and arc-fault detection are inverter functions, not separate devices (`sma_stp_interfaces`, unverified).

## 5. Sources

- `ei_pv_safety`: https://www.electrical-installation.org/enwiki/PV_System:_how_to_ensure_safety_during_normal_operation
- `ei_prosumer`: https://www.electrical-installation.org/enwiki/Specific_protection_of_prosumer_electrical_installations
- `iec60364_7_712_preview`: https://assets.vde-verlag.de/iec-normen/preview-pdf/info_iec60364-7-712%7Bed3.0%7Db.pdf
- `sma_stp_interfaces`: https://manuals.sma.de/STPxx-US-41/en-US/391139595.html
- `sma_stp_protective`: https://manuals.sma.de/STPxxUS50/en-US/12078896395.html
- `sma_rcmu`: https://manuals.sma.de/SMAStorageXLPackage/en-US/17058314251.html
- `repo_inverters_central`: repo://harness/docs/pv/inverters/central_inverters_and_accessories.md
