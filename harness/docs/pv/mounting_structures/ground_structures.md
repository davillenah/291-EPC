# Ground-mount PV support structures: research notes

Status: research draft. Every value is `unverified`, `typical` or `not_found` (none is `verified`; only a person sets that). Machine-readable data: `harness/src/engines/calculation/pv/src/epc_pv/data/mounting_structures/ground/*.json` (schema `mounting_structure.schema.json`, `schema_version` 1.0). Research date: 2026-11-20. No PDF was stored; facts were extracted and cited by URL.

## 1. Families covered

| id (JSON file) | Family | Foundation | Layout | Main sources |
|---|---|---|---|---|
| `driven_pile_fixed_table` | Fixed tilt, multi-post | Rammed/driven galvanized posts, embedment 1500 mm | 2P10 reference, 20 modules, 12 posts, 6 beams, 8 purlins, 2 braces, tilt 20-30 deg | ProSolar 2P10; Sadef 2023 |
| `ramming_c_pile_fixed_table` | Fixed tilt, single post | Rammed post (generic C reference 114.3 x 193.7 mm, approximate; not confirmed for this product) | 2 modules portrait or 4 landscape, tilt 0-30 deg | ArcelorMittal fixed structure |
| `ramming_h_pile_fixed_table` | Fixed tilt | Rammed H pile (W6x9 reference from Gerdau; grade and length not stated) | Not stated | Gerdau solar posts; Sadef 2023 (generic) |
| `ground_micropile_fixed_table` | Fixed tilt, micropile | Micropile (section not stated) | 2 poles, 21 modules portrait, tilt 10-30 deg (discrete) | ProSolar 3P-7 micropile kit |
| `ground_vertical_bifacial_fence` | Vertical bifacial fence | Posts (section, length not stated) | 12 modules per table, 3 posts per table | Fence data sheet 2024 (ENFSolar copy) |
| `ground_screw_fixed_table` | Fixed tilt | Helical ground screw, 76 mm OD | Screw lengths 1.4-2.9 m | Terrasmart; BDI; American Ground Screw |
| `concrete_footing_fixed_table` | Fixed tilt | Concrete footing (zapata) or precast block | Not stated | ArcelorMittal; Sadef |
| `ballasted_ground_fixed_table` | Fixed tilt, no penetration | Precast concrete ballast | Portrait or landscape, tilt 5-40 deg | Terrasmart SS33 GLIDE; Schletter 2023 |
| `single_axis_tracker_torque_tube` | 1-axis tracker | Piles with torque tube bearings | 1P portrait per row, tilt +/-52 deg (+/-62 optional) | Array DuraTrack HZ v3; Nextracker NX Horizon |
| `carport_steel_s355` | Carport / pergola | Plate embedded in foundation | Column/beam system | Avrii SOL Integra |

Coverage is 8 types as requested, plus 2 added types (micropile fixed table, vertical bifacial fence). The C-pile section is only a generic approximate reference from an article; the H-pile uses a W6x9 wide-flange section from Gerdau. The actual product sections for both remain unconfirmed. East-west ground tables and floating structures were not added: no sourced data was found in this pass.

## 2. Comparison (sourced values only)

| Property | Driven fixed table | Ground screw | Ballast | Tracker | Carport |
|---|---|---|---|---|---|
| Steel grade | Not stated | ASTM A500 Gr C (Terrasmart), A500C 50 ksi (BDI), Q235B (American GS) | Not applicable (concrete, fibre mesh) | Not stated | S355 |
| Corrosion protection | HDG (EN ISO 1461 per Sadef minima: 85/70/55 um by thickness), or Z275, ZM310/ZM430 | HDG to ASTM A123 and ISO 1461 | Concrete | Pre-galv, HDG or aluminium | HDG + powder coat RAL 7016 |
| Tilt range | 20-30 deg (2P10); 0-30 deg (ArcelorMittal single post) | Not applicable | 5-40 deg | Not stated | Not stated |
| Wind basis | 40 m/s design wind (ArcelorMittal) | Not stated | 170 mph+ rating (Terrasmart) | 140 mph, 3-s gust, exposure C, ASCE 7-10 (Array); 240 km/h configurable (Nextracker) | Tests mentioned, values not stated |
| Snow basis | Not stated | Not stated | 90 psf+ rating (Terrasmart) | Not stated | Not stated |
| Foundation dimension | Embedment 1500 mm (2P10) | Length 1425-2900 mm (Terrasmart) | Not stated | Not stated | Not stated |

