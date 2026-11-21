# LV protection and switching devices: applications and ranges

Research for the harness SLD/MLD generator. Facts only, sourced on 2026-11-20. Status vocabulary in `sld_mld_conventions.md`. Each device has a JSON record in `devices/<id>.json` with the full `selection_criteria`, `ratings_typical` and `sources`.

## 1. Summary table

| Device (JSON id) | Use | Main ratings found | Status |
|---|---|---|---|
| MCB (`mcb`) | Final and small feeder circuits | Rated current up to 125 A; trip bands B 3-5, C 5-10, D 10-20, K 10-14, Z 2-3 x In | unverified (range); pending review (bands) |
| MCCB (`mccb`) | Feeders and mains | 16-1600 A; Icu 25-150 kA (by frame); Ics 25/50/75/100 % of Icu | unverified (conflict on large-frame Icu, see note) |
| ACB (`acb`) | Main incomers above 1600 A | Above 1600 A up to 6300 A+ | unverified |
| RCCB (`rccb`) | Earth leakage, no overcurrent | IΔn 10/30/100/300/500/1000 mA | unverified; 30 mA and 300 mA rules pending review |
| RCBO (`rcbo`) | Circuit with RCD and overcurrent in one module | not found | not_found (ratings) |
| RCD type AC (`rcd_type_ac`) | Sinusoidal AC leakage only | Not for 400 Hz | unverified |
| RCD type A (`rcd_type_a`) | AC and pulsating DC (up to 6 mA DC) | Rectifier loads | unverified |
| RCD type F (`rcd_type_f`) | Single-phase drives, mixed frequency up to 1 kHz, pulsating DC up to 10 mA | Single-phase VFD, heat pumps | unverified |
| RCD type B (`rcd_type_b`) | Smooth DC leakage | Three-phase VFD, EV charger, UPS | unverified |
| gG fuse (`fuse_gg`) | Full-range cable and feeder protection | NH current ratings not found | not_found (ratings) |
| aM fuse (`fuse_am`) | Motor short-circuit only (needs overload device) | not found | not_found (ratings) |
| gPV fuse (`fuse_gpv`) | PV string DC protection (IEC 60269-6) | DC voltage and current not found | not_found |
| Switch-disconnector (`switch_disconnector`) | Isolation and load switching (IEC 60947-3) | Current not found | not_found (current) |
| Contactor (`contactor`) | Motor start/stop | AC-3 normal motor duty; AC-4 inching/plugging/reversing | unverified |
| MPCB (`mpcb`) | Motor overload and short-circuit in one device | Breaking capacity must be at least the prospective fault | unverified (criterion) |
| Thermal overload relay (`thermal_overload_relay`) | Sustained motor overload | Trip classes 10 / 20 / 30 | unverified; setting range not_found |
| ATS (`ats`) | Generator / utility transfer | 30-4000 A; open, closed, delayed transition | unverified |
| SPD type 1 (`spd_type1`) | Direct lightning (10/350 us) | Iimp 25 kA per pole (3P), 100 kA total 3P+N (IEC 62305 as cited) | pending review |
| SPD type 2 (`spd_type2`) | Induced and switching surges (8/20 us) | In minimum 5 kA, 19 times | pending review |
| SPD type 3 (`spd_type3`) | Point of use, low discharge | Uoc test wave; In not found | unverified / not_found |

## 2. Circuit breakers

### 2.1 MCB (miniature)

- Use for final circuits and small feeders up to 125 A. Source: `viox_breaker_sizes` (unverified).
- Curve selection by load (typical unless sourced):
  - B: 3-5 x In. Resistive or lighting loads with low inrush.
  - C: 5-10 x In. General circuits, the usual default.
  - D: 10-20 x In. High inrush (motors, transformers). Band sourced from ABB (`abb_mcb_curves`), quoted from the standard: pending review.
  - K: 10-14 x In. Motors and transformers.
  - Z: 2-3 x In. Electronic loads that need sensitive fault detection.
- Breaking capacity (Icn) of MCBs was not found in the fetched sources. Take it from the catalogue.
- Not for: rated current above 125 A (MCCB); fault current above Icn (MCCB or higher-capacity fuse).

### 2.2 MCCB and ACB

