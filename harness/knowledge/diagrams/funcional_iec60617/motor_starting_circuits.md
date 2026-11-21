# Motor starting circuits (power and control)

Status tags: `unverified` = supported by a cited public source; `typical` = generic practice, no source; `not_found` = not located. Nothing is `verified`.

Machine-readable records: `circuits/circ_*.json` (one per circuit), index `circuits_index.json`. Symbols use the IDs in `symbols/`.

| Circuit | ID | Status |
|---|---|---|
| Direct-on-line (DOL), one direction | `circ_direct_on_line_starter` | typical |
| DOL reversing | `circ_reversing_direct_on_line` | unverified |
| Star-delta (wye-delta) | `circ_star_delta_starter` | unverified |
| Autotransformer (compensator) | `circ_autotransformer_starter` | typical |
| Soft starter with bypass | `circ_soft_starter` | typical |
| Variable frequency drive | `circ_vfd_drive` | typical |
| Dahlander two-speed | `circ_dahlander_two_speed` | unverified |
| Rotor resistance (wound rotor) | `circ_rotor_resistance_starter` | typical |

## 1. Direct-on-line (DOL)

- **Components**: Q1 breaker (or fuses), KM1 contactor (3 poles + coil), F2 thermal overload (NC 95-96), M1 motor, S1 stop (NC), S2 start (NO), KM1 13-14 self-holding, F3 control fuse.
- **Power**: L1, L2, L3 to Q1, to KM1 (1, 3, 5 in; 2, 4, 6 out), overload heaters in series, motor U, V, W. Terminal numbers `typical`.
- **Control rungs**: (1) control supply through F3; (2) S1 NC in series with F2 95-96 NC, S2 NO in parallel with KM1 13-14; (3) KM1 coil A1-A2.
- **Interlocks**: none beyond the holding contact.
- **Protections**: Q1 short-circuit, F2 overload, F3 control fuse. Stop as NC for fail-safe.
- **Sequence**: start, KM1 pulls in, holds, motor at full voltage. Stop or overload trip releases KM1.
- **Common errors**: holding contact on the wrong terminals (start works only while pressed); overload contact wired NO; overload heater sized below the motor full-load current.
- **Range**: small to medium motors where the supply accepts full-voltage starting current.
- **MLD**: one line per pole with the motor symbol; **functional**: ladder rungs. `typical`.

## 2. Reversing direct-on-line

- **Components**: KM1 (forward), KM2 (reverse, phases interchanged), both with coils; NC interlocks of each in the other's rung; F2 overload; S1 stop, S2 forward, S3 reverse; Q1.
- **Power**: KM1 feeds U, V, W in phase order. KM2 feeds the motor with two phases swapped. The ABB technical document (reversing contactors, open type, pp. 3/1 to 3/6) shows the reverse contactor with an L2/L3 interchange at its labelled terminals (KM1 at 5/L3, KM2 at 3/L2). Check the marking on the actual product before drawing. `unverified`.
- **Control rungs**: forward rung: S2 NO in series with KM2 NC (21-22), F2 95-96, S1 NC; KM1 coil. Reverse rung: S3 NO with KM1 NC (21-22); KM2 coil. Self-holding via KM1 13-14 and KM2 13-14. `unverified`.
- **Interlocks**: electrical (NC of each in the other rung) and mechanical (kit that prevents both closing). The ABB document lists VM 5-1 (VOA) and VE 5-2 (VNA) devices and their N.C. contacts (VE 5-1 for A 9 to A 40; VE 5-2 for A 95 and A 110). `unverified`.
- **Sequence**: forward; stop; reverse. Direct reversal without stop is blocked by the interlock.
- **Common errors**: no electrical NC interlock (both coils energize with a faulty selector); interlock on NO instead of NC; no phase interchange in the reverse contactor.
- **Range**: conveyors, hoists, any motor needing reversal without speed change.

## 3. Star-delta (wye-delta), open transition with timer

- **Components**: KM1 (main), KM2 (star), KM3 (delta), KT1 (timer, on-delay), F2 overload, Q1, S1 stop, S2 start, M1 six-terminal motor.
- **Power**: KM1 line to motor. KM2 joins the motor ends W2, U2, V2 (star point). KM3 connects U1-W2, V1-U2, W1-V2 (delta). Motor windings must be delta at line voltage. `unverified` (Industrial Monitor Direct article; Schneider TeSys Tera user guide).
- **Control rungs**: start rung with KM1 and KM2 coils; KM2 NC in the KM3 rung and KM3 NC in the KM2 rung; KT1 timer opens the star rung after Delay 1 and a short changeover delay closes KM3. KM1 holds through 13-14 across S2. `unverified`.
- **Timer values**: Schneider TeSys Tera example default Delay 1 = 10.00 s (star time), Delay 2 = 0.30 s (changeover), adjustable 0.01 to 600.00 s each. The article suggests 5 to 15 s depending on load inertia. Both are data points, not a rule.
- **Interlocks**: mechanical and electrical between KM2 and KM3. The star and delta contactors must never close together; closing both short-circuits two phases (article).
- **Common errors**: interlock missing (fuses blow); motor terminals misidentified (poor running in star, excess delta current); star time too short (high transition current) or too long (overheating); PLC output too weak for contactor coils (use interposing relays for larger contactors). `unverified`.
- **Range**: motors with six accessible terminals and delta at line voltage. Not for motors without a delta connection.
- **Note**: the TeSys Tera page does not say whether star and delta are prevented from closing together; the interlock requirement above comes from the article only.