## 3. Materials and finishes by family

- **Driven and ramming posts**: structural steel, grade not stated in any source. Galvanizing per EN ISO 1461. Sadef gives minimum mean thickness for hot-dip galvanizing: 85 um (over 6 mm), 70 um (3-6 mm), 55 um (1.5-3 mm). Pre-galvanized coil per EN 10346: Z275 (19 um average), up to Z1200 on request; zinc-magnesium ZM310 (25 um) or ZM430 (35 um). Duplex systems (powder over galvanizing) are listed.
- **Module clamps**: aluminium. ArcelorMittal states AL 5754; 2P10 states anodized aluminium. Both are sourced; the alloy for 2P10 is not stated.
- **Ground screws**: round shafts of 76.2 mm (3 in) OD and 3.6-4.0 mm wall (Terrasmart 0.142 in = 3.61 mm; BDI 0.157 in = 4.0 mm; American GS minimum 0.148 in = 3.75 mm). Also a 114 mm (4.5 in) option (American GS).
- **Concrete ballast**: fibre mesh replaces rebar (Terrasmart claim, not verified). Concrete class not stated.
- **Trackers**: torque tube steel grade and section not stated by either manufacturer; dry slide bearings (Array); slew gear (Nextracker).
- **Carport**: S355 rectangular hollow sections, hot-dip galvanized then powder coated; stainless A2 fasteners.

## 4. Fasteners (bolts, nuts, washers, set screws)

| Item | Where sourced | Grade / standard | Size | Torque |
|---|---|---|---|---|
| Structural bolts (driven table) | 2P10 | Class 8.8, galvanized | Not stated | Not stated |
| Structural bolts (micropile kit) | ProSolar 3P-7 | Class 8.8, galvanized | Not stated | Not stated |
| Structural bolts (tracker) | Array / Nextracker | Not stated | Not stated | Not stated |
| Friction bolt (ground screw connection) | American GS | Class 4.8, DIN 933; ASTM A153 HDG | M16 x 30 | Snug-tight + 1/4 turn |
| Set screws (screw top connection) | Terrasmart | Not stated | 5/8-11, qty 3 | Not stated |
| Screw installation torque | American GS / BDI / Terrasmart | Not applicable | 76 mm and 114 mm shafts | 6547 N m (3 in); 9066 N m (4.5 in); BDI 5000 ft-lb (about 6779 N m, converted) |
| Stainless bolts, nuts and washers (Schletter 2023, mirror) | Schletter | A2, A2-70, A4 (various) | M6-M12; examples M8 x 55 DIN 912 A2, M10 x 25 A2 | Not stated |
| Carport fasteners | Avrii SOL | A2 (property class not stated) | M6x12, M6x16, M8x25, M10x110 threaded rod, M10 and M20 cap nuts with washers 10.5 and 21 mm | Not stated |
| Tracker structural bolts | Nextracker | Not stated ("engineered fastening system, vibration-proof") | Not stated | Not stated |

Standards for fasteners named in the research brief (ISO 4017, ISO 4032, ISO 7089/7090, ISO 898-1) are **not** cited by the sources reviewed. They are listed as references only and are not applied to any value.

Bolt torques for the IronRidge ground-mount pipe-pier system (installation manual v2.6, greentechrenewables.com copy) were reviewed: cap set screws 11-20 ft-lb, diagonal brace bolts 40 ft-lb, grounding lug 80 in-lb. They belong to a different system (pipe piers) and are not applied to any file above.

## 5. Connectors, clamps, brackets, caps, grounding, sealants

- **Clamps**: driven/ramming tables use aluminium mid and end clamps (quantities per module not stated). Trackers use single-fastener clamps with integrated grounding (Array). Schletter lists mid/end clamps for several rail families, mostly roof or laminate types, which are out of scope here.
- **Caps and plates**: post head caps, pile caps and anchor plates are named in the carport (pillar caps 160 x 80 and 100 x 40 mm) and screw tops (nut cage, Terrasmart, BDI). Other caps are not stated.
- **Grounding**: Array states integrated grounding in tracker clamps; Terrasmart ballast states integrated bonding through the raised purlin; Schletter lists a grounding and lightning clamp VA M8 (clamping range 8-10 mm, conductor 4-50 mm2, catalogue item 135003-002). No other bonding sizes are sourced.
- **Sealants and gaskets**: Schletter lists EPDM gaskets and tapes (mostly roof). Ground-mount sealants are not stated in any source; they are `not_found`.

