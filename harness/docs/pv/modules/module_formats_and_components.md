# PV module formats and component families (research for 2D/3D modelling)

Status: research notes, second pass. Accessed 2026-11-20. All values are from manufacturer datasheets or installation manuals listed in section 6; standards are cited by title only (not fetched). No value here is `verified` (only a person may set that). Values not found in any source reached are `not_found`; generic industry values are `typical` (none used).

JSON files (schema `pv_module.schema.json`, kind `format`) are in:
`harness/src/engines/calculation/pv/src/epc_pv/data/pv_modules/formats/`

## 1. Module size classes

Mechanical data from the datasheet extracts. Cell counts are as printed. Weights and loads are for the specific product line.

| id (JSON) | L x W x T (mm) | Cells (as printed) | Weight (kg) | Junction box | Static load front / rear (Pa) | Source |
|---|---|---|---|---|---|---|
| `g12_66_132hc_2382x1134x30` | 2382 x 1134 x 30 | 132, layout 6x22 (BC-CELL mentioned) | 32.5 | IP68, 3 diodes | 5400 / 2400 | S1 (LONGi LR8-66HVD) |
| `g12r_66_132hc_2382x1134x30_renew` | 2382 x 1134 x 30 | 132 half-cut G12R | 33.5 | IP68 / IP67, diode count not stated | wind 2400 / snow 5400 (no split) | S21 (Renew RPS3MH66BD) |
| `g12_72_144_2278x1134x30` | 2278 x 1134 x 30 | 144, layout 6x24 | 27.2 | IP68, diode count not stated | 5400 / 2400 | S2 (LONGi LR5-72HTH) |
| `g12_72_144_abc_2382x1134x30` | 2382 x 1134 x 30 (tol. +-2) | 144 N-type ABC, layout 6x24 | 33.5 (+-3 %) | IP68, 3 bypass diodes | 5400 / 2400 | S3 (AIKO MCH72Dw) |
| `cs6_2_54tm_1961x1134x30` | 1961 x 1134 x 30 | 108 TOPCon, printed as 2 x (9 x 6) (model "54TM") | 23.3 | IP68, 3 bypass diodes | snow 5400 / wind 2400 (no split) | S17 (Canadian Solar CS6.2-54TM) |
| `jinko_60hl4r_1955x1134x30` | 1955 x 1134 x 30 | 120, printed as 2 x 60 | 24 | IP68, diode count not stated | wind 2400 / snow 5400 (no split) | S18 (JinkoSolar JKM475-495N-60HL4R-V) |
| `aiko_neostar_3pplus60_1954x1134x30` | 1954 x 1134 x 30 | 120, printed as 6 x 20 | 27.1 (+-3 %) | IP68, 3 bypass diodes | 5400 / 2400 | S19 (AIKO Neostar 3P+60, dual glass) |
| `longi_lr5_54htb_1722x1134x30` | 1722 x 1134 x 30 | 108, printed as 6 x 18 | 20.8 | IP68, 3 diodes | 5400 / 2400 | S20 (LONGi Hi-MO 6 LR5-54HTB) |
| `m10_54_108_1722x1134x30` | 1722 x 1134 x 30 | 108 N-TOPCon, layout 6x18 | 25.0 (+-0.5) | IP68, 3 bypass diodes | 5400 / 2400 | S5 (Maysun, glass-glass, steel frame) |
| `m10_54_108_1800x1134x30` | 1800 x 1134 x 30 | 108, layout 6x18 | 21.6 | IP68, 3 diodes | 5400 / 2400 | S4 (LONGi LR7-54HVH, third-party copy) |

