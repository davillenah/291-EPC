# Medium-voltage control schemes: contactor with protection relays

Status tags: `unverified` = supported by a cited source; `typical` = generic practice, no source; `not_found` = not located. Nothing is `verified`.

Machine-readable record: `circuits/circ_mv_contactor_protection_relays.json`.

## Scope

This file covers a MV contactor (or circuit breaker) controlled by a protection relay through a trip contact, with current transformers feeding the relay and a lock-out relay holding the trip. The MV switchgear itself, its arc-flash and insulation requirements, and the protection setting calculations are out of scope and not covered by the sources read.

## Symbols used

| Element | Symbol record | IEC 60617 ID | Status |
|---|---|---|---|
| Phase current transformers (2 CTs) | `sym_current_transformer_2sec` | S00882 | unverified |
| Residual / earth-fault CT | `sym_current_transformer_2sec` (or single-core CT) | S00882 | unverified (the symbol is for a two-secondary CT; a single-secondary residual CT is typical) |
| MV contactor with automatic tripping | `sym_contactor_auto_trip` | S00285 | unverified |
| Main contact (power pole) | `sym_contact_main_pole` | S00286 | unverified (see remark note) |
| Protection relay | `sym_relay_coil_general` | not_found | not_found |
| Lock-out relay (86-type) | `sym_relay_coil_general` | not_found | not_found |
| Differential relay characteristic | `sym_differential_current_relay` | S00332 | unverified |
| Reset pushbutton | `sym_pushbutton` | S00475 | unverified |
| Voltage transformer fuse | `sym_fuse_general` | S00362 | unverified |

Letters (IEC 81346-2, from the article): Q for the contactor or breaker; K for the protection and lock-out relays; F for fuses; S for the reset pushbutton; T for CTs and VTs (typical).

## Components

- **CT1, CT2** (phase CTs) feed the relay measurement inputs.
- **CT3** residual or earth-fault CT for earth-fault detection.
- **KM1** MV contactor with an automatic trip coil (the contactor drops out when the trip coil energizes).
- **K1** protection relay: phase overcurrent and earth fault; trip contact in the trip circuit.
- **K2** lock-out relay: latches on trip, keeps KM1 open until reset.
- **S1** reset pushbutton.
- **F1** fuse on any voltage transformer used for supervision or metering.

## Control rungs

1. K1 trip contact in series with the KM1 trip coil and the normally closed contact of K2 (`typical`).
2. K2 latches on trip. S1 reset releases K2 only after the fault is cleared (`typical`).

## Protections

- Phase overcurrent (instantaneous and time-delayed) from the phase CTs.
- Earth-fault from the residual CT.
- Thermal or motor protection, depending on the relay type.
- Trip circuit supervision (recommended, typical): a small current or voltage monitor detects an open trip coil.

## Interlocks

- Lock-out prevents re-closing until the reset and fault clearance. Typical.

## Sequence

1. Fault detected by K1 (current above setting, time delay expires).
2. K1 trip contact closes; the KM1 trip coil energizes; KM1 opens.
3. K2 latches; the trip cannot be cleared without the reset.
4. After inspection, reset with S1; re-closing is allowed only after reset and a normal close command.

## Common errors

- CT polarity reversed: wrong directional or differential response (typical).
- Trip coil not supervised: a trip circuit failure goes undetected (typical).
- Lock-out not wired: the relay resets after a transient fault and recloses automatically (typical).
- Residual CT wired as a phase CT (or the reverse): earth-fault pickup wrong (typical).

## Representation

- **MLD**: MV path with CTs on two phases and a residual CT; relays and trip circuit shown as blocks.
- **Functional**: trip contact of K1 in series with the KM1 trip coil; lock-out K2 in the same path; reset S1 across K2 coil. `typical`.

## Not found or open

- No IEC 60617 symbol ID was found for a general protection relay or a lock-out relay; those records are `not_found`.
- The MV circuit breaker device symbol (with the trip function) was not located; `sym_circuit_breaker_function` covers the function only.
- ANSI device numbers (50/51, 86) are mentioned as typical; the ANSI C37.2 numbering was not read.
- No MV scheme from a manufacturer document was read; the scheme above is `typical` except where a symbol carries an `unverified` ID.