## 4. Autotransformer (compensator), closed or open transition

- **Components**: KM1 (line), KM2 (start, autotransformer in circuit), KM3 (run, bypass), TA1 autotransformer with taps, KT1 start timer, F2, M1.
- **Power**: line through KM2 into the autotransformer tap, output to the motor; KM3 bypasses the autotransformer in run. Taps 50 %, 65 %, 80 % are typical values.
- **Control rungs**: start energizes KM1 and KM2; KT1 opens KM2 and closes KM3 after the start time. Closed-transition variants close KM3 before opening KM2 (design dependent). `typical`.
- **Interlocks**: KM2 and KM3 interlocked.
- **Protections**: thermal overload and short-circuit on line.
- **Common errors**: wrong tap; open-transition current spike; autotransformer undersized for starting duty.
- **Range**: medium to large motors needing more starting torque than star-delta at reduced current.

## 5. Soft starter with bypass contactor

- **Components**: Q1 breaker, soft starter (controller and thyristor stage), KM1 bypass contactor, M1.
- **Power**: line into the soft starter; output to the motor; KM1 closes after the ramp and bypasses the semiconductors. `typical`.
- **Control**: start command enables the soft starter; the soft starter's run relay energizes KM1 at the end of the ramp. `typical`.
- **Interlocks**: the soft starter output must not be energized while bypass is closed (manufacturer rule, typical).
- **Protections**: motor overload by the starter's motor model or an external relay; short-circuit by the breaker.
- **Common errors**: bypass closed before the ramp ends (current spike); starter sized for the wrong motor rating.
- **Range**: pumps, fans, conveyors.

## 6. Variable frequency drive (VFD)

- **Components**: Q1 input breaker, KM1 line contactor, drive (rectifier, DC link, inverter), M1 motor, S1 stop and enable.
- **Power**: line into the drive input through Q1 and KM1; drive output U, V, W to the motor; shielded motor cable per EMC practice. `typical`.
- **Control**: run enable with safety input (STO) and start command to the drive digital inputs; KM1 coil driven by the drive relay or PLC output after enable. `typical`.
- **Interlocks**: drive output not connected to the motor while the line contactor is open (design-dependent).
- **Protections**: drive motor-overload function; input short-circuit protection; STO as a safety function (IEC 61800-5-2 is cited as typical; not read).
- **Common errors**: line contactor switched frequently (damages the input stage); STO and enable wired incorrectly.
- **Range**: pumps, fans, conveyors, process control.

## 7. Dahlander two-speed (one direction)

- **Components**: KM1 (low speed), KM2 (high speed, double star), KM3 (star point for high speed), F2 overload, M1 Dahlander motor, S1 stop, S2 low, S3 high.
- **Power**: low speed = delta-based pole configuration. High speed = double star with the star point closed. `unverified` (electricaltechnology.org).
- **Control rungs**: low rung with KM1; high rung with KM3 (star) energizing only when KM1 NC is closed; KM2 energizes after KM3 NO closes. `unverified`.
- **Interlocks**: low and high speed never together; KM1 NC in the KM3 path; KM3 NO in the KM2 path. `unverified`.
- **Sequence**: low speed (KM1). Change to high speed: KM1 drops, KM3 star closes first, then KM2; the motor runs at high speed with fewer poles. `unverified`.
- **Common errors**: low and high speed energized together (short circuit); wrong sequence (KM2 before KM3).
- **Mapping caveat**: the electricaltechnology source lists K1/K2 (low, forward/reverse) and K3/K4/K5 (high) for a reversing version. The mapping of contactors to delta and double-star windings was not confirmed by the sources read. The KM names in the record are the author's choice.
- **Range**: fans, pumps, machine tools, mixers with 2:1 speed ratio.

## 8. Rotor resistance (wound rotor, slip rings)

- **Components**: KM1 (line to stator), KM2 and KM3 (short-circuit contactors for resistor stages), KT1 and KT2 (stage timers), resistor bank, M1 wound-rotor motor.
- **Power**: line to stator; slip rings to resistor bank; stages shorted in order. `typical`.
- **Sequence**: start with full resistance; timed shorting of stage 1 (KM2), then stage 2 (KM3); the rotor is shorted at full run. `typical`.
- **Interlocks**: stage contactors in order.
- **Common errors**: stages shorted too early (current spike); resistor bank overheats with repeated starts.
- **Range**: cranes, hoists, high-inertia loads.

## Not found or open

- The IEC 60617 ID for a general resistor bank and for a rotor resistor symbol were not located; the rotor resistor record is used only as a component reference (`symbol_id: null`).
- Soft starter, VFD and autotransformer circuits have no cited source in this research: their status is `typical`.
- Power numbering of Dahlander contactors (which contactor drives which winding) was not confirmed.