## 6. Standards cited by the sources

- ISO 1461 (hot-dip galvanizing), cited by ArcelorMittal, Sadef, Terrasmart.
- ASTM A123 and ASTM A153, cited by Terrasmart, BDI and American GS.
- EN 10346 (continuous hot-dip coil), EN ISO 14713 (zinc coatings), ISO 12944-2 (corrosion categories), cited by Sadef.
- EN 1090-1 and ISO 3834:2021 (execution of steel structures and welding), cited by Sadef and Avrii.
- EN 1991-1-3 and EN 1991-1-4 (snow and wind actions), cited by Avrii.
- ASCE 7-10 (wind basis), cited by Array.
- UL 2703 (listing), cited by Terrasmart and Array (press release).
- IEC 62817 (design qualification of solar trackers), found in search results; the full text was not reviewed.
- ASTM C1884 (concrete ballast block), found in search results; not reviewed.

## 7. Sources (with URLs)

1. ProSolar Structures, Technical Data Sheet 2P10 Rammed: https://prosolarstructures.com/wp-content/uploads/Technical_Data_Sheet_2P10_Rammed.pdf
2. voestalpine Sadef, SOLAR 2023 brochure: https://www.voestalpine.com/sadef/en/content/download/24414/file/SOLAR-2023-BROCHURE-v7+cover.pdf
3. ArcelorMittal, Technical datasheet - Ground mounted fixed structure v2: https://projects.arcelormittal.com/cca/repo/Solar/Technical%20datasheet-Ground%20mounted%20fixed%20Structure%20v2.pdf
4. Terrasmart, Ground Screw Spec Sheet: https://www.terrasmart.com/wp-content/uploads/2026/04/Ground-Screw-Spec-Sheet.pdf
5. BDI BD-01-1001 ground screw (Solar-Electric listing): https://www.solar-electric.com/bid-bd-01-1001-60inch-ground-screw.html
6. American Ground Screw, Steel Ground Screw Systems specification (ARCAT): https://www.arcat.com/specification/american-ground-screw-inc-52607/31_66_00cgs
7. Schletter Component overview 2023 (mirror on bimblesolar.com): https://www.bimblesolar.com/docs/schletter-component-overview-2023-2.pdf
8. Terrasmart, SS33 GLIDE Ballast: https://www.terrasmart.com/wp-content/uploads/2021/12/SS33-GLIDE-Ballast.pdf
9. Array Technologies, DuraTrack HZ v3 specification sheet (copy in utility appendix): https://prod.aes.com/sites/vault/files/2025-04/Appendix%202-2.%20Array%20Technologies%20DuraTrack%C2%AE%20HZ%20v3%20Tracking%20System%20Specification%20Sheet.pdf
10. Nextracker, NX Horizon datasheet: https://info.nextracker.com/hubfs/2024%20Datasheets/nxt_NX_Horizon_Datasheet_090723.pdf
11. Avrii SOL Integra carport structure datasheet (EnFSolar): https://cdn.enfsolar.com/z/pp/2024/5/y22yooez233m4z/carport-avrii-sol-structure-datasheet.pdf
12. IEC 62817:2014 (catalogue entry, not reviewed in full): https://webstore.iec.ch/publication/7442
13. ProSolar Structures, 2P10 datasheet (tilt options, embedment 1500 mm, 6 beams, 8 purlins, 2 braces): https://prosolarstructures.com/wp-content/uploads/Technical_Data_Sheet_2P10_Rammed.pdf
14. Gerdau, Solar Posts Data Sheet (W-shape list, converted from inches): https://gsn.gerdau.com/sites/gsn_gerdau/files/downloadable_files/Gerdau-Solar-Posts-Data-Sheet.pdf
15. NA Clean Energy article, Driven Foundations for Trackers and Fixed Racks - W vs. C (generic C pile dimensions, approximate): https://www.nacleanenergy.com/solar/driven-foundations-for-trackers-and-fixed-racks-w-vs-c
16. ProSolar Structures, 3P-7 micropile kit page (tilt options, 21 modules, class 8.8): https://prosolarstructures.com/ground-mounted-solar-panel-kits-3p-7-micropiles
17. Fence data sheet 2024 (vertical bifacial fence; publisher not named in the document, copy on ENFSolar): https://cdn.enfsolar.com/z/pp/2025/4/pgfxjhg0az471a/fence-data-sheet-2024.pdf
18. IronRidge Ground Mount Installation Manual v2.6 (torques for a pipe-pier system, not applied to any file; copy on greentechrenewables.com): https://www.greentechrenewables.com/sites/default/files/inline-files/IronRidge_Ground_Mount_Installation_Manual.pdf