Notes:
- The "66-cell G12" class is printed as 132 cells (6x22) in S1, i.e. 66 full-cell equivalent. Cell size is not stated in any source.
- The 1800 mm LR7-54HVH is not the common 1722 mm M10 length; both are kept as separate formats.
- The Maysun 1722 module uses a steel frame (galvanized or powder-coated), not aluminium. Do not reuse its frame family. The new `longi_lr5_54htb_1722x1134x30` entry is the aluminium-framed 1722 mm format.
- The Canadian Solar "54TM" name is printed with 108 cells; the model name is kept as printed and the cell count is the printed one.
- The Jinko "60HL4R" model name comes from the datasheet file name; the printed title was not extracted.
- Cable on all modules: 4 mm2 (IEC), 12 AWG (UL) where printed. Lengths are per module (section 2.4 and the JSON).

### 1.1 Size classes requested: status

| Requested class | Status | Note |
|---|---|---|
| 54-cell 156-166 mm (M6) | partial | `longi_lr5_54htb_1722x1134x30` (108 half cells, 1722 mm). Cell size (156.75 mm or other) not stated in the extract, so the M6 class is not confirmed. |
| 60-cell 156-166 mm (M6/M10) | partial | `jinko_60hl4r_1955x1134x30` and `aiko_neostar_3pplus60_1954x1134x30` are 60-cell (120 half cells) at 1955 / 1954 mm; cell size not stated. Not the 1650-1700 x 1000-1030 class. |
| 66-cell M6 (156-166 mm) | not_found | Not reached in any datasheet during this pass. |
| 66-cell M10 (182) | not_found | Not reached. |
| 72-cell M10 (182), 2278 x 1134 | found as `g12_72_144_2278x1134x30` | 144 half cells (6x24) on the LONGi datasheet; cell size not stated, so neither the M10 nor the G12 class is confirmed. |
| 55-cell and 60-cell G12 (210) | not_found | Not reached. |
| 60-cell 1650-1700 x 1000-1030 | not_found | Searches for 1650 x 1000 / 1665 x 1002 modules returned no product datasheet. |
| G12R | found as `g12r_66_132hc_2382x1134x30_renew` | 132 half-cut G12R cells, 2382 x 1134 x 30 mm (Renew). |
| G12R 1762 x 1134 | not_found | Searched; no product datasheet reached. |
| 2382 x 1134 | found (three entries) | `g12_66_132hc_2382x1134x30`, `g12_72_144_abc_2382x1134x30`, `g12r_66_132hc_2382x1134x30_renew`. |
| 1722 x 1134 | found (three entries) | `m10_54_108_1722x1134x30` (steel), `longi_lr5_54htb_1722x1134x30` (aluminium). |
| 1961 x 1134 and 1954-1955 x 1134 | found (new, not requested) | `cs6_2_54tm_1961x1134x30`, `aiko_neostar_3pplus60_1954x1134x30`, `jinko_60hl4r_1955x1134x30`. |

Seen in search, not added (outside the requested classes, no entry yet): JinkoSolar JKM590-610N-78HL4-BDV (2465 x 1134 x 35 mm, 156 cells 2 x 78, IP68, 4.0 mm2 cable 400/200 mm, frame anodized aluminium) and Solvis SV132 HCG12R (2382 x 1134 x 35 mm, 132 cells, 33 kg).

## 2. Component families

Each family is one JSON file. Components have no module outline, so `layers` is `[]` and `elements` is `[]`.

