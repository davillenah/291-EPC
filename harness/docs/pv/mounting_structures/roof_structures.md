# Roof-mount PV support structures: families, materials, fasteners and sources

Status: research draft. Every value below is `unverified` (single manufacturer source, pending review), `typical` (generic, none added in this pass) or `not_found`. No value is `verified`; only a person sets that. Data for the engine lives in `harness/src/engines/calculation/pv/src/epc_pv/data/mounting_structures/roof/<id>.json` (schema `mounting_structure.schema.json`, `schema_version` 1.0). All 13 files validate against the schema (jsonschema, Draft 2020-12).

Facts were extracted from public manufacturer documents and product pages. No PDF is stored in the repository; only short citations and extracted values are kept. Torques given in in-lb or lbf-ft are converted to Nm (x 0.11298 and x 1.3558) and the conversion is noted in each entry.

## 1. Families covered

| id (JSON file) | Family | Typical roof | Attachment | Main sources |
|---|---|---|---|---|
| `roof_trapezoidal_sheet_rail` | Rail on trapezoidal / corrugated metal sheet | Steel or aluminium sheet on purlins | Thread-forming stainless screws with EPDM seal (calotte) through sheet crest | K2 catalogue, K2 hanger bolt / solar fastener manual |
| `roof_standing_seam_clamp` | Non-penetrating seam clamp | Standing-seam, snap-seam, double-fold metal roofs | Set screw clamps the seam; rail or module clamp on top | S-5! clamp guides, ClickFit EVO manual |
| `roof_tile_hook` | Adjustable roof hook | Pitched tile and slate roof, timber rafters | Hook under tile course; base plate screwed to rafter; sealing tape | Schletter ProLine and Rapid2+ slate manuals |
| `roof_fibrecement_hanger_bolt` | Stud (hanger) bolt | Corrugated fibre cement; timber or steel substructure | Hanger bolt through the crest, EPDM sealing ring, climber carries rail | K2 HangerBolt CR and hanger bolt manuals |
| `roof_sandwich_panel_clip` | Winged profile on insulated sandwich panel | Insulated metal sandwich panels | Self-drilling screws and trefoil rivets at rib high points, butyl and EPDM seals | Indexfix PSA manual |
| `roof_flat_ballast_tilted_frame` | Ballasted tilted frame | Flat roof, membrane, max 3 degree pitch | Plastic base elements on membrane; concrete ballast trays; no penetration | Esdec FlatFix Fusion manual |
| `roof_flat_ballast_epdm_pad` | Ballasted rail frame with EPDM pad | Membrane roof | EPDM pad under base rail; concrete blocks on pallets; legs set tilt | KSENG ballast manual |
| `roof_flat_ballast_east_west` | Ballasted east-west frame | Flat roof, 0 to 5 degree pitch | Base troughs with ballast trough; 10 degree module supports; no penetration | BayWa r.e. novotegra flat-roof III manual |
| `roof_flat_slab_anchored` (new) | Tilted frame on anchored base plates | Flat concrete slab | Chemical anchors (HIT-Z with HIT-HY 200, HIT-RE 500) or mechanical anchors (HSL-3, HSA) | Hilti anchor documentation |
| `roof_pitched_rafter_rail` (new) | Rails or mini-rails on L-feet fixed to rafters | Pitched tile or shingle roof, timber rafters | Lag screw through covering into rafter; L-foot carries rail | IronRidge Flush Mount manual |
| `roof_membrane_adhered` (new) | Mount welded or fastened through membrane | TPO or PVC membrane roof | Fastener through hot-air welded cover membrane | GAF RM240 installation instructions |
| `roof_metal_minirail_stud` (new) | Mini-rail on stud bolts or seam clamps | Metal sheet or standing-seam roof | Stud bolt through sheet, or S-5 style seam clamp | S-5! guide, K2 catalogue |
| `roof_accessory_catalogue` (new) | Shared catalogue: rail profiles, splices, clamps, gaskets, cable clips | Any roof family | Not a support; holds entries no family file owns | K2 catalogue |

Not covered by sourced data: chemical or mechanical anchor design values (embedment, concrete class, HIT-RE 500 drill hole and torque), cable clips for all families, fully adhered (no-penetration) membrane systems, and EPDM membrane mounts.

