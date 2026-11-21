# IEC 60617 control and signalling symbols: drawing guide

Status tags: `unverified` = from a cited public source, not checked against the printed standard. `typical` = generic practice. `not_found` = not located. Nothing is `verified`.

Machine-readable records: `symbols/*.json`, index in `symbols_index.json`.

## Table of control symbols

| Symbol (en) | Symbol (es) | IEC 60617 ID | Status | Letter | Record |
|---|---|---|---|---|---|
| Make contact (NO), general | Contacto de cierre (NA), general | S00227 | unverified | parent device | `sym_contact_make_general` |
| Break contact (NC), general | Contacto de apertura (NC), general | S00229 | unverified | parent device | `sym_contact_break_general` |
| Make contact, delayed closing (on-delay) | Contacto de cierre temporizado | S00243 | unverified | parent (timer) | `sym_contact_make_delayed_closing` |
| Break contact, delayed opening (off-delay) | Contacto de apertura temporizado | S00245 | unverified | parent (timer) | `sym_contact_break_delayed_opening` |
| Make contact, delayed (title only) | Contacto de cierre temporizado (título) | S00247 | unverified | parent (timer) | `sym_contact_make_delayed` |
| Push-button | Pulsador | S00475 | unverified | S | `sym_pushbutton` |
| Actuator, operated by pushing | Accionador por empuje | S00171 | unverified | S | `sym_actuator_pushing` |
| Manual switch, general | Interruptor manual, general | S00253 | unverified | S | `sym_switch_manual_general` |
| Emergency stop switch | Parada de emergencia | S00258 | unverified | S | `sym_switch_emergency_stop` |
| Switch with signal lamp (installation) | Interruptor con piloto (instalación) | S00467 | unverified | S | `sym_switch_signal_lamp` |
| Relay coil unaffected by AC | Bobina de relé no afectada por CA | S00315 | unverified | K | `sym_relay_coil_ac_unaffected` |
| Relay coil, general | Bobina de relé, general | not_found | not_found | K | `sym_relay_coil_general` |
| Contactor coil, general | Bobina de contactor, general | not_found | not_found | Q | `sym_contactor_coil_general` |
| Contactor with automatic tripping | Contactor con disparo automático | S00285 | unverified | Q | `sym_contactor_auto_trip` |
| Timer relay coil, on-delay | Bobina de temporizador (retardo) | not_found | not_found | K (suffix T) | `sym_timer_coil_on_delay` |
| Selector switch (multi-position) | Selector multiposición | not_found | not_found | S | `sym_selector_switch` |
| Signal lamp, general | Lámpara de señalización | not_found | not_found | H | `sym_lamp_signal_general` |
| PLC input/output module | Módulo E/S de PLC | not_found | not_found | A | `sym_plc_io` |
| Terminal block (terminal point) | Borne | not_found | not_found | X | `sym_terminal_block` |
| Percentage differential current (relay characteristic) | Corriente diferencial porcentual | S00332 | unverified | K | `sym_differential_current_relay` |
| Static switch, general | Interruptor estático, general | S00376 | unverified | Q | (listed; no separate record) |
| Thermal switch, break contact | Interruptor térmico, contacto NC | S00265 | unverified | F | `sym_thermal_switch_break` (power file) |
| Spot light | Foco | S00488 | unverified | H | not used (see note on lamps) |

## Contacts: how to draw

- **NO (make) contact**: two terminals, blade open at about 30 degrees; closes when the parent device operates. Carries the parent's designation (for example KM1 contact 13-14).
- **NC (break) contact**: blade drawn closed (bar across the gap) in the unoperated state. Opens when the parent operates.
- **Timed contacts**: the same contact symbols plus a delay mark (an arc or a clock mark) next to the blade. S00243 is "delayed closing" (on-delay). S00245 is "delayed opening" (off-delay). S00247 is titled only "Make contact, delayed", so check the print before drawing it as on-delay.
- **Positive opening**: a bar across the blade indicates positively opening contacts. This is shown as the `sym_contact_break_general` with the note in the layout standard (typical).

## Pushbuttons and switches

- **Pushbutton (S00475)**: contact plus an actuator bar. Momentary; the NO or NC type is shown on the contact.
- **Emergency stop (S00258)**: mushroom head on the contact block, latching. Drawn as the switch with a bar on top to show the actuator.
- **Manual switch (S00253)**: the general switch symbol, two terminals, blade inclined.
- **Switch with signal lamp (S00467)**: an installation-diagram symbol (circle with a bar), not for control logic.

## Coils and relay symbols

- Coil terminals on IEC diagrams are `A1` and `A2`. Source note: the article on IEC 81346 lists relays as K (K1, K2) and contactors as Q (Q11 onward in some schemes). These are the common conventions; they are not a universal rule.
- The IEC database ID S00315 is titled "Relay coil of a relay unaffected by alternating current". It is not the general relay coil symbol. The general relay coil was not found, so `sym_relay_coil_general` is `not_found` (typical rectangle geometry).
- Timers: IEC 81346 uses a suffix (K1T for timing, K1R for reversing) according to the article. The timer coil symbol was not found; drawn as a rectangle with "t".

## Signal lamps

The S00488 entry is titled "Spot light", which is not the same as a pilot lamp. The general signal lamp was not located, so `sym_lamp_signal_general` is `not_found` and drawn as a circle with a cross (typical).

## PLC I/O

No IEC 60617 ID was found for PLC input/output modules. Draw as a labelled block with input and output channels (typical). The letter A (assemblies/controllers) is `typical` in IEC 81346 usage.

## Terminal blocks

The terminal point symbol (small circle with a leader) is typical. The IEC ID was not located. Terminal numbering rules are in `reference_designations_and_terminals.md`.

## Limits of this file

- Only two symbols (S00475 pushbutton and S00258 emergency stop) were checked against the library titles; their geometry is typical.
- Several general control symbols (coil, lamp, selector, PLC, terminal) are `not_found`. They should be replaced by the verified IEC entries once they are read from the database.
