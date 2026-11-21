# Typical control circuits (mando): emergency stop, self-holding, timers, level control, ATS

Status tags: `unverified` = supported by a cited public source; `typical` = generic practice, no source; `not_found` = not located. Nothing is `verified`.

Machine-readable records: `circuits/circ_*.json`. Index: `circuits_index.json`.

| Circuit | ID | Status |
|---|---|---|
| Emergency stop (latching, NC loop, reset) | `circ_emergency_stop_safe_stop` | typical |
| Start-stop with self-holding (memory) | `circ_start_stop_self_holding` | typical |
| On-delay timer control | `circ_on_delay_timer` | typical |
| Tank level control, two alternating pumps | `circ_level_control_alternating_pumps` | typical |
| ATS mains to generator (transfer) | `circ_ats_mains_generator` | unverified (in `circuits/`, category transfer) |

## 1. Emergency stop

- **Components**: S0 mushroom E-stop (latching, NC contacts, two blocks for redundancy), reset pushbutton S4 (NO), optional safety relay KA1 for categories 3 or 4.
- **Rungs**: E-stop NC contacts in series with every start rung. Reset NO energizes the safety relay or contactor only after the E-stop is released.
- **Protection**: loop monitoring (a broken wire gives stop); no automatic restart after release.
- **Sequence**: press E-stop (NC open; power contactors drop); release; press reset; normal start command required.
- **Common errors**: E-stop used as normal stop; missing reset, so the machine restarts on release.
- **Note**: stop categories and safety levels depend on the machine standard, not covered here.

## 2. Start-stop with self-holding

- **Components**: S1 stop (NC), S2 start (NO), KM1 holding contact 13-14, KM1 coil.
- **Rungs**: S1 and S2 in series with the coil; S2 in parallel with KM1 13-14.
- **Sequence**: press start, coil energizes and holds; press stop, coil drops.
- **Common errors**: holding contact on the wrong terminals; stop as NO.

## 3. On-delay timer (retardo a la conexión)

- **Components**: S2 start (NO), K1T on-delay timer coil, K1T delayed make contact (15-18), KM1 load coil.
- **Rungs**: S2 energizes K1T; K1T delayed contact energizes KM1 after the set time.
- **Symbol note**: delayed make contact = `sym_contact_make_delayed_closing` (IEC 60617 S00243, unverified). The off-delay contact (S00245) is the reverse behavior.
- **Sequence**: energize; after delay the load starts.
- **Common errors**: timer not reset when released; delay repeats incorrectly.

## 4. Tank level control with two alternating pumps

- **Components**: LS1 low-level float (stop), LS2 high-level float (start duty pump), LS3 high-high float (start standby), KM1 and KM2 pump contactors, K1 and K2 alternation relays, M1 and M2 pumps, F2 and F3 overloads, S5 selector (Hand/Off/Auto) per pump.
- **Rungs**: floats select duty and standby; alternation relay swaps duty pump each cycle; overload and selector in series with each pump coil.
- **Interlocks**: each pump's start rung uses the other's NC, preventing double start on the same signal (typical).
- **Sequence**: high level starts duty pump; low level stops it; next cycle the other pump is duty. If the duty pump fails, standby starts.
- **Common errors**: floats without hysteresis (short cycling); both pumps set as duty.
- **Symbols**: float switches use the letter B (sensors, typical); their IEC symbols were not located (`not_found`).

## 5. Automatic transfer switch (ATS), mains to generator

Source: ABB automatic transfer switch white paper (ATS021 and ATS022). `unverified`.

- **Components**: Q1 normal switch, Q2 emergency switch (both with motor operators), ATS controller, generator G1, TS (transfer delay) timer, TGoff (generator stop delay) timer.
- **Power**: mains and generator into the two switches; both outputs into a common load bus. The ABB paper states that the breakers need a mechanical interlock so that the two sources cannot be paralleled (type C mechanical interlock for the bus-tie setup).
- **Control**: mains voltage monitoring; after TS, the ATS sends a generator start command. When the generator is up, the emergency switch closes. On mains return, the ATS retransfers and TGoff starts for generator stop.
- **Interlock**: mechanical between the switches. Electrical interlock with position feedback: switching is inhibited and an alarm sounds if a breaker position does not match the ATS command (ABB). The paper does not describe a separate electrical interlock scheme.
- **Protection**: each source has its own breaker; motor operators with key locks to block manual operation.
- **Transition**: with minimal delays, the paper cites about 2 s (ATS022) and 4.5 s (ATS021) break; shorter breaks need a UPS.
- **Neutral and supply**: three-phase with and without neutral, and single-phase, per the paper. The ATS021 needs an external isolation transformer (40 VA) when it is the only supply.
- **Common errors**: no mechanical interlock (sources paralleled); timers left at default (unnecessary transfers on short dips).

## Not found or open

- No cited source for E-stop, self-holding, on-delay or level-control circuits; their status is `typical`.
- Float switch symbols (level sensors) have no located IEC 60617 ID.
- The timer contact types (on-delay vs. off-delay) should be matched to the timer manufacturer's catalogue before drawing; not checked here.