## 2. Comparison (key values as stated by sources)

| Family | Tilt | Rail / profile | Module clamp frame range | Torque (stated) | Penetration |
|---|---|---|---|---|---|
| Trapezoidal sheet rail | not stated | BasicRail 22 3.65 m; SolidRail 4.80 m / 5.95 m; MultiRail High 150 x 100 mm | K2 Clamp 25-40 mm; DomeClamp 30-50 mm (name only) | Not stated for K2 clamps; 35 Nm rail connection (SolidRail, related manual) | Yes, sheet screws |
| Standing seam clamp | not stated | Rail via clamp | S-5: not stated; ClickFit EVO 29-50 mm | S-5 set screw 15-20 Nm (other metals 15-17, 22 ga steel 18-20); hex flange bolt 18.1 Nm; ClickFit module clamp 4.5 Nm | No (seam clamp) |
| Tile hook | not stated | ECOA, Rapida, Rapida universal | Not in guide | M8 connections 15 Nm; max overhang 43 mm; min clearance 5 mm; base plate edge distance 4 x diameter | Yes, rafter screws through tile |
| Fibre-cement hanger bolt | 5-75 deg | SingleRail, SingleRail 50 | OneMid/OneEnd 32-42 mm | Upper nut 32 Nm; clamps 14 Nm; rail joint 16 Nm | Yes, hanger bolt |
| Sandwich panel clip | not stated | PSA-A winged profile | Frame height 30-40 mm (gauge GM-A) | Clamp screws 14 Nm | Yes, screws and rivets |
| Flat ballast tilted | 13 deg | Base profiles 210-940 mm | Not in mm (end clamp type by thickness) | Mounting screws 4.5 Nm (max 6.5 Nm) | No (ballast) |
| Flat ballast EPDM pad | not stated | Base rail (profile not stated) | Not stated | Not stated | No (ballast) |
| Flat ballast east-west | 10 deg module elevation; roof 0-5 deg | Support brace 20 x 20 x 1.5 mm | Not stated | Middle clamp 10 Nm; end clamp 8 Nm; earthing 20 Nm | No (ballast) |
| Flat slab anchored | not stated | Base plate and frame not found | Not found | HIT-Z rods: M8 10, M10 25, M12 40, M16 80, M20 150 Nm (Hilti) | Yes, anchors into slab |
| Pitched rafter rail | not stated | Rail / mini-rail (cross-section not found) | IronRidge compatible frames 30-50 mm (across makes) | L-foot 14.9 Nm; rail-to-roof 28.2 Nm; mid/end clamp 9.0 Nm; splice screws 2.3 Nm | Yes, lag screw through covering |
| Membrane welded mount | not stated | Mount base (dimensions not stated) | Not stated | Connection nut 27.1 to 33.9 Nm (20-25 lbf-ft) | Yes, through membrane |
| Metal roof mini-rail / stud | not stated | Mini-rail (K2 MiniRail 60 Set; cross-section not found) | Via seam clamp | See standing seam clamp | Yes (stud) or No (seam clamp) |

## 3. Materials and finishes (as stated)

- Aluminium: EN AW-6063 T66 for K2 rails (K2 catalogue, BasicRail 22, MiniRail 60 Set, MultiRail, SolidRail). EN AW 6082 T6 for the K2 DomeClamp middle clamp. The requested alloy 6005-T5 and 6063-T6 were not found in any source reviewed. T66 is K2's temper designation. K2 SolidRail Light is black anodised; the clamp bodies are black anodised (alloy not stated).
- Stainless steel: A2 (1.4301) for T-bolts, nuts, socket screws, thread-forming screws and rail connector sets (K2). Property class (A2-70 or similar) not stated in any source. A4 not found. 301 TA for TerraGrif grounding parts (K2 SZ and PA 32). Stainless steel for ABEI5519 joint screws (Indexfix). Stainless steel A2 for hanger bolt set screws and adapter plates (K2 CR).
- Galvanised steel: named only in an EnFSolar datasheet for a ballast support (Huge Energy). No thickness or grade stated.
- Plastics and polymers: glass-fibre reinforced polyamide for end caps and BasicClip (K2); thermoplastic clamp parts (K2); top-grade plastic base elements (Esdec); polyamide PA for BasicLock (K2).
- Seals: EPDM for sealing washers, hanger bolt sealing rings, membrane pads and clamps (K2, Indexfix, KSENG). Butyl tape under winged profiles (Indexfix). Fibre-cement seal for hanger bolts (K2).
- Membrane: TPO and PVC cover membranes, hot-air weldable (GAF). EPDM is not covered by the GAF source.
- Copper: equipment grounding conductor minimum 10 AWG solid or stranded (IronRidge).
- Concrete: ballast blocks and paving slabs (Esdec 21 x 10.5 x 8 cm, about 4 kg; KSENG 9.4 kg per block as design standard). Concrete class of anchored slabs not stated.
- Finish of stainless fasteners and clamp bodies: not stated in any source.