### 2.1 Frame profile (`frame_profile_anodized_aluminium`)
- Section dimensions (height, width, wall thickness, groove): **not_found** in all sources reached. Heliene (S22) prints a "double webbed" profile; Solvis (not added) prints "twin-wall profile"; no dimensions in either.
- Alloy temper: **not_found** for the frame (6063-T5 is not printed). Trina recommends clamps in 6005-T5/T6 (S23); this is a clamp material, not the frame.
- Anodizing thickness: **15 micron** as printed by Heliene (S22) for its G12R module. Not confirmed for other families.
- Grounding hole: diameter 4.0 mm (S8, S21 Renew 2 holes, S22 Heliene 4 holes) and 4.2 mm (S3 AIKO, S24 LONGi). Both kept as printed. Long side of the back frame near the edge (S8, S24). Bolted grounding only; S23 (Trina) gives grounding conductor 4-16 mm2 (12-6 AWG), screw torque 3-7 N.m, and says the screw penetrates the anodized coating. Trina recommends grounding resistance below 1 ohm.
- Drainage holes: 8 x phi3 x 8 printed in S3 (AIKO); Renew (S21) and Heliene (S22) print 4 or 8 drainage holes with sizes not stated; S8 and S24 do not state them.
- Mounting holes: M8 - 14 x 9 mm (S8, S21), printed as 9 x 14 by Trina (S23); M8 torque 16-20 N.m (S8, S23), 12-16 N.m (S24 LONGi). M6 - 10 x 7 mm (S8, S21), printed as 7 x 10 by Trina (S23); M6 torque 9-12 N.m (S8), 8-12 N.m (S23, S24). LONGi uses 8 holes for M8 (4 inner, 4 outer) on the back-side frame (S24). Positions and centre distances: **not_found**.
- Clamp contact: length >= 50 mm (S8, S23, S24; >= 60 mm for modules > 2.2 x 1.3 m in S8). Thickness >= 3 mm (S8) or >= 4 mm (S23). Frame overlap: 10-11 mm (S8), 8-12 mm (S23), 8-11 mm (S24, framed modules; corner clamps length >= 60 mm and overlap >= 9 mm). M8 clamp torque: 16-20 N.m (S8), 10-14 N.m (S23), 14-18 N.m (S24).
- Clamp zones (geometry.clamping_zones_mm, values as printed, reference edge not stated, status `unverified`): Trina Vertex DE09 A = 250-350 mm (perpendicular rails, long side, S23 p.23); NEG20C.20 A = 360-430 mm (S23 p.22); NDG05R.78 A = 210-310 mm (S23 pp.28-29). LONGi clamp placement D = 1/4 L - 50 to 1/4 L + 50 mm (S24 p.14), L as printed. Jinko formula L = A/4 +-50 mm (S8): A is not defined in the extract and is `not_found` as a value.
- Installation load examples (S8 Table 2), bolt mounting: 8-hole (4 inner holes) +5400/-2400 Pa for 1.6 mm glass families; 12-hole (4 outer holes) +5400/-2400 Pa for 66QL6-BDV, 66HL4M-BDV, 66HL4M-(V), 66HL5-BDV; +6000/-4000 Pa for other listed families. The test load is 1.5 x design load. LONGi general maximum: downforce 5400 Pa, uplift 2400 Pa (S24).
- Corner keys: **not_found** (no source printed them).
- Clamp positions cannot be placed in `elements` yet: each hole and clamp needs a position, and the reference edges are not stated in the Trina and LONGi extracts.

### 2.2 Junction box (`junction_box_ip68_3diode`)
- Split 3-part junction box, its dimensions and diode ratings: **not_found**. The Renhe, Amphenol, Zhejiang Qunli and Staubli junction box searches returned no product datasheet with dimensions.
- Module junction boxes as printed: IP68 with three bypass diodes (S1, S3, S5, S17 CS6.2-54TM, S19 AIKO, S20 LONGi 54HTB, S22 Heliene G12R 35 mm). S2 (LONGi 72HTH), S18 (Jinko 60HL4R) and S21 (Renew G12R) print IP68 without diode count.
- Bypass diode current, voltage and type: **not_found** in every reached datasheet. Component datasheets for Schottky diodes exist, but they are not this product's diode, so no rating is copied from them.
- Reference only: Hirschmann Multiple Fresh Box (S9), a one-diode box 68 x 74 x 18 mm, up to 12 A, 1000 V DC, IP66/IP67/IPX9K, cable up to 4 mm2, -40 to +85 C, IEC 62790:2014 cited, UL 3730 cited. This is not a split box and not for three-diode modules.

