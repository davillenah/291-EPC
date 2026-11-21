# PV AC-side protection and interconnection: overcurrent, RCD, interface relays, meter

AC side from the inverter output to the point of connection. Status vocabulary in `pv_sld_mld_conventions.md`. Facts only, sourced on 2026-11-20. Nothing is verified. Norm-quoted values are `pending review`.

## 1. AC overcurrent device at the inverter output

| Point | Value or rule | Status | Source |
|---|---|---|---|
| Conductor ampacity | 125 % of the inverter maximum current, or the ampacity after conditions of use without the 125 % factor, whichever is greater | pending review | `iaei_ac` (NEC 690.8(A)(3), short citation) |
| Overcurrent device rating | Typically 125 % of the rated output current, rounded up to the next standard rating; never less than 125 % of the rated continuous output current | pending review | `iaei_ac` |
| Manual limit | The inverter manual may limit the maximum external device; it overrides the 125 % choice if lower | unverified | `iaei_ac` |
| Device location | Usually at the utility end, because the utility is the higher fault-current source | unverified | `iaei_ac` |
| SMA STP US model | Maximum output overcurrent 60 A | unverified | `sma_stp_protective` |
| Fronius Symo three-phase | Maximum AC fuse 25 A on the listed range; recommended fuse by model: 3.0 kW 10 A; 3.7 kW 13 A; 4.5 kW 16 A; 5.0 kW 16 A; 6.0 kW 16 A; 7.0 kW 20 A; 8.2 kW 25 A | unverified | `fronius_symo_manual` |
| Huawei SUN2000-L1 (single-phase) | Customer-supplied AC breaker, at least 250 V AC: 2 kW 16 A; 3 kW and 3.68 kW 25 A; 4 kW to 6 kW 32 A | unverified | `huawei_l1_cables` |

Rule `r08` in `pv_decision_rules.json`. The 125 % factor is `pending review`; the manufacturer values are model-specific.

Cable and breaker sizing is a calculation (AEA 90364 / IEC 60364 workflow) and is outside this research.

## 2. Overcurrent at the point of connection

- An overcurrent device must be located at the point where the PV system connects to the building installation, to avoid tripping the main breaker on a PV feeder fault (`ei_prosumer`, unverified).
- Selectivity with the main breaker may be hard when PV capacity approaches building power. Options listed: oversize the main breaker, split the PV system, or use time selectivity above 630 A (`ei_prosumer`, unverified).
- DC and AC disconnection means are required on both the DC and AC sides of the inverters, plus the PV switchboard (`ei_prosumer`, unverified).
- An AC disconnection device at the local-sources switchboard isolates PV for maintenance (`ei_prosumer`, unverified).

## 3. Residual-current protection

### 3.1 Inverter-internal RCMU (SMA)

- All-pole sensitive residual-current monitoring unit that monitors AC and DC residual currents. It disconnects the inverter from the grid, redundantly, when residual-current jumps exceed 30 mA (`sma_rcmu`, unverified). If it malfunctions, the inverter disconnects at all poles at once.
- No external RCD is needed if an overcurrent device gives automatic disconnection under DIN VDE 0100-410 (`sma_rcmu`, unverified).
- SMA lists the all-pole residual-current monitoring unit as "Available" (`sma_stp_protective`, unverified). Not stated as mandatory.
- SMA ground-fault insulation monitoring: Riso above 100 kOhm (`sma_stp_protective`, unverified).

### 3.2 External RCD where local rules require one (conflict c03)

| Source | Statement | Status |
|---|---|---|
| SMA (`sma_rcmu`) | Where local regulations require an RCD: type B, rated 500 mA or higher; one RCD per inverter; a lower rating may trip falsely | unverified |
| Fronius (`fronius_symo_manual`) | Type A generally sufficient, but Fronius recommends an RCD suitable for frequency converters; trip current at least 100 mA; whether one is required depends on local rules and the retailer | unverified |
| Kostal PIKO note (`kostal_piko_rcd`) | Transformerless inverters may produce DC current in the outer protective conductor. Cites EN 62109-1: "recommends that RCD/RCM type B is used if galvanically unisolated". DC threshold 6 mA: if DC can exceed it, only type B is permitted on the AC grid side. For other RCCBs: "type B RCCBs must always be used" | pending review (norm value cited) |

Reading for the SLD (`r09`, `r10`):