## 4. Fasteners (as stated)

| Fastener | Used in | Size and grade (stated) | Torque (stated) |
|---|---|---|---|
| Thread-forming screw with EPDM seal | Trapezoidal sheet | 6 x 22 mm, A2 (1.4301); sheet 0.4-1.25 mm; K2 variant code 6x25_rs conflicts | not stated |
| Self-tapping screw (discontinued) | Trapezoidal sheet | 6 x 38 mm, A2 (1.4301); sheet 0.4-1.25 mm | not stated |
| T-bolt 28/15 | Rail channel | M8 (20, 30 mm); M10 (20, 25, 30 mm); 1.4301 (A2) | not stated |
| Hex socket head cap screw | Rail/clamp | M8 x 20, ISO 4762, drive A/F 6 | not stated |
| Serrated flange nut | Rail channel | M8 (A/F 13), M10 (A/F 15), DIN 6923, A2 | not stated |
| Hanger bolt CR | Fibre cement | M10 and M12; pre-drill 14 and 15 mm | no torque (seal slightly compressed) |
| Hanger bolt for timber | Timber rafter | M10 (180, 200, 250 mm), M12 (200, 250, 300 mm); min depth 40 / 48 mm | not stated |
| Solar fastener M10 | Timber, steel, sheet | Screws 50 and 70 mm; total 80-200 mm (timber); 85-195 mm (steel) | 16 Nm (clamps), 35 Nm (rail connection) |
| Set screw for seam clamp | Standing seam | Size and grade not stated; T30 Torx bit | 15-17 Nm (other metals), 18-20 Nm (22 ga steel) (S-5) |
| M8-1.25 x 16 hex flange bolt | Standing seam (S-5) | Sold separately; grade not stated | 160 in-lb = 18.1 Nm (S-5, step 4) |
| Mounting screw | Flat ballast (Esdec) | 6.5 x 55 to 85 mm (length by frame thickness); 6.5 x 19 mm | 4.5 Nm, max 6.5 Nm; check 3.0-3.5 Nm |
| Self-tapping screw | Flat ballast trays | 6.0 x 25 mm; 6.3 x 32 mm (grounding) | not stated |
| Self-drilling ABEI5519 | Sandwich panel joints | Stainless steel; 2 per side for rigid joint | not stated |
| M8 x 25 bolt with nut | KSENG ballast | M8 x 25 | not stated |
| Upper self-locking nut | Fibre-cement rail | Similar to ISO 4161 (per K2) | 32 Nm |
| Wood screw M8 (base plate) | Tile hook (ProLine) | M8, one per roof hook, Torx T40 drive; length per local standards | 15 Nm |
| HIT-Z anchor rod M8 to M20 | Flat slab (Hilti) | M8, M10, M12, M16, M20; base plate clearance 9/11, 12/14, 14/16, 18/20, 22/24 mm | 10, 25, 40, 80, 150 Nm |
| HSL-3 / HSA mechanical anchor | Flat slab (Hilti) | HSL-3 M8 to M24; HSA M6 to M20; drill, embedment and torque not stated | not stated |
| Lag screw into rafter | Pitched rafter (IronRidge) | Pilot hole 1/4 in (6.35 mm); diameter, length and embedment not stated | L-foot 132 in-lb = 14.9 Nm |
| Drill-Tec #14 / XHD #15 / purlin fastener | Membrane (GAF) | Per design professional; length not stated | Connection nut 20-25 lbf-ft = 27.1-33.9 Nm |
| Bonded splice screws | Pitched rafter rail (IronRidge) | Two per rail, 1 in apart; splice 6 in into rail | 20 in-lb = 2.3 Nm |