- MCCB standard rated currents: 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 320, 400, 500, 630, 800, 1000, 1250, 1600 A (`viox_breaker_sizes`, unverified).
- Icu by frame (guide, unverified): small 16-250 A, Icu 25-50 kA; medium 250-630 A, Icu 35-70 kA; large 630-1600 A, Icu 50-100 kA.
- **Conflict:** the same page gives 65-150 kA for the large frame and 85 kA for the 630 A row. Check the manufacturer catalogue before using any Icu value.
- Ics: 25 %, 50 %, 75 % or 100 % of Icu (unverified).
- ACB above 1600 A, up to 6300 A+ (unverified). Icu for ACB not found.

Rule of thumb: prospective short-circuit current at the point must not exceed Icu (MCCB) or Icn (MCB). This is a `typical` check, and the calculation is outside this research.

## 3. Residual current devices (RCD / RCCB / RCBO)

### 3.1 Sensitivity IΔn

| IΔn | Use (as cited) | Status |
|---|---|---|
| 10 mA | Niche applications only, risk of nuisance tripping (`ei_rcd`) | unverified |
| 30 mA | Direct-contact protection: sockets up to 20 A, lighting, portable outdoor appliances up to 32 A, areas near water (`ei_rcd`, `schneider_rcd`) | pending review (norm IEC 60364-4-41 quoted via wiki) |
| 100 mA | Medium sensitivity; selective (S) and time-delayed (R) versions exist | unverified |
| 300 mA | Fire protection, IEC 60364-4-42 cites 300 mA or less in high-risk premises (`ei_rcd`) | pending review |
| 500 mA, 1000 mA | Medium sensitivity options | unverified |
| 3000 mA | Upper bound for indirect contact, depending on earthing (`ei_rcd`) | unverified |

Notes:
- The ABB FAQ (`abb_rccb_faq`) states 30 mA for additional protection against direct contact and lists 300 mA and 500 mA in the test table. The Schneider and wiki sources give the application list above.
- The fetched sources do not give a complete per-type availability matrix (IΔn by type). Not found.

### 3.2 RCD type

| Type | Detects | Typical use | Status |
|---|---|---|---|
| AC | Sinusoidal AC residual current | Resistive, lighting, heaters, simple Class II. Not for 400 Hz | unverified |
| A | AC and pulsating DC residual current (up to 6 mA DC) | Single-phase rectifier loads: induction hobs, washing machines, tumble-dryers, single-phase UPS | unverified |
| F | AC with mixed frequencies up to 1 kHz; pulsating DC up to 10 mA | Single-phase variable speed drives (air-conditioning, heat pumps) | unverified |
| B | Smooth DC, plus AC and pulsating DC | Three-phase VFD, three-phase EV chargers, UPS with DC leakage, medical DC loads | unverified |
| B+ | Type B with high-frequency detection up to 20 kHz | Dedicated markets only (ABB) | unverified |

Decision: when a load can leak smooth DC, the type is B. The ABB FAQ also lists type A-APR (high immunity to nuisance tripping) and type F with 200 Hz, 300 Hz and 400 Hz variants for automotive, woodworking and aircraft use. These are niche and are not modelled as separate devices.

### 3.3 RCBO

- RCD and overcurrent in one module. Use for one final circuit that needs both protections in a small space. Typical (no ratings sourced).
- Ratings (rated current, IΔn) were not found in the fetched sources. Status `not_found`.

## 4. Fuses

### 4.1 gG and aM (IEC 60269)

| Type | Protects | Needs other device? | Source |
|---|---|---|---|
| gG | Overload and short-circuit, full range (cable and feeder) | No | `viox_fuse` (unverified) |
| aM | Short-circuit only, partial range (motor branch) | Yes: thermal overload or motor relay | `viox_fuse` (unverified) |
| gPV | Full range, DC PV strings and combiners (IEC 60269-6) | No | `viox_fuse` (unverified) |

- Replacing gG by aM can remove the cable overload protection. Not a direct swap (`viox_fuse`).
- NH current values were not in the fetched page (only application by size). Ratings: `not_found`.

## 5. Switching and motor protection

### 5.1 Switch-disconnector (IEC 60947-3)

- Isolates a circuit for maintenance and switches load within its utilization category. It does not replace a breaker for fault breaking (`typical`).
- Current rating not found in the fetched sources. Utilization categories AC-22 and AC-23 are `typical`.

### 5.2 Contactor, MPCB and overload relay (motor)

Source for this group: `viox_motor` (third-party guide, unverified).