## 8. What remains unverified or not found

- **Profiles**: post, beam, purlin and torque-tube sections and dimensions are not stated for the driven, ballast and tracker families. Sourced dimensions now exist for the ground screw (76 mm OD), the carport (160 x 80 x 5 and 100 x 40 mm), the ballast rail lengths, the H-pile (W6x9, Gerdau) and an approximate generic C-pile (article).
- **Steel grades**: not stated for driven posts, purlins, bracing, H/C piles, trackers and ballast rails. Ground screw and carport grades are sourced (A500 C, Q235B, S355).
- **Bolts**: diameters, lengths and torques are mostly not stated. Grades are sourced for the ground screw friction bolt (M16, 4.8, DIN 933), the carport (A2) and the 2P10 and micropile structures (class 8.8). Only the ground screw and carport have sizes.
- **Quantities**: no source gives clamp, bracket or connector counts per module or table, except the 2P10 diagonal braces (2 per table), the 2P10 beam and purlin counts (6 and 8 per table, lengths not stated), the 2P10 and micropile post counts, the fence (3 posts per 12 modules) and the screw set screws (3 per screw). Every other quantity is a placeholder with `value: 0` and `status: not_found`. Consumers must read the status, not the value.
- **Foundations**: footing dimensions, concrete class and anchor details are not stated.
- **Loads**: design wind and snow values are stated only for ArcelorMittal (40 m/s), Terrasmart ballast (170 mph+, 90 psf+), Array (140 mph) and Nextracker (240 km/h configurable). No source gives load basis or resistance values.
- **Trackers**: tilt range is sourced from Array (+/-52 deg standard, +/-62 deg optional). Bearing dimensions and pile spacing are not stated.
- **Grounding and sealants**: largely not stated for ground structures.
- **Standards not reviewed**: IEC 62817, ASTM C1884 and fastener standards (ISO 4017/4032/7089/7090/898-1) are referenced in the research brief but their texts were not reviewed; they are not applied to any value.
- **Inconsistencies in sources**: the American Ground Screw specification lists 63 in (1600 mm) and 70.9 in (1800 mm) in its capacity tables, and gives both 79 in and 78.7 in (2000 mm) for the same length; it also gives 4.5 in as both 114 mm and 115 mm, and a compression value of 2357 kN that is likely a typo. The BDI reseller listings are inconsistent (the URL slug says 72 in, the title says 78 in); only the 60 in model is recorded in detail.

Count in the JSON files (ground folder, all status fields): 77 `unverified`, 4 `typical`, 84 `not_found`, 0 `verified`. No `verified` value is set.

## 9. Resumen en español

Este documento resume la investigación de diez tipos de estructuras de soporte para plantas fotovoltaicas en suelo (ocho del encargo y dos añadidos: micropilotes y valla bifacial vertical): mesa fija hincada (2P), pilote C de hincado, pilote H de hincado, tornillo de tierra (pilote helicoidal), zapata de hormigón, lastre de hormigón sin penetración, seguidor de un eje sobre tubo de torsión y marquesina de acero S355.

- Datos con fuente: se registran como `unverified` con URL. Ningún valor está `verified`; solo una persona puede aprobarlo.
- Valores genéricos de la industria: `typical` (por ejemplo, un accionamiento por fila en seguidores).
- Secciones añadidas con fuente: pilote H como W6x9 (Gerdau, sin verificar) y pilote C como referencia genérica aproximada (artículo del sector, no confirmada para el producto). Vigas, correas y diagonales de la mesa 2P10 con cantidad por mesa (ProSolar).
- Sin dato en las fuentes revisadas: `not_found`. Las cantidades sin fuente llevan `value: 0` como marcador; el estado `not_found` indica que no deben usarse.
- Principales huecos: secciones y calidades de la mayoría de perfiles, pares de apriete y cantidades de sujeciones, dimensiones de zapatas, y cargas de diseño con su base de cálculo.
- Normas de tornillería (ISO 4017, ISO 4032, ISO 7089/7090, ISO 898-1) citadas en el encargo no se han revisado en su texto; no se aplican a ningún valor.
- Ningún PDF se ha almacenado; los datos son extractos con cita por URL.