Bolt grades (A2-70, 8.8, 10.9) were not stated in any of these documents. The grade of each stainless fastener must be confirmed before use.

## 5. Standards

Referenced in the JSON `applicable_standards` lists. Only EN 1991-1-4, ISO 3506-1, ISO 898-1 and IEC 62817 were located through search, and only the ISO and IEC catalogue pages were opened. The other items are cited from general knowledge and were not checked. None of the standard texts was read.

- EN 1991-1-3 (snow loads) and EN 1991-1-4 (wind actions): design loads. Not applied in this research. Projects must compute loads.
- EN 1999-1-1 (aluminium) and EN 1995-1-1 (timber): member design. Not verified.
- EN 1090-2: execution of steel and aluminium structures. Not searched.
- ISO 3506-1:2020: mechanical properties of corrosion-resistant stainless steel fasteners (3rd edition, 2020; title confirmed on the ISO site). The property classes (such as A2-70) are not named on that page. The class assignments are not confirmed here.
- ISO 898-1:2013: carbon steel fasteners, property classes (8.8, 10.9). Title located in search results only.
- ISO 4017 (hex bolts), ISO 4032 (hex nuts), ISO 7089 / 7090 (washers): cited in the task, not searched.
- ISO 4161 (flange nuts): cited by K2 as similar to the self-locking nut. Not searched.
- ISO 4762 (socket head cap screw) and DIN 6923 (flange nut): cited by the K2 catalogue page; not read.
- Hilti anchor approvals (ETA 04/0027, ETA 07/0260, ETA 09/0295, ETA 12/0083, ETA 12/0006, ETA 12/0084, ICC-ES ESR-3187) are cited by number only. The approval documents were not opened.
- IEC 62817: the JRC catalogue entry gives its scope as "photovoltaic systems, design qualification of solar trackers". It does not cover fixed roof mounts, so it is not listed in any roof JSON. This is a correction to the task brief.

## 6. Sources (URLs, accessed 2026-11-20)

Manufacturer and distributor documents (extracted facts only, not stored):