- Start from current, not kW: I = P / (√3 × V × PF × η). Example in the guide: 7.5 kW at 400 V, PF 0.85, η 0.90 gives about 14.2 A. Confirm with the nameplate FLC.
- Contactor: choose by AC-3 for normal motor duty. AC-1 is not for motor duty. AC-4 for inching, plugging or reversing.
- Thermal overload relay: protects against sustained overload, set to the nameplate current. Trip classes 10, 20, 30; higher class for longer acceleration. No numeric adjustment range found (`not_found`).
- MPCB: overload and short-circuit in one device. A basic overload relay needs a separate short-circuit device.
- Breaking capacity must be at least the prospective short-circuit current (example in guide: a 6 kA device is unsuitable where 10 kA is available).
- Starting current, direct-on-line, is roughly 5-8 x FLC (`viox_motor`). Instantaneous settings must not be too low.
- Type 1 vs type 2 coordination is not covered by the guide. Do not claim it without manufacturer data for the exact combination.

### 5.3 ATS (transfer switch)

- Transition modes (Kohler brochure, unverified): open (break-before-make), closed (make-before-break, used for data centres and hospitals, falls back to open if a source cannot sync), delayed (pause in off position, for inductive loads).
- Ratings: 30 to 4000 A (Kohler, unverified). Standards in the brochure: UL 1008 (any-breaker withstand test), UL 489, NEC 2017. IEC standard references are not in the brochure: not_found.
- Applications: standard, bypass-isolation, service-entrance, load-shed, three-source systems.

## 6. Surge protection devices (IEC 61643-11, as cited)

| Type | Test wave | Key values | Use | Status |
|---|---|---|---|---|
| 1 | 10/350 us | Iimp: 25 kA per pole (3P) and 100 kA total for 3P+N, as cited from IEC 62305 | Buildings with lightning protection system or meshed cage | pending review |
| 2 | 8/20 us | In: minimum 5 kA, withstood at least 19 times; Imax | Main protection in each LV switchboard | pending review (5 kA, 19 times); Imax not_found |
| 3 | 1.2/50 us voltage, 8/20 us current | Uoc: open-circuit test voltage | Point of use, near sensitive loads, with type 2 upstream | unverified (test) / not_found (In) |

Voltage concepts: Uc (maximum continuous voltage, chosen by system voltage and earthing) and Up (protection level at In, must be below the load withstand). Values for Uc and Up were not fetched: `not_found`.

## 7. Notes and gaps

1. Breaking capacity of MCBs, RCBO ratings, NH fuse currents, switch-disconnector current and contactor current were not found. They are `not_found`.
2. Selectivity and filiation (back-up) between MCB/MCCB were not fetched (the wiki page returned an error). The harness must use manufacturer coordination tables. Status `typical` in the rules.
3. The MCCB Icu conflict (section 2.2) must be resolved from the catalogue.
4. Sources are guides and catalogues, not the standards themselves. Standard numbers are cited for reference only.

## 8. Sources

- `abb_mcb_curves`: ABB, What you need to know about MCB trip curves, https://library.e.abb.com/public/b5acf03b2a1f42e3b08ed2fc27672c30/What%20you%20need%20to%20know%20about%20MCB%20trip%20curves.pdf
- `abb_rccb_faq`: ABB, FAQ RCCBs, https://library.e.abb.com/public/8d7aeb25c10b4a839c43878fa9718de4/FAQ_RCCBs.pdf
- `schneider_rcd`: Schneider Electric, CA908066E, https://download.se.com/doc/CA908066E/CA908066E%20(web).pdf
- `ei_rcd`: electrical-installation.org, Protection of circuits by RCD, https://www.electrical-installation.org/enwiki/Protection_of_circuits_by_RCD
- `ei_spd`: electrical-installation.org, The Surge Protection Device (SPD), https://www.electrical-installation.org/enwiki/The_Surge_Protection_Device_(SPD)
- `viox_breaker_sizes`: VIOX, Standard breaker sizes, https://viox.com/standard-breaker-sizes/
- `viox_fuse`: VIOX, IEC 60269 fuse guide, https://viox.com/iec-60269-low-voltage-fuse-selection-guide-gg-am-nh/
- `viox_motor`: VIOX, Contactors and circuit breakers by motor power, https://viox.com/how-to-select-contactors-and-circuit-breakers-based-on-motor-power/
- `kohler_ats`: Kohler, ATS brochure, https://resources.kohler.com/power/kohler/industrial/pdf/ATS_Brochure.pdf
