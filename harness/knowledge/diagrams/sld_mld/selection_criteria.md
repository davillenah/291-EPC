# Selection criteria: LV and MV protection and switching

Cross-cutting criteria for choosing devices. Each rule has a machine-readable form in `decision_rules.json` (24 rules). Status vocabulary in `sld_mld_conventions.md`. Facts only, sourced on 2026-11-20. Nothing is verified.

## 1. Choosing a breaker family (LV)

| Criterion | MCB | MCCB | ACB |
|---|---|---|---|
| Rated current | up to 125 A | 16 to 1600 A | above 1600 A to 6300 A+ |
| Breaking capacity | Icn (not found in sources) | Icu 25-150 kA (by frame, conflict noted) | not found |
| Service breaking | not found | Ics = 25/50/75/100 % of Icu | not found |
| Typical place | final circuits | feeders, sub-boards, incomers | main incomer of large TGBT |

Rules (decision_rules.json, r01 to r03):
- Rated current up to 125 A with general load: MCB, check Icn against the prospective fault.
- Above 125 A up to 1600 A: MCCB.
- Above 1600 A: ACB.

The fault condition is always checked against Icn or Icu. Prospective fault calculation is not part of this research (`typical`).

## 2. Curve selection (MCB)

| Curve | Instantaneous band (x In) | Typical load | Status |
|---|---|---|---|
| Z | 2-3 | Electronic loads with sensitive fault detection | pending review (band) |
| B | 3-5 | Resistive and lighting loads, low inrush | pending review (band) |
| C | 5-10 | General circuits, the default | pending review (band); default typical |
| K | 10-14 | Motors and transformers | pending review (band) |
| D | 10-20 | High starting current (motors, transformers) | pending review (band) |

Bands are quoted from ABB (`abb_mcb_curves`), which cites the standard (IEC 60898-1). Use the catalogue of the chosen device.

## 3. Residual current protection

### 3.1 Sensitivity by purpose

| IΔn | Purpose (cited) | Status |
|---|---|---|
| 30 mA | Additional protection against direct contact (sockets up to 20 A, lighting, portable outdoor up to 32 A, wet areas, EV charging points, construction sites) | pending review |
| 300 mA or less | Fire protection in high-risk premises (IEC 60364-4-42 as cited) | pending review |
| 100 to 3000 mA | Indirect-contact protection; range depends on earthing system | unverified |

### 3.2 RCD type by load waveform

| Load | Type | Status |
|---|---|---|
| Resistive, lighting, heaters, simple Class II | AC | unverified |
| Rectifier loads (induction hobs, washing machines, single-phase UPS) | A | unverified |
| Single-phase variable speed drives (air-conditioning, heat pumps) | F | unverified |
| Three-phase VFD, three-phase EV charger, UPS with DC leakage, medical DC | B | unverified |

Rule: where DC leakage is possible, type B is required. A 400 Hz network does not use the AC type.

### 3.3 RCBO

Use where one final circuit needs both overcurrent and RCD in one module (`typical`). Ratings not found.

## 4. Fuses

| Need | Device | Status |
|---|---|---|
| Cable or feeder with overload and short-circuit | gG | unverified |
| Motor branch, short-circuit only, overload device present | aM | unverified |
| PV string DC | gPV (DC rated) | unverified |

Do not replace gG by aM where cable overload protection is needed (`viox_fuse`).

## 5. Motor circuits

| Duty | Device set | Status |
|---|---|---|
| Start and stop | Contactor AC-3 + thermal overload relay set to nameplate FLC | unverified |
| Inching, plugging, reversing | Contactor AC-4 | unverified |
| Overload and short-circuit in one device | MPCB | unverified |
| Short-circuit only | aM fuse + thermal overload relay | unverified |

Start from current, not kW (`viox_motor`). Starting current is roughly 5-8 x FLC direct-on-line, so instantaneous settings must allow the start.

## 6. Surge protection

| Location | Device | Status |
|---|---|---|
| Building with lightning protection system, service entrance | Type 1 (Iimp, 10/350 us) | pending review |
| Each LV switchboard | Type 2 (In >= 5 kA, 8/20 us) | pending review |
| Near sensitive loads, after type 2 | Type 3 | unverified (test) |

Uc and Up values (for the system voltage and load withstand) were not fetched. They are chosen per project: Uc from system voltage and earthing, Up below the load withstand (`ei_spd`).

## 7. Switching and transfer

| Need | Device | Status |
|---|---|---|
| Isolation for maintenance | Switch-disconnector | typical (no rating found) |
| Generator backup with automatic transfer | ATS (open, closed or delayed) | unverified |
| Inductive loads sensitive to surge | ATS in delayed transition | unverified |
| Critical load, no interruption | ATS closed transition, where a sync is acceptable | unverified (Kohler) |

## 8. MV selection

| Need | Device | Status |
|---|---|---|
| Switch cable on ring, no fault breaking | C module | unverified |
| Fault breaking on feeder or transformer | V module | unverified |
| Transformer protected by fuse-links only | F module (200 A, fuse 125 A at 12 kV or 63 A at 24 kV) | unverified |
| Relay-protected breaker feeder | CB module (relay required) | unverified |

Relay selection by ANSI number is in `mv_switchgear_and_relays.md`.

## 9. What is not in these criteria

- Selectivity and filiation (back-up) between devices: not fetched. Use manufacturer coordination tables (`typical`).
- Prospective short-circuit calculation and cable sizing: outside this research (AEA 90364 / IEC 60364 workflow).
- Icn values for MCB, RCBO ratings, NH fuse currents and most MV relay setting ranges: not_found.

## 10. Sources

- `abb_mcb_curves`, `abb_rccb_faq`, `schneider_rcd`, `ei_rcd`, `ei_spd`: see `lv_protection_devices.md` section 8.
- `viox_breaker_sizes`, `viox_fuse`, `viox_motor`, `kohler_ats`: see `lv_protection_devices.md` section 8.
- `abb_safering_cat`, `abb_safering_doc`, `control_ansi`: see `mv_switchgear_and_relays.md` section 7.
