# Typical control circuits: start, interface protection, rapid shutdown, disconnector trip

Grid connection sequence, interface protection with 27, 59, 81 and 86 relays, rapid shutdown (NEC 690.12, US reference), and motorized disconnector trip interlocks. The last one has no fetched source.

Status key: unverified = cited public source; typical = generic practice without source; not_found = not located. Nothing is verified.
Spanish text for each item is in the `es` fields of the JSON records under `circuits/`.

## Inverter grid connection start and reconnection sequence (`pv_grid_connection_start_sequence`)

Functional sequence: DC on, grid check with a waiting time, interface closes, MPPT ramp, trip and reconnection.

- Diagram types: functional
- Record status: unverified
- Symbols: sym_circuit_breaker_device, sym_contactor_coil_general. Devices: contactor, mccb, pv_inverter_grid_tie.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| A1 | A | - | pv_inverter_grid_tie | Grid-tie inverter with internal grid monitoring. | typical |
| Q1 | Q | sym_circuit_breaker_device | mccb | AC breaker or interface breaker. | typical |
| K1 | K | sym_contactor_coil_general | contactor | Interface contactor closed by the inverter run signal (if external). | typical |

**Application range**
- [unverified] Grid-tie inverters at LV. Trip concept from the Tesla frequency page; reconnection timing not located. (sources: tesla_freq)

**Power connection**
- [typical] Inverter closes the grid connection only when voltage and frequency are inside limits for the waiting time.

**Control and signal connection**
- [typical] Run signal from inverter to the K1 coil (if external contactor).

**Protections**
- [unverified] Under/over-frequency and voltage trips with time delays (see pv_interface_protection_27_59_81). (sources: tesla_freq)

**Sequence**
- [typical] 1. DC applied; inverter self-test.
- [not_found] 2. Grid check: voltage and frequency inside limits for the waiting time. Waiting time value not located.
- [typical] 3. Interface closes; MPPT ramps up.
- [typical] 4. Abnormal grid: disconnect and wait before reconnecting.
- [not_found] 5. Reconnection after grid return: value not located in the fetched sources.

**Common errors**
- [typical] Reconnect immediately after a trip (typical risk: repeated trips).
- [typical] Grid settings not set to the local grid code.

**Sources**
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)
- tesla_freq: Tesla Powerwall+ installation manual, Appendix D: frequency ride-through - https://energylibrary.tesla.com/docs/Public/EnergyStorage/Powerwall/+/InstallManual/BackupSwitch/en-us/GUID-7374FAFE-32F2-4FF8-AFB8-B7E9ECAF3852.html (manufacturer_doc, accessed 2026-11-20)

## Interface protection: 27, 59, 81 relays and lockout 86 (`pv_interface_protection_27_59_81`)

Undervoltage 27, overvoltage 59 and frequency 81 relays read grid voltage through a VT and trip the interface breaker through a shunt coil; lockout 86 holds it open.

- Diagram types: SLD, functional
- Record status: unverified
- Symbols: sym_circuit_breaker_device, sym_relay_coil_general, sym_transformer_2w. Devices: mccb, relay_ansi_27, relay_ansi_59, relay_ansi_81, relay_ansi_86, vt.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| K27 | K | sym_relay_coil_general | relay_ansi_27 | Undervoltage relay (ANSI 27). | typical |
| K59 | K | sym_relay_coil_general | relay_ansi_59 | Overvoltage relay (ANSI 59). | typical |
| K81 | K | sym_relay_coil_general | relay_ansi_81 | Frequency relay (ANSI 81), under and over. | typical |
| K86 | K | sym_relay_coil_general | relay_ansi_86 | Lockout relay, latched after a trip, manual reset. | typical |
| T1 | T | sym_transformer_2w | vt | Voltage transformer on the grid side, feeding the relays. | typical |
| Q1 | Q | sym_circuit_breaker_device | mccb | Interface breaker, opened by shunt coil. | typical |

**Application range**
- [typical] Distributed generation tied to the LV grid. Set points follow the local grid code.

**Power connection**
- [typical] VT on the grid side of the interface breaker, not the load side.

**Control and signal connection**
- [typical] Relay outputs wired to the shunt trip coil of Q1 through K86 contacts.

**Protections**
- [unverified] Frequency trip points are configurable within listed ranges: three under and three over trip points, each with a time, plus one instantaneous under and over point. Defaults meet IEEE 1547 (Tesla). (sources: tesla_freq)
- [not_found] Voltage trip set points and times: not covered in the frequency source.

**Sequence**
- [typical] Fault: relay picks up, time delay runs, then Q1 trips and K86 latches.
- [typical] Manual reset of K86 after the grid is restored and the cause is cleared.

**Common errors**
- [typical] Set points not matching the local grid code.
- [typical] VT on the load side.
- [typical] K86 not reset, inverter stays off.

