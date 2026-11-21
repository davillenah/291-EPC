# Inverter connection to the AC board, grounding and SPD

AC connection of three-phase and single-phase inverters to the board (breaker, disconnector, neutral, PE), plus structure bonding and surge protection. The fetched sources do not settle the neutral rule or the shutdown order; see the conflict notes.

Status key: unverified = cited public source; typical = generic practice without source; not_found = not located. Nothing is verified.
Spanish text for each item is in the `es` fields of the JSON records under `circuits/`.

## Three-phase inverter to AC board, with neutral and earth (`pv_inverter_three_phase_ac_to_board`)

Dedicated AC breaker per inverter in the main board, with L1 L2 L3 N PE connection and board earth bar.

- Diagram types: SLD, MLD
- Record status: unverified
- Symbols: sym_circuit_breaker_device, sym_disconnector, sym_protective_earth, sym_surge_arrester_spd, sym_terminal_block. Devices: mccb, pv_inverter_grid_tie, spd_type2, switch_disconnector.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| A1 | A | - | pv_inverter_grid_tie | Three-phase inverter, AC terminals L1 L2 L3 N PE per manufacturer. | typical |
| Q1 | Q | sym_circuit_breaker_device | mccb | AC breaker dedicated to the inverter, sized by the repository calculation engine. | typical |
| Q2 | Q | sym_disconnector | switch_disconnector | AC disconnector at the inverter or the board, lockable. | typical |
| F1 | F | sym_surge_arrester_spd | spd_type2 | AC SPD type 2 at the board. | typical |
| X1 | X | sym_protective_earth | - | Board PE bar, bonded to the inverter PE terminal and the structure equipotential bar. | typical |
| X2 | X | sym_terminal_block | - | Neutral bar (N) at the board. | typical |

**Application range**
- [typical] Three-phase grid-tie inverters, one dedicated breaker each. Neutral requirement depends on the inverter.

**Power connection**
- [typical] Phase cables L1, L2, L3 from inverter AC terminals to the line side of Q1, sized by the repository calculation (no value here).
- [not_found] Neutral: connect only when the inverter manual requires it. The fetched sources give no universal rule.
- [typical] PE from the inverter PE terminal to the board PE bar and to the structure equipotential bar.
- [typical] Inverter breaker is not shared with loads.

**Control and signal connection**
- none

**Protections**
- [typical] AC breaker and SPD sized per repository engine (no value here).
- [typical] Islanding and grid-fault protection is in pv_interface_protection_27_59_81.

**Sequence**
- [typical] Close the AC breaker with grid present and check phase sequence before enabling DC.
- [unverified] Shut down: the STRCOM manual says turn off the DC disconnect before the AC disconnect. (sources: solectria_strcom)

**Common errors**
- [typical] Wrong phase sequence or swapped L phases.
- [typical] Neutral missing where the inverter requires it.
- [typical] PE not bonded to the structure equipotential bar.

**Source conflicts**
- Shutdown order DC vs AC: STRCOM says open the DC disconnect first. Common inverter practice (typical) opens the AC side first. Follow the specific inverter manual. (sources: solectria_strcom)

**Sources**
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)
- solectria_strcom: Solectria STRCOM fused string combiner installation and operations manual - https://www.solectria.com/downloads/installation-operation-manuals/strcom-installation-and-operations-manual (manufacturer_doc, accessed 2026-11-20)

## Single-phase inverter to AC board (`pv_inverter_single_phase_ac_connection`)

Single-phase grid-tie inverter with L, N and PE to a dedicated breaker on the board.

- Diagram types: SLD, MLD
- Record status: typical
- Symbols: sym_circuit_breaker_device, sym_protective_earth. Devices: mcb.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| A1 | A | - | - | Single-phase inverter, AC terminals L, N, PE. | typical |
| Q1 | Q | sym_circuit_breaker_device | mcb | Single-pole or double-pole breaker dedicated to the inverter. | typical |
| X1 | X | sym_protective_earth | - | PE connection to the board bar. | typical |

**Application range**
- [not_found] Single-phase grid-tie inverters, residential and small commercial (typical). Specific limits not located.

**Power connection**
- [typical] Phase L and neutral N to the breaker; PE to the board PE bar.
- [typical] Do not place the inverter on the same phase as a large single-phase load without a load study (typical).

**Control and signal connection**
- none

**Protections**
- [typical] Dedicated breaker per inverter; sizing in the repository engine.
- [not_found] Check the inverter manual for neutral and PE requirements (not located here).

**Sequence**
- none

**Common errors**
- [typical] Phase and neutral mix-up on the AC side.

**Sources**
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)

## Grounding, equipotential bonding and surge protection (`pv_grounding_equipotential_spd`)

Structure bonding to a combiner earth bar and the inverter PE, with DC and AC SPD stages and an optional lightning rod.

- Diagram types: SLD, MLD
- Record status: unverified
- Symbols: sym_protective_earth, sym_surge_arrester_spd. Devices: spd_type1, spd_type2, spd_type3.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| X1 | X | sym_protective_earth | - | Structure earth bonding to the combiner ground bar and the board PE bar. | unverified |
| F1 | F | sym_surge_arrester_spd | spd_type2 | DC SPD type 2 at the combiner or the inverter DC input. | unverified |
| F2 | F | sym_surge_arrester_spd | spd_type1 | SPD type 1 at the service entrance (lightning current stage). | typical |
| F3 | F | sym_surge_arrester_spd | spd_type3 | SPD type 3 near sensitive equipment. | typical |
| A1 | A | - | - | Lightning rod and down conductor to the structure: not located in the sources. | not_found |

**Application range**
- [typical] Ground-mounted and roof arrays with a DC combiner and central or string inverters.

**Power connection**
- [unverified] Array frame and mounting structure connect to the combiner ground bar. (sources: solectria_strcom)
- [unverified] Negative DC terminal is grounded only by the inverter, per the STRCOM manual (the combiner does not ground it). (sources: solectria_strcom)
- [unverified] Grounding conductor sized per the standard in force; STRCOM cites UL 690.47 and NEC 250.166 (US references). (sources: solectria_strcom)
- [typical] Equipotential bonding of metal parts: typical practice, no numeric value here.

**Control and signal connection**
- none

**Protections**
- [not_found] Lightning protection standard (IEC 62305) values: not read in this research.

**Sequence**
- [typical] Bond the structure first, then the combiner earth bar, then the inverter PE. Check continuity.

**Common errors**
- [typical] Negative grounded at two points on a non-isolated system.
- [typical] No DC SPD on the array side.
- [typical] Paint or anodising left between structure and bonding point.

**Sources**
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)
- solectria_strcom: Solectria STRCOM fused string combiner installation and operations manual - https://www.solectria.com/downloads/installation-operation-manuals/strcom-installation-and-operations-manual (manufacturer_doc, accessed 2026-11-20)