- Galvanically unisolated (transformerless) inverter: draw type B where the design includes an external RCD (Kostal, citing EN 62109-1; pending review).
- Local rules require an RCD: follow the SMA condition (type B, 500 mA or more, one per inverter) (unverified).
- Type A is only the Fronius general statement and depends on the inverter and local rules. It is not the default for transformerless units in this research.
- The RCMU inside the inverter is not an external RCD on the SLD (see `pv_rcmu` device).

RCD sensitivity for indirect contact and fire protection (30 mA, 300 mA) are in `../sld_mld/selection_criteria.md`, status `pending review`.

## 4. Interface protection (utility or DER requirements)

The OEB sample protection philosophy (`oeb_der_protection`, third-party sample document, unverified) lists these functions for DER interconnection. Settings are not in the sample; it says detailed settings come after the utility's impact assessment.

| Function | ANSI | Note in sample | Harness device |
|---|---|---|---|
| Overvoltage | 59 | Trips the breaker for internal and external faults | `relay_ansi_59` (existing) |
| Undervoltage | 27 | Trips the breaker for internal and external faults | `relay_ansi_27` (existing) |
| Over-frequency | 81O | Trips the breaker for internal and external faults | `relay_ansi_81` (existing) |
| Under-frequency | 81U | Trips the breaker for internal and external faults | `relay_ansi_81` (existing) |
| Synchronization check | 25 | Listed for internal faults (multi-function relay) | not drawn; `not_found` as a device |
| Reverse power | 32R | Monitors utility supply for power flow back to the grid; load monitored | `relay_ansi_32_reverse_power` (new) |
| Overcurrent | 50/51 | Phase overcurrent for external faults | `relay_ansi_50_51` (existing) |
| Directional overcurrent | 67 | Fault current flowing back into a source; normally on incoming breakers with two or more sources | `relay_ansi_67_directional_overcurrent` (new) |
| Active anti-islanding | ID | Required under IEEE 1547 and UL 1741 SA | not a separate relay; part of the inverter |

- Anti-islanding in SMA: frequency shift method (`sma_stp_protective`, unverified); tested to UL 1741 SA and UL 1741 SB / IEEE 1547-2018 (`sma_stp_interfaces`, unverified). No trip thresholds in the SMA page.
- Trip thresholds and times for ANSI 27, 59, 81, 32R, 67: `not_found` in every fetched source. Use the utility's settings.

## 5. Meter

- Bidirectional meter at the point of connection: `typical` (generic practice; the utility sets the model).
- Repo examples: SMA EMETER-20 (direct to 63 A, 230/400 V, 1 %, IP2X) and Huawei DTSU666-H with 100 A CT set (RS485 Modbus-RTU 9600, 0.5 % / 1 %) (`repo_inverters_central`, unverified). Bidirectional capability is not stated in those rows: `not_found`.

## 6. Inverter output for hybrid and AC-coupled storage

- Storage: same rules as solar inverters, plus an overcurrent device between batteries and the inverter (`ei_prosumer`, unverified).
- Islanding: 4-pole islanding switch (SDFI); a separate switching device for the system referencing conductor may be needed; an IMD may be added on the transformer side (`ei_prosumer`, unverified).
- National rules may forbid a 3-phase-plus-neutral local source on LV networks (NFC 15-400 cited; `ei_prosumer`, unverified).

## 7. Sources

- `iaei_ac`: https://iaeimagazine.org/columns/photovoltaic/conductors-currents-and-circuit-protection-the-ac-side/
- `iaei_oc`: https://iaeimagazine.org/columns/photovoltaic/photovoltaic-power-system-overcurrent-protection-why-how-and-where/
- `ei_prosumer`: https://www.electrical-installation.org/enwiki/Specific_protection_of_prosumer_electrical_installations
- `sma_rcmu`: https://manuals.sma.de/SMAStorageXLPackage/en-US/17058314251.html
- `sma_stp_protective`: https://manuals.sma.de/STPxxUS50/en-US/12078896395.html
- `sma_stp_interfaces`: https://manuals.sma.de/STPxx-US-41/en-US/391139595.html
- `fronius_symo_manual`: https://manuals.fronius.com/html/4204260172/en.html
- `huawei_l1_cables`: https://support.huawei.com/enterprise/en/doc/EDOC1100136173/d7e21771/preparing-cables
- `kostal_piko_rcd`: https://www.kostal-solar-electric.com/fileadmin/downloadcenter/kse/1210_HE-RCD-RCM.pdf
- `oeb_der_protection`: https://www.oeb.ca/sites/default/files/DER-wg3-Sample%20Protection%20Philosophy.pdf
- `repo_inverters_central`: repo://harness/docs/pv/inverters/central_inverters_and_accessories.md
