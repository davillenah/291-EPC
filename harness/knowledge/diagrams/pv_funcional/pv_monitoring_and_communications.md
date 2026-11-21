# Monitoring and communications (RS485/Modbus, Ethernet, sensors)

RS485 Modbus daisy chain (SMA module manual) and Ethernet datalogger with meter and sensors (Victron ESS guide). CAN for the BMS is in the storage file. Sensor output types were not located.

Status key: unverified = cited public source; typical = generic practice without source; not_found = not located. Nothing is verified.
Spanish text for each item is in the `es` fields of the JSON records under `circuits/`.

## RS485 Modbus daisy chain for inverter monitoring (`pv_monitoring_rs485_daisy_chain`)

Inverters on a two-wire RS485 bus (D+ and D-) with a shield and a termination plug at the datalogger end.

- Diagram types: MLD, functional
- Record status: unverified
- Symbols: sym_terminal_block. Devices: pv_inverter_grid_tie.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| A1 | A | - | pv_inverter_grid_tie | Inverter with RS485 module (optional on SMA; the inverter acts as subordinate only). | unverified |
| X1 | X | sym_terminal_block | - | RS485 terminals on the SMA module: D+ (terminal 2), D- (terminal 7), GND (terminal 5). | unverified |
| A2 | A | - | - | Datalogger or data manager (SMA partners: Data Manager M, COM Gateway). Model not selected. | not_found |
| A3 | A | - | - | Termination plug on terminals 2 and 7 at the end of the bus. | unverified |

**Application range**
- [unverified] SMA RS485 modules; other brands use the same two-wire bus with their own terminal labels (typical). (sources: sma_md485)

**Power connection**
- [unverified] Shielded twisted pair; copper-foil shield clamped to the module shield clamp and grounded through the module fastening screw in the inverter enclosure. (sources: sma_md485)
- [unverified] Maximum bus length 1200 m. (sources: sma_md485)
- [not_found] Cable type beyond twisted pair: see the separate SMA RS485 cabling plan (not read).
- [unverified] Ethernet can run in parallel with RS485. No automatic firmware updates over RS485. (sources: sma_rs485_page)

**Control and signal connection**
- none

**Protections**
- none

**Sequence**
- [typical] Power the datalogger first, then verify the RS485 link on the datalogger.
- [typical] Assign unique device addresses to each inverter.
- [typical] Terminate according to the datalogger manual.

**Common errors**
- [typical] D+ and D- swapped.
- [unverified] Bus longer than 1200 m or star wiring. (sources: sma_md485)
- [typical] RS485 cable routed with power cables.
- [typical] Termination missing on a long bus.

**Source conflicts**
- RS485 termination rule: The SMA module text says attach the terminator only when one connection cable is used. A common rule (typical) terminates both ends of the bus. Confirm with the datalogger manual. (sources: sma_md485)

**Sources**
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)
- sma_md485: SMA MD.485-40 RS485 module installation manual (rev 10) - https://files.sma.de/downloads/MD485-40-IA-en-10.pdf (manufacturer_doc, accessed 2026-11-20)
- sma_rs485_page: SMA manual page: RS485 interface (STP xx50) - https://manuals.sma.de/STPxx50/en-US/14988097931.html (manufacturer_doc, accessed 2026-11-20)

## Ethernet datalogger with meter, MPPT and irradiance/temperature sensors (`pv_monitoring_ethernet_datalogger_sensors`)

A central gateway (Victron GX type) collects inverter, meter and sensor data over Ethernet, USB-RS485 and VE.direct links.

- Diagram types: MLD, functional
- Record status: unverified
- Symbols: sym_current_transformer_2sec, sym_plc_io. Devices: ct.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| A1 | A | sym_plc_io | - | Datalogger / GX gateway: online via Ethernet or WiFi module. | unverified |
| A2 | A | - | - | Ethernet switch or router for the plant network. | typical |
| P1 | P | - | - | Energy meter. Letter P is not in the repository table; to confirm. | typical |
| T1 | T | sym_current_transformer_2sec | ct | PV current sensor (CT) for inverters not on the Victron auto-list (Fronius, SMA, ABB, SolarEdge). | unverified |
| B1 | B | - | - | Irradiance sensor (pyranometer). Output type not located in the sources. | not_found |
| B2 | B | - | - | Module temperature sensor. Typical types PT100 or 4-20 mA transmitter (typical). | typical |

**Application range**
- [unverified] Remote monitoring of PV plants with a datalogger and a meter. Brand-specific items from the Victron ESS guide. (sources: victron_ess_guide)

**Power connection**
- [unverified] Energy meters connect to the GX device through a USB-to-RS485 interface or Zigbee. (sources: victron_ess_guide)
- [unverified] The smart battery connects through a special RJ45 cable (CAN-bus BMS cable). (sources: victron_ess_guide)
- [unverified] MPPT chargers connect to the GX by VE.direct cable. (sources: victron_ess_guide)
- [unverified] Inverter links to the GX by RJ45 cable. (sources: victron_ess_guide)
- [not_found] Sensor signal type and cabling for the irradiance sensor: not located.

**Control and signal connection**
- none

**Protections**
- none

**Sequence**
- [unverified] Wire each part per its own manual; install inter-device communication cables last. (sources: victron_ess_guide)

**Common errors**
- [typical] Sensor signal type mismatch (voltage vs current loop).
- [typical] BMS cable plugged into a standard Ethernet port.
- [typical] Meter placed in the wrong position for export control (see pv_export_limitation_meter_ct_limiter).

**Sources**
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)
- victron_ess_guide: Victron ESS quick installation guide (online manual) - https://victronenergy.com/live/_export/xhtml/ess:quick-installation-guide (manufacturer_doc, accessed 2026-11-20)