### 2.3 MC4-Evo 2 connector (`connector_mc4_evo2`)
From the Staubli technical data 11014101 EN (S6), and the copy used for the cable table (S25):
- Rated voltage: 1500 V DC (IEC, JET) and 1500 V DC (UL), unrestricted access.
- Rated current IEC / UL, plug: 2.5 mm2 39 A / 30 A (14 AWG); 4 mm2 45 A (IEC), 53 A (6 AWG), 50 A (10 AWG), and 12 AWG 39 A (S6) or 35 A (S25); 10 mm2 69 A / 70 A (8 AWG). The 12 AWG value differs between the two Staubli copies; both are kept and it is not resolved.
- Rated current IEC / UL, panel receptacle: 2.5 mm2 32 A / 30 A; 4 mm2 42 A (IEC), 47 A (6 AWG), 50 A (10 AWG), 12 AWG 39 A (earlier extract) or 35 A (S25); 10 mm2 62 A (IEC) / 70 A (UL).
- Cable variants (S25 table): cable OD 4.7-6.4 mm, 6.1-7.3 mm or 6.4-8.4 mm, by variant name (2A/2.5I, 2A/2.5X, 2A/2.5II, 2A/6I, 2A/6X, 2A/6II, 2A/10X, 2A/10II). Crimp opening: 4.0 mm for 2.5 mm2, 5.8 mm for 4 mm2, 6.5 mm for 10 mm2. The 4.7-6.4 mm range is the one for the 2.5 and 4 mm2 plugs; the other ranges fit 2.5, 4 and 10 mm2 variants as listed.
- IP: IP65/IP68 mated (plug 1 m, 168 h; receptacle 1 m, 1 h); IP2X unmated.
- Ambient -40 to +85 C; upper limiting temperature 115 C.
- Panel wall thickness: 1 to 4 mm (metal), 1 to 6 mm (plastic).
- Outline: the drawing values 11.3, 12.15 and 12.3 mm are printed without an axis or reference point. Full outline: **not_found**.
- Standards cited by the manufacturer: IEC 62852:2014+Amd.1:2020 (TUV Rheinland); UL 6703 (E343181); CSA C22.2 No. 182.5; IEC TS 63126 Level 2; UL94-V0 flame class; TUV ammonia resistance 2 PfG 1911/03.2011.

### 2.4 PV cable H1Z2Z2-K (`cable_h1z2z2_k_pv`)
From the Prysmian TECSUN PV H1Z2Z2-K data sheet (S7):
- Conductor: electrolytic tinned copper, finely stranded, class 5 (IEC 60228).
- Insulation: cross-linked HEPR, 120 C. Sheath: cross-linked EVA rubber, 120 C.
- Rated voltage: 1.5/1.5 kV DC; 1.0/1.0 kV AC. Conductor 90 C in operation; short circuit 250 C for 5 s.
- 4 mm2 (1x4): OD 5.3-5.9 mm, minimum fixed bending radius 18 mm, max resistance 5.09 ohm/km at 20 C.
- 6 mm2 (1x6): OD 5.9-6.5 mm, bending radius 20 mm, 3.39 ohm/km.
- Screened variants 1x4 (C): OD 6.0-6.6 mm, bending radius 26.4 mm; 1x6 (C): OD 6.5-7.1 mm, 28.4 mm.
- Standard: EN 50618 cited; TUV certificate 60103637 cited.
- Lengths per project: **not_found** (project data). The lengths printed by module makers are in each module's pv_cable part: 300/200 mm (S17 CS6.2, S21 Renew 300 mm), 400/200 mm (S18 Jinko, S1 LONGi LR8), 1200 mm +- (S19 AIKO, S20 LONGi 54HTB), 1100 mm (S22 Heliene), 300 mm, 1000 mm (S5 Maysun, portrait N/P, customizable), +400/-200 and +-1400 mm (S1 LONGi as printed).
- The manufacturer gives min and max OD, not a nominal value.

### 2.5 Other families requested

