# IEC 60617 power symbols (BT and MT): drawing guide

Status tags: `unverified` = taken from a cited public source (IEC library page or a manufacturer/secondary article), not checked against the printed standard. `typical` = generic practice, no source. `not_found` = no verifiable ID or data located. Nothing here is `verified`.

Machine-readable records: `symbols/*.json`, index in `symbols_index.json`. IDs below are the IEC 60617 database identifiers (S + 5 digits) read from `library.iec.ch` (accessed 2026-11-20).

Geometry is given as simple primitives on a grid (1 unit = one symbol grid step, origin top-left, y down). Scale to the drawing standard in use. Primitives are the author's own description, not copied from the standard.

## Table of power symbols

| Symbol (en) | Symbol (es) | IEC 60617 ID | Status | Letter (IEC 81346) | Record |
|---|---|---|---|---|---|
| Contactor main pole (power contact) | Polo principal de contactor | S00286 | unverified (see note) | Q | `sym_contact_main_pole` |
| Disconnector (isolator) | Seccionador | S00288 | unverified | Q | `sym_disconnector` |
| Static (semiconductor) contactor | Contactor estático | S00377 | unverified | Q | `sym_static_contactor` |
| Circuit breaker function | Función de interruptor | S00219 | unverified | Q | `sym_circuit_breaker_function` |
| Circuit breaker, device symbol | Interruptor automático (aparato) | not_found | not_found | Q | `sym_circuit_breaker_device` |
| Miniature circuit breaker (MCB) | Interruptor miniatura (PIA) | not_found | not_found | F | `sym_mcb_miniature` |
| Residual current device (RCD) | Interruptor diferencial | not_found | not_found | F | `sym_rcd_residual_current` |
| Surge protective device (SPD) | Protector contra sobretensiones (DPS) | not_found | not_found | F | `sym_surge_arrester_spd` |
| Fuse, general | Fusible, general | S00362 | unverified | F | `sym_fuse_general` |
| Fuse with alarm contact | Fusible con contacto de alarma | S00365 | unverified | F | `sym_fuse_with_alarm_contact` |
| Static thermal overload relay | Relé térmico estático | S00381 | unverified | F | `sym_thermal_overload_static` |
| Thermal switch, break contact | Interruptor térmico, contacto de apertura | S00265 | unverified | F | `sym_thermal_switch_break` |
| Induction motor, three-phase, squirrel cage | Motor trifásico de jaula | S00836 | unverified | M | `sym_motor_3ph_squirrel` |
| Transformer, two windings, general | Transformador de dos devanados | S00841 | unverified | T | `sym_transformer_2w` |
| Current transformer, two secondaries, one core | TC con dos secundarios, un núcleo | S00882 | unverified | T | `sym_current_transformer_2sec` |
| Static generator, general | Generador estático, general | S00899 | unverified | G | `sym_generator_static` |
| Rotating generator | Generador rotativo | not_found | not_found | G | `sym_generator_rotating` |
| Protective earthing | Puesta a tierra de protección | S00202 | unverified | not_found | `sym_protective_earth` |

## Symbol notes and geometry

1. **Contactor main pole (S00286).** The IEC page title is "Contactor; Main break contact of a contactor". Its remark says "Contact closed in the unoperated position". A power pole of a contactor is normally open when de-energized. This is a discrepancy between the database remark and the usual reading. Check the printed symbol before drawing. Geometry in the record: two terminals, a blade inclined from the upper terminal, and a pivot mark. Status `unverified`.
2. **Disconnector (S00288).** Blade open at an angle, with a pivot dot. No load-breaking function in the symbol itself; the device type is given in the name.
3. **Static contactor (S00377).** Rectangle (solid-state block) between line and load; geometry is typical.
4. **Circuit breaker function (S00219).** IEC title is a function symbol. Use it to mark the breaking function on a device symbol. The device symbol (blade with release) was not found as an ID, so `sym_circuit_breaker_device` is `not_found` with a typical geometry.
5. **MCB, RCD, SPD, generator rotating, breaker device.** No IEC 60617 ID located in this research. Drawn with typical geometry only. The identifier S00332 found in searches is "Percentage differential current" (a relay characteristic), not an RCD symbol; it is recorded as `sym_differential_current_relay` in the control/protection file.
6. **Fuse (S00362).** Rectangle on a conductor, two terminals. Fuse with alarm contact (S00365): add a small auxiliary contact on the side.
7. **Static thermal overload relay (S00381).** Rectangle with a zigzag heater (bimetal or electronic). Trip contact is a separate symbol.
8. **Motor (S00836).** Circle with the letter M and three supply leads. The source gives the title "Induction motor, three-phase, squirrel cage". Terminal labels (U, V, W) are typical marking.
9. **Transformer (S00841).** Two coupled circles (primary above, secondary below). Terminal names in typical IEC practice (1U/2U, 1V/2V); not sourced.
10. **Current transformer (S00882).** Ring core with two secondary windings on one core (title from source).
11. **Protective earth (S00202).** Vertical lead with three hatch lines. The general earth symbol is S00200 (title "Earth, general symbol") and was not drawn separately.

## Letter designations used with these symbols

The source article (see `reference_designations_and_terminals.md`) lists: Q for switching devices (power contactors, breakers, motor starters); F for direct self-acting protection (fuses, miniature breakers, thermal overload releases); M as a motor suffix; T as a timing suffix. K is for signal-processing devices (relays, time relays). Classes G, T (for transformers/CT) and M (for drives) are `typical` IEC 81346 usage and are not confirmed by the sources read.

## Connection points

Use the connection points in each record (`connection_points`) to place terminals. For power poles, line side is top and load side is bottom. For a transformer, primary is the upper winding. These are drawing conventions (`typical`).

## Not found or open

- No IEC ID located for: circuit breaker device, MCB, RCD, SPD, rotating generator, general terminal, PLC I/O. Their records are `not_found`.
- The "make contact, delayed" entry (S00247) has a title that does not state whether the delay is on closing or opening. See the control file for the on-delay and off-delay variants.
- Old database references like 06-06-03 (seen on a database page for a series motor) were not used here because no current ID was tied to them.
