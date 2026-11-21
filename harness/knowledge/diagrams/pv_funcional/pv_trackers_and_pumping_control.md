# Solar tracker and solar pump control

Single-axis tracker control with limit switches and wind stow (NOV flyer, self-powered product), and a solar pump controller (Grundfos GI SPC I/O sheet).

Status key: unverified = cited public source; typical = generic practice without source; not_found = not located. Nothing is verified.
Spanish text for each item is in the `es` fields of the JSON records under `circuits/`.

## Single-axis tracker control with limit switches and wind stow (`pv_tracker_motor_control_limit_stow`)

A tracker controller drives a slew motor with end-of-travel limit switches and an anemometer that triggers stow.

- Diagram types: functional, MLD
- Record status: unverified
- Symbols: sym_contactor_coil_general, sym_plc_io. Devices: none.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| A1 | A | sym_plc_io | - | Tracker controller: reads sun position or irradiance and drives the motor. | typical |
| B1 | B | - | - | Anemometer (wind speed and direction). Standard wind sensor on the NOV product. | unverified |
| S1 | S | - | - | End-of-travel limit switches (east and west). Type not located. | not_found |
| M1 | M | - | - | Slew drive motor, 24 VDC on the NOV product. No DC motor symbol in the repository set. | unverified |
| G1 | G | - | - | Local supply: LiFePO4 battery with integrated module on the NOV product. | unverified |
| K1 | K | sym_contactor_coil_general | - | Forward and reverse contactor or H-bridge for a wired drive (typical). | typical |

**Application range**
- [unverified] Single-axis trackers. The NOV TechTrack is a self-powered proprietary product; a classic wired controller is typical. (sources: nov_techtrack)

**Power connection**
- [typical] Drive motor fed from the controller through forward and reverse contacts (typical).
- [unverified] NOV: no external controller wiring; the site uses a proprietary on-site mesh network. (sources: nov_techtrack)

**Control and signal connection**
- [typical] Anemometer wires to the controller input (typical).

**Protections**
- none

**Sequence**
- [unverified] Wind speed above the stow threshold moves the tracker to stow (NOV states a stow at 35 mph). (sources: nov_techtrack)
- [typical] Limit switch stops the motor at the end of travel (typical).

**Common errors**
- [typical] Limit switches without fail-safe wiring.
- [typical] Anemometer mounted in the turbulence of the array.
- [typical] Battery undersized for winter sun hours (NOV self-powered case).

**Sources**
- nov_techtrack: NOV TechTrack single-axis tracker flyer - https://assets.nov.com/NCP4N68N/at/cmb5wnnmbgk5brszbkjxgth/NOV_CMKT_Solar_TechTrack_Flyer.pdf (manufacturer_doc, accessed 2026-11-20)
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)

## Solar pump controller with DC input and digital run/stop (`pv_solar_pump_inverter_control`)

PV DC input to a pump controller; digital inputs for run/stop and dry-run or level; relay output for power-frequency switch-over.

- Diagram types: SLD, MLD, functional
- Record status: unverified
- Symbols: sym_circuit_breaker_device, sym_fuse_general, sym_motor_3ph_squirrel, sym_plc_io, sym_protective_earth, sym_pushbutton, sym_relay_coil_general. Devices: switch_disconnector.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| Q1 | Q | sym_circuit_breaker_device | switch_disconnector | PV DC breaker before the controller; open before any connection. | unverified |
| A1 | A | sym_plc_io | - | Solar pump controller: DC input PV+ and PV- (max 750 VDC), AC input 220-240 V 3-phase or 380-415 V 50 Hz. | unverified |
| M1 | M | sym_motor_3ph_squirrel | - | Three-phase pump motor fed by the controller. Output choke needed if the motor cable exceeds 50 m. | unverified |
| S1 | S | sym_pushbutton | - | RUN/STOP push button on a digital input. | unverified |
| B1 | B | - | - | Level or dry-run switch on a digital input (analogue level inputs not supported on the GI SPC). | typical |
| K1 | K | sym_relay_coil_general | - | Relay RO1 switches the motor to power-frequency supply (default function 30). | unverified |
| F1 | F | sym_fuse_general | - | Protection on the AC supply (typical). Rating not in the source. | typical |
| X1 | X | sym_protective_earth | - | PE terminal of controller and motor. | unverified |

**Application range**
- [unverified] Solar pumping with a dedicated pump controller (Grundfos GI SPC is the source). Other brands not fetched (Danfoss page not reached). (sources: grundfos_gi_spc)

**Power connection**
- [unverified] PV input DC PV+ and PV-; maximum 750 VDC; check polarity before connecting. (sources: grundfos_gi_spc)
- [unverified] AC input for grid or generator supply (3-phase; 380 V models use R, Y, B and PE). (sources: grundfos_gi_spc)
- [unverified] Motor cable above 50 m needs an output choke. (sources: grundfos_gi_spc)

**Control and signal connection**
- [unverified] Digital inputs 12 to 30 V NPN, programmable (S2). S3 remote run/stop by SMS. S4 RUN/STOP button. COM is +24 V common. S1 is internal to COM. (sources: grundfos_gi_spc)
- [unverified] Analogue water-level inputs AI1 to AI3 are marked not supported. Use a float or dry-run switch on a digital input. (sources: grundfos_gi_spc)
- [unverified] Relay RO2 default function 5: inverter fault. (sources: grundfos_gi_spc)

**Protections**
- [unverified] Open the DC breaker before any connection. Wait at least 5 minutes, then confirm zero voltage with a multimeter. (sources: grundfos_gi_spc)
- [unverified] Connect PE for personnel safety and EMI reduction. (sources: grundfos_gi_spc)
- [typical] Motor thermal protection through the controller (typical).

**Sequence**
- [typical] Start: DC on, check polarity, controller powers up, run command from S4 or S3.
- [typical] Dry-run or low-level input stops the pump and sets a fault (typical).
- [unverified] Switch-over to power-frequency through RO1 when the controller is not operating (function 30). (sources: grundfos_gi_spc)

**Common errors**
- [unverified] PV polarity reversed at the DC input. (sources: grundfos_gi_spc)
- [unverified] Analogue level sensor wired to AI1 to AI3. (sources: grundfos_gi_spc)
- [unverified] DC voltage above 750 VDC at the input. (sources: grundfos_gi_spc)
- [typical] NPN and PNP sensor types confused.

**Sources**
- grundfos_gi_spc: Grundfos GI SPC solar pump controller, electrical I/O instructions - https://www.grundfos.com/content/dam/local/en-za/catalogues/_jcr_content1/case-story-brochures11/GI%20SPC_Electical%20IO_GB_V0.0.pdf (manufacturer_doc, accessed 2026-11-20)
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)