| Family | Status | Reason |
|---|---|---|
| Corner keys | not_found | No source reached printed corner keys. |
| Busbars / ribbons | not_found | Not stated in any datasheet reached. |
| Backsheet vs glass (rear) | partial | Glass-glass in S5 (2.0 mm front and rear, POE), S19 AIKO (2.0 + 2.0 mm), S21 Renew (2 mm + 2 mm), S22 Heliene (2 mm back glass, 35 mm module). LONGi 54HTB (S20) is single-glass; rear material not stated. |
| Edge sealant | not_found | Not stated in any source. |
| Labels | not_found | Not stated in any source. |
| Drain holes | partial | 8 x phi3 x 8 (S3). Other sizes not stated (see 2.1). |
| Encapsulant (type, thickness) | partial | POE in S5; others not stated. |
| Cell size / busbar count | not_found | Not stated in any source (S1 mentions BC-CELL, no size). |
| Front glass thickness | partial | 2.0 mm (S5, S19, S21, S22); 3.2 mm (S17 CS6.2, S20 LONGi 54HTB). |

## 3. Standards cited

Standards are cited by title only. Their text was not fetched and nothing is copied from them. Each is recorded as a source with the status `unverified`.

| Standard | Cited by | Used for |
|---|---|---|
| IEC 61215 (design qualification) | S2, S4 | module qualification |
| IEC 61730 (safety) | S2, S4, S24 (grounding symbol) | module safety |
| IEC 62852 (DC connectors) | S6, S25 | MC4-Evo 2 |
| IEC 62790 (junction boxes) | S9 | reference junction box |
| IEC 62941 (design qualification guideline) | S2, S4 | module design |
| EN 50618 (PV cables) | S7 | H1Z2Z2-K |
| UL 6703 | S6, S25 | connector |
| IEC 60228 (conductors) | S7 | cable conductor class |
| IEC TS 63126 (connector temperature level) | S6, S25 | MC4-Evo 2 |

Not verified: whether each datasheet's standards list is current.

## 4. Gaps (what the next pass should do)

1. Find datasheets with cell size for the 54/60/66-cell M6 classes at 156-166 mm, the 60-cell 1650-1700 x 1000-1030 class, the G12 55/60-cell classes, and the G12R 1762 x 1134 class. Searches in this pass did not reach them.
2. Obtain a frame section drawing (height, width, wall, groove) from a manufacturer drawing, and confirm the alloy temper.
3. Obtain the hole positions (mounting, drainage, grounding) and the clamp reference edge per module family, to place them in `elements`. Trina (S23) and LONGi (S24) give the numbers without an axis reference.
4. Obtain a split 3-part junction box datasheet with dimensions and bypass diode ratings (Renhe, Amphenol, Zhejiang Qunli, Staubli).
5. Obtain the full MC4-Evo 2 outline drawing (the three drawing values are not assigned to an axis).
6. Confirm the standards cited by manufacturers against the standard publishers (not done here).
7. Confirm the 1800 mm LR7-54HVH (S4 is a third-party copy) and the 54HTB 4 mm2 cable (the extract is garbled) on the manufacturer sites.
8. Decide whether to add the 2465 x 1134 x 35 (Jinko 78HL4) and 2382 x 1134 x 35 (Solvis, Heliene) variants, which were seen but not added.

## 5. Unverified items (summary)

- Cell size, busbar count and cell technology details for almost all module formats.
- Front and rear glass thickness, encapsulant and backsheet for several formats (see 2.5).
- Frame section, alloy temper and groove for all frames. Anodizing 15 micron for the Heliene G12R only.
- Mounting, drainage and grounding hole positions (sizes are printed for several families, see 2.1).
- Clamp reference edges (Trina A, LONGi D) per family.
- Junction box dimensions, split construction and diode ratings.
- Connector outline dimensions (the MC4-Evo 2 cable OD mapping is now from the variant table, S25).
- Cable lengths per project.
- All standards cited by manufacturers (not checked against the standard publishers).

Count of objects with `status: not_found` across the 14 JSON files: 127 (counted from the JSON, all `status` fields equal to `not_found`). The first pass counted 74 values across nine files with a different method, so the two counts are not comparable.

## 6. Sources