1. K2 Systems catalogue, trapezoidal sheet metal: https://catalogue.k2-systems.com/en-uk/area-of-application/pitched-roofs/trapezoidal-sheet-metal/
2. K2 Systems, hanger bolts and solar fasteners (EN): https://catalogue.k2-systems.com/media/fc/93/f4/Hanger-bolts-solar-fasteners-assembly-en.pdf
3. K2 Systems, HangerBolt CR SingleRail (EN): https://cdn.shopify.com/s/files/1/0524/2018/2189/files/HangerBolt-CR-assembly-en.pdf
4. IronRidge XR100 product page (distributor, rail finish only): https://www.greentechrenewables.com/product/ironridge-xr100-11ft-anodized-rail-clear-xr-100-132a
5. S-5! clamp installation guide (S-5-U, S-5-S, S-5-E, S-5-B, S-5-V): https://cdn.shopify.com/s/files/1/0299/1477/files/s-5-s-u-e-b-v-clamp-install-guide.pdf
6. S-5-H90 clamps installation: https://cdn.shopify.com/s/files/1/0420/1073/8840/files/s-5-h90-clamps-installation.pdf
7. Enstall ClickFit EVO standing seam manual (EN): https://portal.segen.co.uk/reseller/docs/Manual_ClickFitEvo_StandingSeamRoof_EN_216.pdf
8. Schletter ProLine roof hook mounting instruction (EN): https://portal.segen.co.uk/reseller/docs/ProLine_Roof_Hook_-_Mounting_instruction_EN_202102_V2.asd.pdf
9. Schletter roof hook Rapid2+ slate: https://portal.segen.co.uk/reseller/docs/Roof_hook_Rapid22B_Slate_-_mounting_instructions_V1_I400317GB.pdf
10. Esdec FlatFix Fusion Dual manual (EN): https://portal.segen.co.uk/reseller/docs/Manual_FlatFixFusion_Dual_EN_051.pdf
11. EnFSolar datasheet, Esdec FlatFix eco (discontinued; used for context only): https://www.enfsolar.com/pv/mounting-system-datasheet/203
12. EnFSolar datasheet, Huge Energy ballast support (context only): https://www.enfsolar.com/pv/mounting-system-datasheet/9359
13. KSENG ballast roof mounting installation manual (v8): https://cdn.shopify.com/s/files/1/0567/8022/6625/files/Installation_Manual_-KSENG_Ballast_roof_mounting_system_8.pdf
14. BayWa r.e. flat roof III east-west mounting instructions: https://solar-distribution.baywa-re.de/out/media/Flachdach_III_05-3-1-EN-Flat-roof-III-Mounting-instructions.pdf
15. Indexfix FTA GS M SC-PSA installation guide (rev1): https://www.indexfix.com/wp-content/uploads/CMP6735/files/FTA_GS_M_SC-PSA_en_rev1.pdf
20. Hilti anchor technical document (HIT-HY 200, HIT-RE 500, HSL-3, HSA; title not extracted): https://hilti.com/medias/sys_master/h7c/h06/9167662088222.pdf
21. IronRidge Flush Mount Installation Manual v2.0: https://cdn.shopify.com/s/files/1/0079/6003/5417/files/IronRidge_Flush_Mount_Installation_Manual.pdf
22. GAF Rooftop Equipment Mount 240 installation instructions (COMEG542): https://www.gaf.com/en-us/document-library/documents/installation-instructions-&-guides/gaf-rooftop-equipment-mount-240-installation-instructions-comeg542.pdf

Standards pages:

16. ISO 3506-1:2020 (catalogue page): https://www.iso.org/standard/70045.html
17. ISO 898-1:2013 (catalogue page, from search): https://www.iso.org/standard/60610.html
18. IEC 62817 scope (JRC catalogue): https://ses.jrc.ec.europa.eu/eirie/en/standard-regulations/photovoltaic-systems-design-qualification-solar-trackers-0
19. EN 1991-1-4 (NEN catalogue, from search): https://connect.nen.nl/standard/detail/3703987

Several sources are distributor-hosted copies of manufacturer manuals (Segen, Shopify CDNs). Their revision dates are not stated, so the currency of each value is not confirmed. The Hilti and GAF extracts were read by page or step; the IronRidge manual page numbers are as printed by the extract.

## 7. What remains unverified or missing

