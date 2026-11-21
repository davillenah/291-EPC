# Zero export, limitation and battery storage

Export limitation with a CT and grid meter; DC-coupled and AC-coupled battery. The Victron Q&A on grid meter position is a secondary source and one thread is unresolved.

Status key: unverified = cited public source; typical = generic practice without source; not_found = not located. Nothing is verified.
Spanish text for each item is in the `es` fields of the JSON records under `circuits/`.

## Zero or limited export with grid meter, CT and limiter (`pv_export_limitation_meter_ct_limiter`)

A CT at the grid connection feeds a meter and a limiter that sets the inverter output. A relay or Modbus setpoint is the inverter input.

- Diagram types: SLD, functional
- Record status: unverified
- Symbols: sym_current_transformer_2sec, sym_relay_coil_general. Devices: ct, pv_inverter_grid_tie.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| T1 | T | sym_current_transformer_2sec | ct | CT at the grid connection point, ahead of the loads, measures net flow. | unverified |
| P1 | P | - | - | Grid meter reading the CT. Letter P not in the repository table. | unverified |
| A1 | A | - | - | Export controller or limiter. Brand (e.g., DEIF) not located. | not_found |
| K1 | K | sym_relay_coil_general | - | Relay output sending the export limit to the inverter (if the inverter has a hardware input). | typical |
| A2 | A | - | pv_inverter_grid_tie | Inverter with power limit input or Modbus setpoint. | typical |

**Application range**
- [typical] Zero or limited export where the utility or the site prohibits feed-in.

**Power connection**
- [unverified] CT on the incoming supply ahead of the loads. A meter after the inverter sees only inverter output and misses consumption. (sources: victron_grid_meter_qa)
- [unverified] A grid-side meter measures the same as the inverter internal sensor when no loads are on the AC input. (sources: victron_grid_meter_qa)

**Control and signal connection**
- [typical] Relay or Modbus signal from the limiter to the inverter setpoint.

**Protections**
- [typical] Fail-safe: if the meter link is lost, the inverter limits to zero export (typical).

**Sequence**
- [unverified] Set the meter role in the gateway, then set the external meter as an AC load (Victron Q&A). (sources: victron_grid_meter_qa)
- [typical] Verify export is zero under real load.

**Common errors**
- [typical] CT polarity reversed.
- [unverified] Meter placed after the inverter. (sources: victron_grid_meter_qa)
- [unverified] Feed-in control inactive because the meter role was not set. (sources: victron_grid_meter_qa)

**Source conflicts**
- Grid meter role thread: The Q&A says feed-in worked only after the MultiPlus was set as grid meter. A later poster still saw only critical loads measured, and the thread does not resolve it. (sources: victron_grid_meter_qa)

**Sources**
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)
- victron_grid_meter_qa: Victron community archive: grid meter position in ESS configuration (Q&A) - https://communityarchive.victronenergy.com/questions/143738/grid-meter-position-in-ess-configuration.html (secondary_article, accessed 2026-11-20)

## DC-coupled battery with BMS, fuse, disconnector and precharge (`pv_battery_dc_coupled_ess`)

Battery on a DC bus with fuse, DC disconnector, main contactor and precharge, controlled by the BMS over CAN.

- Diagram types: SLD, MLD, functional
- Record status: unverified
- Symbols: sym_contactor_coil_general, sym_disconnector, sym_fuse_general, sym_plc_io, sym_switch_emergency_stop. Devices: contactor, fuse_gg, switch_disconnector.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| G1 | G | - | - | Battery pack (storage). The repository table has no storage letter; G used for generation or storage (typical). | typical |
| F1 | F | sym_fuse_general | fuse_gg | Battery fuse at the positive pole, close to the battery (typical). | typical |
| Q1 | Q | sym_disconnector | switch_disconnector | Battery DC disconnector, lockable. | typical |
| K1 | K | sym_contactor_coil_general | contactor | Main battery contactor. | typical |
| K2 | K | sym_contactor_coil_general | - | Precharge contactor in series with a precharge resistor (resistor letter R not in the repository table). | typical |
| A1 | A | sym_plc_io | - | BMS: monitors cell voltage, temperature and current; enables the contactors. | unverified |
| S1 | S | sym_switch_emergency_stop | - | Emergency stop removing the contactor control supply. | typical |

**Application range**
- [unverified] Lithium battery with a hybrid or DC-coupled inverter-charger. Brand-specific items from the Victron guide only. (sources: victron_ess_guide)

**Power connection**
- [typical] Battery to inverter DC input through fuse, disconnector and main contactor; cable kept short.
- [unverified] BMS communicates with the inverter-charger over CAN (special RJ45 cable). (sources: victron_ess_guide)
- [not_found] Precharge value and time: not located in the sources.

**Control and signal connection**
- [typical] BMS enable signal to the main contactor (typical).
- [typical] Emergency stop breaks the control supply to the contactors.

**Protections**
- [typical] Battery fuse rated for the DC short-circuit current of the battery (typical).
- [typical] Over/under voltage and temperature cut-offs in the BMS (typical).

**Sequence**
- [typical] BMS powers up; inverter checks battery voltage.
- [typical] Close the precharge contactor through the resistor until the DC bus is near battery voltage.
- [typical] Close the main contactor, then open the precharge contactor.

**Common errors**
- [typical] No precharge: inrush at main contactor closing.
- [unverified] BMS cable plugged in the wrong port. (sources: victron_ess_guide)
- [typical] Battery polarity reversed on DC terminals.

**Sources**
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)
- victron_ess_guide: Victron ESS quick installation guide (online manual) - https://victronenergy.com/live/_export/xhtml/ess:quick-installation-guide (manufacturer_doc, accessed 2026-11-20)

## AC-coupled battery storage on the AC board (`pv_battery_ac_coupled_storage`)

A storage inverter sits on the AC side next to the PV inverter, with its own AC breaker and a shared grid meter.

- Diagram types: SLD, MLD
- Record status: typical
- Symbols: sym_circuit_breaker_device. Devices: mccb.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| A1 | A | - | - | Storage inverter (bidirectional) with battery. | typical |
| G1 | G | - | - | Battery pack. | typical |
| Q1 | Q | sym_circuit_breaker_device | mccb | AC breaker for the storage inverter. | typical |
| P1 | P | - | - | Shared grid meter (letter P not in the repository table). | typical |

**Application range**
- [not_found] Retrofit of storage on an existing PV plant. Topology details not located in the fetched sources.

**Power connection**
- [typical] AC output of the storage inverter connects to its own breaker on the AC board.
- [typical] Grid meter must see both PV and storage flows for export control.

**Control and signal connection**
- [not_found] Communication between storage and PV inverter for export control: typical Modbus or CAN; not located.

**Protections**
- [typical] Anti-islanding and export limit as in the other files.

**Sequence**
- none

**Common errors**
- [typical] Charge from grid and export at the same time without control (typical).
- [typical] Storage inverter on the PV inverter output without a dedicated breaker.

**Sources**
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)