| id | Title | Publisher | URL |
|---|---|---|---|
| S1 | LONGi LR8-66HVD product datasheet (2382 x 1134 x 30 mm) | LONGi (copy hosted on enfsolar CDN) | https://cdn.enfsolar.com/z/pp/2026/4/71uvt57p0ct63xch/lr8-66hvd-1.pdf |
| S2 | LONGi LR5-72HTH 590-600M product datasheet | LONGi (copy hosted on Shopify CDN) | https://cdn.shopify.com/s/files/1/0882/5641/4023/files/Datasheet_Longi_LR5-72HTH_590_600M.pdf |
| S3 | AIKO Stellar MCH72Dw 635-660 W product datasheet | AIKO (copy hosted on Segen portal) | https://portal.segen.co.uk/reseller/docs/Stellar-1N_Plus_Customized_Stellar_192.5-AIKO-G-MCH72Dw-635-660W_2382x1134x30mm_DSDr_EN_2405_V1.5.pdf |
| S4 | LONGi LR7-54HVH 485M product datasheet | LONGi (copy hosted by a third-party site) | https://usercontent.one/wp/www.gingroup.it/wp-content/uploads/2025/03/Longi-LR7-54HVH-485M-Datasheet-EN.pdf |
| S5 | Maysun Solar 1722 x 1134 x 30 mm 108-cell TOPCon datasheet | Maysun Solar | https://www.maysunsolar.com/wp-content/uploads/2026/01/Maysun-Solar-182mm-Glass-Glass-TOPCon-108-cells-425W-445W-1722mm-x-1134mm-x-30mm.pdf |
| S6 | Staubli SOL MC4-Evo 2 technical data (11014101 EN) | Staubli Electrical Connectors | https://www.staubli.com/content/dam/spot/SOL-MC4-Evo-2-11014101-en.pdf |
| S7 | TECSUN(PV) H1Z2Z2-K technical data sheet | Prysmian Group | https://www.prysmian.com/sites/www.prysmian.com/files/media/documents/Tecsun-PV-_H1Z2Z2-K.pdf |
| S8 | JinkoSolar Global Installation Manual A1.8 (2026-05) | JinkoSolar | https://www.jinkosolar.com/uploads/%5BFINAL%5D%20JinkoSolar%20Global%20Installation%20Manual_202605_A1.8-EN.pdf |
| S9 | Hirschmann Multiple Fresh Box product flyer | Hirschmann Automotive | https://www.hirschmann-automotive.com/media/user_upload/Products/Renewable_Energy/Hirschmann_Automotive_Renewable_Energy_Product_Flyer_Multiple_Fresh_Box_EN.pdf |
| S10 to S16 | Standards (IEC 61215, IEC 61730, IEC 62852, EN 50618, IEC 62790, IEC 62941, UL 6703): title only, not fetched | IEC, CENELEC, UL | see the JSON `sources` arrays |
| S17 | Canadian Solar CS6.2-54TM PV module datasheet V1.2 (1961 x 1134 x 30 mm) | Canadian Solar (copy hosted by Solarproof) | https://solarproof.com.au/datasheets/panel_datasheet_CS-Datasheet-TOPHiKu6_CS6.2-54TM_v1.2_EN.pdf |
| S18 | JinkoSolar JKM475-495N-60HL4R-V datasheet (1955 x 1134 x 30 mm), AU CEC version | JinkoSolar (copy hosted by Solarproof) | https://solarproof.com.au/datasheets/panel_datasheet_JKM475-495N-60HL4R-V-F1.3C2-EN-for-AU-CEC.pdf |
| S19 | AIKO Neostar 3P+60 AIKO-A-MCE60Dw dual glass datasheet (1954 x 1134 x 30 mm) | AIKO (copy hosted by EnergyMatters) | https://www.energymatters.com.au/wp-content/uploads/2026/10/aiko-neostar-3pplus60-dual-glass-datasheet.pdf |
| S20 | LONGi Hi-MO 6 LR5-54HTB 410-430M datasheet (1722 x 1134 x 30 mm), AU version | LONGi (copy hosted by Solarproof) | https://solarproof.com.au/datasheets/panel_datasheet_LR5-54HTB430-AU.pdf |
| S21 | Renew G12R TOPCon datasheet RPS3MH66BD (2382 x 1134 x 30 mm), Jan 2026 | Renew | https://solarpv.renew.com/assets/pdf/Renew%20Datasheet-G12R%20TOPCon_003_Jan26.pdf |
| S22 | Heliene HSPE 132HC G12R N-type SL bifacial datasheet Rev.01 (2382 x 1134 x 35 mm) | Heliene | https://heliene.com/wp-content/uploads/HSPE_132HC_G12R_NTYP_SL_Bifacial_Rev.01.pdf |
| S23 | Trina Solar Vertex Series User Manual UM-M-0002-PP7 | Trina Solar | https://www-cdn.trinasolar.com/wwwstorage/sites/5/UM-M-0002-PP7-Trina-Solar-Vertex-Series-User-Manual_EN.pdf |
| S24 | LONGi Photovoltaic Module Installation Manual (LR5-54/66/72 HTH/HTB, LR6, LR4 families) | LONGi (copy hosted on Shopify CDN) | https://cdn.shopify.com/s/files/1/0510/6148/9855/files/LONGI_IM.pdf |
| S25 | Staubli SOL MC4-Evo 2 technical data 11014101 (copy used for cable variants) | Staubli Electrical Connectors (copy hosted on Segen portal) | https://portal.segen.co.uk/reseller/docs/SOL-MC4-Evo-2-11014101-en.pdf |

