# PV string wiring and combiner boxes

DC side from module strings to combiner boxes and MPPT inputs. Main sources: ABB PANORAMA and Solectria STRCOM combiner manuals. MC4 polarity, cable length and section values are typical (no source) and must be checked against the module datasheet and local code.

Status key: unverified = cited public source; typical = generic practice without source; not_found = not located. Nothing is verified.
Spanish text for each item is in the `es` fields of the JSON records under `circuits/`.

## String combiner box, parallel strings with fused positives (`pv_string_combiner_parallel_fused`)

Strings with MC4 connectors run to a combiner box; each string has its own fuse and the outputs are paralleled on positive and negative bus bars.

- Diagram types: SLD, MLD
- Record status: unverified
- Symbols: sym_disconnector, sym_fuse_general, sym_surge_arrester_spd, sym_terminal_block. Devices: fuse_gpv, spd_type2, switch_disconnector.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| G1 | G | - | - | PV string: modules in series. Voc at the coldest expected temperature must stay under the inverter DC maximum. | typical |
| X1 | X | - | - | MC4 connector pair per string (positive and negative). No IEC symbol in the repository set. | not_found |
| F1-Fn | F | sym_fuse_general | fuse_gpv | String fuse gPV, one per string on the positive bus when strings are paralleled. ABB PANORAMA series: 15 A, 10x38 mm (1000 V) or 10x85 mm (1500 V). | unverified |
| Q1 | Q | sym_disconnector | switch_disconnector | DC string disconnector inside the string box. | unverified |
| F2 | F | sym_surge_arrester_spd | spd_type2 | DC SPD type 2, pluggable, in the combiner. | unverified |
| A1 | A | - | - | Combiner enclosure with positive and negative bus bars and an earth bar. | typical |
| X2 | X | sym_terminal_block | - | Output terminals: pipe or ring lugs, copper or aluminium. Inputs enter through M16 glands for 2.5 to 16 mm2 cable. | unverified |

**Application range**
- [unverified] Multi-string arrays with several strings per combiner box (typical). Single-string inputs may have no fuse. (sources: abb_panorama)

**Power connection**
- [unverified] Each string cable enters through a gland and terminates directly on its fuse holder. (sources: abb_panorama)
- [typical] Strings join the positive and negative bus bars; one output pair feeds one inverter DC or MPPT input.
- [unverified] One PV string per fuse position in the STRCOM range (4 to 30 positions). (sources: solectria_strcom)
- [typical] Positive and negative cables kept separate, double insulated. Typical string cable 4 to 6 mm2 (typical value; check module datasheet and local code).
- [typical] MC4 polarity: positive and negative are not interchangeable. Check polarity with a multimeter before mating.
- [not_found] Cable length and voltage-drop limits per string: not located in the fetched sources.

**Control and signal connection**
- none

**Protections**
- [unverified] String fuse rating typically at least 1.56 x short-circuit current (Isc) of the string; never above the module series-fuse rating on the module label. (sources: solectria_strcom)
- [unverified] DC SPD type 2 in the string box (pluggable, both ranges). Mounting position not specified. (sources: abb_panorama)
- [not_found] Parallel-string count above which string fuses become mandatory: not located (fetched pages show per-string protection without a threshold).
- [unverified] Enclosure: array frame and mounting structure grounds connect to the combiner ground bar. (sources: solectria_strcom)

**Sequence**
- [typical] Measure open-circuit voltage of each string before connecting it to the combiner.
- [typical] Install the fuses; check that the rating matches the string cable and module data.
- [typical] Close the DC disconnector only after the inverter DC input checks pass.

**Common errors**
- [typical] Reversed MC4 polarity on one string.
- [typical] Parallel string without its own fuse.
- [typical] Mixed string lengths or module models on one MPPT input.

**Sources**
- abb_panorama: ABB PANORAMA string combiners (1SLC009000B0202) - https://library.e.abb.com/public/94aed02352b6439b8a1dc44fb85e0fc1/1SLC009000B0202%20PANORAMA%20COMBINERS.pdf (manufacturer_doc, accessed 2026-11-20)
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)
- solectria_strcom: Solectria STRCOM fused string combiner installation and operations manual - https://www.solectria.com/downloads/installation-operation-manuals/strcom-installation-and-operations-manual (manufacturer_doc, accessed 2026-11-20)

## MPPT stringing diagram and array layout (`pv_mppt_stringing_and_layout`)

Assignment of strings to MPPT inputs and routing of string cables on roof or ground arrays.

- Diagram types: SLD, MLD
- Record status: typical
- Symbols: none. Devices: pv_inverter_grid_tie.

| Ref | Letter | Symbol | Device | Description | Status |
|---|---|---|---|---|---|
| A1 | A | - | pv_inverter_grid_tie | Grid-tie inverter with several MPPT inputs. Per-model MPPT count is in the repository inverter catalog (not re-read here). | typical |
| G1 | G | - | - | PV strings grouped per MPPT input, same orientation and tilt. | typical |

**Application range**
- [not_found] Any inverter with several MPPT inputs. Count and voltage window per model are not from a fetched datasheet.

**Power connection**
- [typical] All strings on one MPPT input share orientation, tilt and shading profile.
- [typical] Module count per string keeps the MPPT voltage inside the window at the lowest cell temperature and keeps Voc under the DC maximum at cold.
- [typical] Roof layout: strings run along module rows to a tray and then to the combiner.
- [typical] Ground layout: string cables run along the table ends in a trench or conduit to the combiner.

**Control and signal connection**
- none

**Protections**
- none

**Sequence**
- [typical] Compute Voc and Vmp per string for the site minimum and maximum temperatures.
- [typical] Assign strings to MPPT inputs, balancing string count and orientation.
- [typical] Route string homeruns to the combiner and mark each cable at both ends.

**Common errors**
- [typical] Mixed orientations on one MPPT input.
- [typical] String voltage outside the MPPT window at cold temperature.

**Sources**
- repo_devices: EPC-291 repository: sld_mld/devices and funcional_iec60617/symbols_index.json (ids reused) - repo://sld_mld/devices (internal_repo, accessed 2026-11-20)