- Status counts over the 13 files (all status fields, including file level): `unverified` 202, `not_found` 66, `typical` 0, `verified` 0.
- Material grades and finishes: alloy and temper (T66 is K2's designation; 6005-T5 and 6063-T6 were not found), stainless property class (A2-70 not confirmed), zinc or coating thickness for galvanised parts, lag screw and anchor grade.
- Profile cross sections in mm: only rail lengths and a few width and height values were found (MultiRail High 150 x 100 mm). Most profile `dimensions_mm` are empty.
- Torque: found for a subset. Missing for most K2 clamps, rail joints and sheet screws, and for HIT-RE 500, HSL-3 and HSA.
- Quantities per module, per rail, per row and per support: not stated in any source reviewed. Stored as `value 0` with a note. Treat 0 as unknown, not zero. The only sourced counts are: one base plate and one wood screw per roof hook (ProLine), two splice screws per rail (IronRidge).
- Geometry: no fixing pitch, rail spacing, clamp spacing, hook spacing, rafter spacing or anchor pattern was stated, so `geometry.elements` is empty for the new families. Only the trapezoidal rail has a reference element (BasicRail 3650 mm length, placeholder origin).
- Loads: no wind or snow design calculation. Only manufacturer ratings are mentioned (Huge Energy 216 km/h wind and 2.4 kN/m2 snow; KSENG design basis 25 m/s and 1 kN/m2; K2 XR100 and XR10 have no numeric ratings). Ballast per module is not stated for any system.
- Grounding and bonding: stated for Esdec FlatFix Fusion, K2 (TerraGrif), BayWa (contact latch and earthing 20 Nm), IronRidge (lug 9.0 Nm, terminal 2.3 Nm, copper 10 AWG). Not found for tile hooks, standing-seam clamps, hanger bolts, sandwich panels, anchored slabs and membrane mounts.
- Sealants: EPDM is common; butyl (Indexfix) is the only other sealant named. No sealant product found for membrane mounts (GAF specifies none).
- Anchors: HIT-Z torques and clearances are sourced; embedment depth, concrete class and HSL-3, HSA and HIT-RE 500 drill and torque values are not stated in the extracted pages.
- Cable clips: no sourced product for any roof family.
- Standards: EN 1991-1-3, -1-4, EN 1999, EN 1995, EN 1090, ISO 4017, 4032, 7089, 7090, ISO 4161 are cited but not read. Loads and design are the designer's responsibility.
- Product currency: K2 6x38 screw and some K2 rails are marked discontinued or phase-out. Esdec FlatFix eco is no longer manufactured. K2 MultiRail 10 and 25 are phase-out items.
- Source conflicts: K2 6x22 screw description vs variant code 6x25_rs; IronRidge grounding lug 80 in-lb (text) vs 84 in-lb (diagram); K2 6063 T66 vs requested 6063-T6.

## Resumen en español

Este documento recoge trece archivos de soportes para instalaciones fotovoltaicas en cubierta. Ocho son familias existentes: rieles sobre chapa trapezoidal, garras para cubierta de junta alzada (S-5! y ClickFit EVO), ganchos para teja (Schletter ProLine y Rapid2+ pizarra), espárragos para fibrocemento y madera (K2 HangerBolt), perfiles sobre panel sándwich (Indexfix PSA) y tres familias lastradas para cubierta plana (Esdec FlatFix Fusion, KSENG con almohadilla EPDM y BayWa novotegra este-oeste). Cinco son nuevas: anclajes en losa plana (Hilti HIT-Z, HIT-RE 500, HSL-3, HSA), rieles sobre escuadras en L fijadas a cabios (IronRidge), membrana soldada (GAF, TPO y PVC), mini-rieles sobre espárragos o garras de junta en metal (tipo S-5) y un catálogo común de perfiles, empalmes, garras, juntas y clips.

Hechos verificados: no. Todos los valores están marcados como `unverified` (fuente única de fabricante, pendiente de revisión) o `not_found`. Ningún valor está marcado como `verified`; solo una persona puede hacerlo. No se usó ningún valor `typical`.

Nuevos datos sourced en esta pasada: aleación EN AW-6063 T66 y EN AW 6082 T6 (K2); acero inoxidable A2 (1.4301) y 301 TA para puesta a tierra (K2); pares de apriete de ProLine (M8 15 Nm), S-5 (15-20 Nm y 18,1 Nm), Hilti HIT-Z (10 a 150 Nm), IronRidge (14,9; 28,2; 9,0 y 2,3 Nm) y GAF (27,1 a 33,9 Nm); conductor de cobre mínimo 10 AWG (IronRidge).

Principales lagunas: grados y clases de los tornillos (A2-70 no confirmado; 6005-T5 y 6063-T6 no encontradas; los documentos citan EN AW-6063 T66); cantidades por módulo, riel, fila o soporte (no encontradas salvo dos casos); perfiles con sección transversal en mm; cargas de viento y nieve; empotramiento de anclajes, clase de hormigón y valores de HIT-RE 500, HSL-3 y HSA; puesta a tierra en varias familias; cables de módulo; y sellantes distintos de EPDM y butilo. La norma IEC 62817 trata de seguidores solares, no de soportes fijos de cubierta, por lo que no se usa para estas familias. Los valores sin verificar y los no encontrados están registrados en los archivos JSON.

Archivos: `/home/user/291-EPC/harness/docs/pv/mounting_structures/roof_structures.md` y trece JSON en `/home/user/291-EPC/harness/src/engines/calculation/pv/src/epc_pv/data/mounting_structures/roof/`. Todos validan contra `mounting_structure.schema.json` (jsonschema, Draft 2020-12).