**Sources**
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)
- tesla_freq: Tesla Powerwall+ installation manual, Appendix D: frequency ride-through - https://energylibrary.tesla.com/docs/Public/EnergyStorage/Powerwall/+/InstallManual/BackupSwitch/en-us/GUID-7374FAFE-32F2-4FF8-AFB8-B7E9ECAF3852.html (manufacturer_doc, accessed 2026-11-20)

## Rapid shutdown initiator and array controlled state (US NEC 690.12 reference) (`pv_rapid_shutdown_initiator`)

An initiator signals the array disconnect or module electronics to bring conductors to a controlled state. Reference only outside the US.

- Diagram types: SLD, functional
- Record status: unverified
- Symbols: sym_disconnector, sym_relay_coil_general, sym_switch_emergency_stop. Devices: switch_disconnector.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| S1 | S | sym_switch_emergency_stop | - | Rapid shutdown initiator switch at the service entrance. | typical |
| K1 | K | sym_relay_coil_general | - | Shutdown relay that sends the initiation signal. | typical |
| Q1 | Q | sym_disconnector | switch_disconnector | Array-level disconnect (PVHCS) or module-level electronics (alternative). | unverified |

**Application range**
- [unverified] US NEC 690.12 requirement for rooftop PV. Outside the US it is a reference, not a local rule (not located). (sources: iaei_rsd)

**Power connection**
- none

**Control and signal connection**
- [unverified] Initiator is the NEC 690.12(C) device; where a hazard control system needs initiation, that device performs it. (sources: iaei_rsd)

**Protections**
- [unverified] Controlled state within 30 seconds of initiation (2017 NEC cycle). The 2014 NEC used 10 seconds. (sources: iaei_rsd)
- [unverified] Array boundary one foot (305 mm) from the array. Inside the boundary, 80 V within 30 seconds (from 2019). (sources: iaei_rsd)
- [unverified] Array-level listed system (PVHCS, UL 3741) or module-level electronics (microinverters, optimizers) as alternatives. (sources: iaei_rsd)

**Sequence**
- [typical] Initiate: signal to Q1 and to module electronics; array conductors reach the controlled state.

**Common errors**
- [unverified] Boundary conductors above the 80 V limit after the timing. (sources: iaei_rsd)
- [not_found] Local rule (Latin America) for rapid shutdown: not located.

**Source conflicts**
- Boundary distance: IAEI says one foot (305 mm). The 1.5 m (5 ft) figure appears in the same article only as a 2014 building distance. Check the code year and jurisdiction. (sources: iaei_rsd)

**Sources**
- iaei_rsd: IAEI Magazine: NEC rapid shutdown requirements and UL 3741 (2023) - https://iaeimagazine.org/electrical-fundamentals/nec-rapid-shutdown-requirements-and-ul-3741/ (secondary_article, accessed 2026-11-20)
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)

## Motorized disconnector with shunt trip, contactor and interlocks (`pv_motorized_disconnector_trip_interlock`)

Motor-operated disconnector on the board with a shunt coil, a disconnection contactor, a lockout and a key interlock with the grid breaker.

- Diagram types: SLD, functional
- Record status: typical
- Symbols: sym_contactor_coil_general, sym_disconnector, sym_fuse_general, sym_pushbutton, sym_relay_coil_general. Devices: contactor, relay_ansi_86, switch_disconnector.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| Q1 | Q | sym_disconnector | switch_disconnector | Motorized disconnector or breaker with spring-charge motor. | typical |
| Q1-YC | Q | sym_relay_coil_general | - | Shunt trip coil on the breaker (suffix YC; not in the repository table). | typical |
| K1 | K | sym_contactor_coil_general | contactor | Disconnection contactor, energised by the protection output. | typical |
| K2 | K | sym_relay_coil_general | relay_ansi_86 | Lockout relay: holds the trip until manual reset. | typical |
| S1 | S | sym_pushbutton | - | Manual trip push button. | typical |
| S2 | S | - | - | Key interlock with the grid breaker. Symbol not in the repository set. | typical |
| F1 | F | sym_fuse_general | - | Fuse for the control supply of the shunt coil and contactor. | typical |

**Application range**
- [not_found] Motorized disconnector or breaker on a PV or grid interface board. No specific source fetched for this circuit.

**Power connection**
- [typical] Shunt coil is energised only to trip; the motor operator charges the spring after each close.

**Control and signal connection**
- [typical] Auxiliary contact of Q1 (normally closed) in series with K1 so that K1 cannot re-close a tripped breaker (typical).
- [typical] Key interlock with the grid breaker: only one of the two can be closed (typical).

**Protections**
- none

**Sequence**
- [typical] Protection output energises K1 or the shunt coil; Q1 opens; the auxiliary contact opens K1.
- [typical] Close only after K2 is reset and protection is healthy.

**Common errors**
- [typical] Shunt coil energised continuously.
- [typical] Auxiliary contacts wired in the wrong state.
- [typical] K2 lockout not reset after a trip.

**Sources**
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)