Search results were used only to find the sources above. None of them is cited for a value. Sources that were searched for the Renhe, Amphenol, Zhejiang Qunli and Staubli split junction box, and for the 1650-1700 and 1762 classes, returned no usable product datasheet.

## 7. Resumen en espanol

Este documento recoge formatos de modulos fotovoltaicos y familias de componentes para modelado 2D/3D. En esta segunda pasada se anadieron 5 formatos nuevos (G12R 2382 x 1134 x 30 mm, Canadian Solar CS6.2-54TM 1961 x 1134 x 30 mm, JinkoSolar 60HL4R 1955 x 1134 x 30 mm, AIKO Neostar 3P+60 1954 x 1134 x 30 mm y LONGi LR5-54HTB 1722 x 1134 x 30 mm con marco de aluminio) y se completaron datos de marco, cajas de conexion, conector MC4-Evo 2 y longitudes de cable. Los valores proceden de fichas tecnicas y manuales de fabricante (LONGi, Jinko, Trina, AIKO, Canadian Solar, Renew, Heliene, Staubli, Prysmian, Maysun, Hirschmann) y se marcan como `unverified`. Lo no encontrado se marca como `not_found` y no se estima.

- Quedan sin encontrar: las clases de 60 celdas de 1650-1700 x 1000-1030 mm, 54/60/66 celdas M6 con celda de 156-166 mm, G12 de 55 y 60 celdas, G12R de 1762 x 1134 mm, y las cajas de conexion partidas de tres piezas (Renhe, Amphenol, Zhejiang Qunli, Staubli) con dimensiones y diodos.
- Los diodos de bypass no tienen corriente ni tension en ninguna ficha consultada; no se copian valores de componentes genericos.
- El marco tiene anodizado de 15 micras (solo una ficha) y los agujeros de fijacion M8 y M6 vienen impresos en dos orientaciones distintas (Trina frente al resto). Las posiciones y las zonas de sujecion no tienen referencia de borde en las fuentes de Trina y LONGi, por lo que no se colocan en `elements`.
- Las normas (IEC 61215, IEC 61730, IEC 62852, EN 50618, IEC 62790, IEC 62941, UL 6703, IEC TS 63126) se citan solo por titulo; no se han consultado sus textos.
- Hay 127 objetos con `status: not_found` en los 14 JSON. Los 14 archivos pasan el esquema `pv_module.schema.json` (jsonschema, Draft 2020-12), sin errores, y todas las fuentes referenciadas existen.
