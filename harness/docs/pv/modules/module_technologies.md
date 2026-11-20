# PV module technologies: research for 2D/3D modelling

Scope: module and cell technologies (`kind = "technology"`). Each technology has a JSON file in
`harness/src/engines/calculation/pv/src/epc_pv/data/pv_modules/technologies/<id>.json`, validated against
`pv_module.schema.json` (jsonschema draft 2020-12, all 13 pass).

Rules applied: facts only with short citations; no PDFs or protected text stored; no value invented.
Status meanings: `unverified` = sourced from a cited page, not yet approved; `typical` = generic industry
value, not from a source; `not_found` = not stated in any source reached, never guessed. No status is `verified`
(only a person may set that).

Research date: 2026-11-20. Sources are manufacturer datasheets or distributor copies, plus IEC, Fraunhofer ISE
papers and aggregator pages. Where the source is a distributor copy, an aggregator or a lab-module paper, this is stated.

## 1. Technology overview (EN)

| id | Technology | Cell notes (sourced) | Reference module (sourced) | Size mm (L x W x T) | Weight kg | Module eff. % | Frame | Status |
|---|---|---|---|---|---|---|---|---|
| `perc` | Mono PERC (bifacial variant) | 60 cells (6x10), mono PERC | JA Solar JAM60D00 300-320/BP | 1675 x 998 x 30 | 25.1 | not_found | anodized Al, height 30 | unverified |
| `topcon` | TOPCon n-type | n-type TOPCon mono, 132 cells (66x2) | JinkoSolar JKM610-635N-66HL4M | 2382 x 1134 x 35 | 28.2 | 22.58 - 23.51 | anodized Al alloy | unverified |
| `hjt` | HJT heterojunction | HJT, 80 half-cut bifacial (REC); 120 half cells SmartWire (Meyer Burger) | REC Alpha Pure-R | 1730 x 1118 x 30 | 21.5 | 20.7 - 22.3 | anodized black Al | unverified |
| `ibc` | IBC / back contact | LONGi HPBC 108 cells (6x18); Maxeon IBC 120 cells | LONGi Hi-MO 6 HPBC LR5-54HTH | 1722 x 1134 x 30 | 20.8 | 21.3 - 22.3 | anodized Al alloy | unverified |
| `polycrystalline` | Polycrystalline | cell type 'Poly', 120 cells (6x20) as stated | JA Solar JAP60S10 275-295/SC | 1689 x 996 x 35 | 18.7 | 16.3 - 17.5 | anodized Al, height 35 | unverified |
| `half_cell` | Half-cell layout | 80 (REC), 156 (Qcells), 132 = 66x2 (Jinko) | REC Alpha Pure-R | 1730 x 1118 x 30 | 21.5 | 20.7 - 22.3 | anodized Al | unverified |
| `bifacial_dual_glass` | Bifacial dual glass | 132 cells mono bifacial (Trina); 156 half (Qcells) | Trina Vertex N dual-glass | 2384 x 1134 x 30 | 33.1 | up to 22.4 | anodized Al (30 mm) | unverified |
| `shingled` | Shingled, bifacial N-type TOPCon matrix | 390 shingle cells (matrix technology) | Heckert APOLLON 2.0 (preliminary datasheet 03/2026) | 1762 x 1134 x 30 | 23.5 | 22.5 - 23.0 | black anodized Al, height 30 | unverified |
| `cdte` | CdTe thin film | monolithic, up to 268 cells | First Solar Series 7 TR1 | 2300 x 1216 x not_found | 38.46 - 39.7 (TR1); 36.8 (FT1, NEPD) | 18.1 - 19.3 | none (frameless) | unverified |
| `cigs` | CIGS thin film | cell type CIGS; substrate not stated | Avancis SKALA | 1587 x 664 x 38 | 17 | 11.4 - 13.3 | none (frameless) | unverified |
| `bipv_transparent` | BIPV / semi-transparent | mono c-Si 156 mm, spaced; 28-60 cells | BISOL Lumina BMO | 1649 x 991 x 35 | 18.3 | 8 - 17 (transparency 6.2 - 53 %) | anodized Al, BIPV or frameless variants | unverified |
| `flexible_lightweight` | Flexible CIGS film (glass-free) | CIGS flexible, cell count not stated | Miasole FLEX-03NS series | 1709 x 348 x 2.5 (1.6 w/o adhesive) | 1.1 - 1.3 | 15.3 - 18.3 (aperture) | none | unverified |
| `opv_flexible` | Flexible organic (OPV) film | organic triple junction, NOT CIGS | Heliatek HeliaSol 436-2000-AFA | 2000 x 436 x 1.8 | 1.6 | 7.2 - 8.0 (aperture) | none | unverified |

Notes:
- Module efficiency is kept in `mechanical_ratings.module_efficiency_pct_range`, not in `cell`, because the
  sources give module efficiency only (the LONGi page gives "higher than 25 %" for the HPBC cell only).
- Sizes in the table follow the datasheet order. The EnfSolar listings are no longer used.
- The Sunman eArc (glass-free mono-Si, 1503 x 689 x 5.6 mm, 3.9 kg) is a second reference inside
  `flexible_lightweight.json` under `mechanical_ratings.reference_sunman_earc_mono_si_glass_free`.
- The Solar Frontier SF170-S (CIS, framed, 1257 x 977 x 35 mm, 20 kg) is a reference inside `cigs.json`.

## 2. Laminate stack, front to back (sourced plus generic)

Sourced front glass: 3.2 mm (PERC, TOPCon, HJT, IBC, poly, BIPV, half-cell, Maxeon, CIGS Avancis and Solar Frontier),
2.0 mm front and rear (Trina, Qcells dual glass, Heckert shingled), 3.2 mm glass with a plastic rear film (Solar Frontier).

Lab-module thicknesses (Fraunhofer ISE, EU PVSEC 2019, paper 4CO43; status `unverified`, a generic reference, not
from the product datasheet): EVA 0.45 mm per side (nominal), solar cell 0.18 mm, backsheet 0.35 mm (only where a
backsheet is stated). These replace the earlier generic 0.5 / 0.2 / 0.3 mm values in the crystalline entries.

Generic `typical` values still in use: front glass 3.2 mm where the datasheet does not state it (PERC JA, poly JA).

| Technology | Front (mm) | Encapsulant | Cells | Rear | Source of rear |
|---|---|---|---|---|---|
| PERC | glass 3.2 (typical, not stated by JA) | EVA/POE 0.45 (Fraunhofer) | PERC cells 0.18 | not stated, 0.35 reference only | not_found |
| TOPCon | glass 3.2 AR (unverified) | EVA/POE 0.45 (Fraunhofer) | n-type TOPCon 0.18 | backsheet or glass, not stated | not_found |
| HJT | glass 3.2 AR (unverified) | EVA/POE 0.45 (Fraunhofer) | HJT 0.18 | polymer backsheet, black (REC) | unverified |
| IBC | glass 3.2 AR (unverified) | EVA/POE 0.45 (Fraunhofer) | back contact 0.18 | white backsheet (Maxeon) | unverified |
| Poly | glass 3.2 (typical, not stated by JA) | EVA/POE 0.45 (Fraunhofer) | poly cells 0.18 | not stated, 0.35 reference only | not_found |
| Half-cell | glass 3.2 (REC) | EVA/POE 0.45 (Fraunhofer) | half cut 0.18 | polymer backsheet (REC) | unverified |
| Bifacial dual glass | glass 2.0 HS AR (unverified) | EVA/POE 0.45 (Fraunhofer) | bifacial mono 0.18 | glass 2.0 HS white grid (unverified) | unverified |
| Shingled | glass 2.0 semi-tempered AR (Heckert) | EVA/POE 0.45 (Fraunhofer) | shingled TOPCon 0.18 | rear glass 2.0 (Heckert) | unverified |
| CdTe | heat-strengthened glass, thickness not_found | laminate with edge seal, not_found | CdTe layer, thickness not_found | heat-strengthened glass, not_found | unverified |
| CIGS | glass 3.2 single pane (Avancis, SF170-S) | not_found | CIGS on substrate, not_found | plastic film (SF170-S) or back glass, not_found | not_found |
| BIPV | glass 3.2 tempered low-iron AR (unverified) | EVA/POE 0.45 (Fraunhofer) | spaced mono c-Si 0.18 | not stated | not_found |
| Flexible CIGS | polymer laminate, total 1.6 mm (not split) | adhesive, 0.9 mm derived from 2.5 - 1.6 | CIGS flexible, not_found | not stated | not_found |
| OPV (flexible) | polymeric film, thickness not_found | adhesive tape | organic layer, not_found | black film, not_found | unverified |

## 3. Frames, junction boxes, connectors, cables

- Frames: aluminium alloy, anodized, in every framed datasheet reached (black anodized for REC, Maxeon and Heckert).
  Height is sourced where the datasheet gives the module thickness (30 to 40 mm). Profile section and
  width are not stated in the sources, so the frame footprint width of 30 mm is `typical`.
- Junction boxes: IP68 is the most common claim (TOPCon, HJT, IBC, bifacial, CdTe, shingled, poly, PERC, flexible CIGS).
  IP67 for CIGS (Avancis, SF170-S) and OPV. IP65 for the old EnfSolar PERC listing (no longer used).
  Bypass diodes: 3 (LONGi HPBC, BISOL, Heckert, JA Solar PERC and poly), 2 (Maxeon).
- Connectors: MC4 or compatible (most), Stäubli MC4 PV-KBT4/KST4 (REC), Stäubli MC4-EVO 2 (Heckert), QC 4.10-35 (JA Solar),
  TE PV4-S (First Solar, OPV), H4 (Avancis, Miasole).
- Cables: 4 mm2 (most crystalline, JA Solar, Heckert, Sunman), 2.5 mm2 (First Solar, Avancis, SF170-S),
  length 1200 mm (Heckert), 650 mm (First Solar TR1), 500 mm (First Solar FT1), not stated (JA Solar).
- Standards: IEC 61215 (design qualification and type approval), IEC 61730 (safety), IEC 61701 (salt mist corrosion),
  IEC TS 63209-1 (extended-stress tests, see below). IEC 62716 (ammonia), IEC 62804 (PID), IEC TS 62941 (JA Solar),
  IEC 62790 (junction box, Heckert), UL 61730 and UL 1703 appear in datasheets.

## 4. Standards

- IEC TS 63209-1:2021 is a Technical Specification that supplements IEC 61215 baseline tests. It lists five extended-stress
  test sequences: thermal fatigue, mechanical stress, sequential UV-to-back, damp heat, and PID. It is for comparative
  analysis, not pass-fail or life prediction, and was developed mainly for crystalline silicon modules. (IEC/VDE preview, see sources.)
- IEC 61215-1 and IEC 61730-1 scope: datasheets use the phrases "design qualification and type approval" and
  "safety qualification". The full scope texts were not fetched (VDE preview redirected), so the scope lines are `unverified`.
- IEC 61701: salt mist corrosion testing, severity levels. Cited from the IEC publication page. Some datasheets list it only as an extended test (First Solar), or as "under certification" (Heckert).
- Not reached: IEC TS 63209-2 (listed in search only).

## 5. Gaps and conflicts

- Shingled: the Heckert APOLLON 2.0 preliminary datasheet (03/2026) gives geometry, cells, weight and frame. The TCL MI590 page
  is still mostly unreadable and is used only for the cell-layout and standards lines. Cell size is not stated.
- CdTe: module thickness, glass thickness and CdTe layer thickness are not stated in the TR1, FT1 or NEPD sources. Elements are left empty.
  Weight differs by model (38.46 to 39.7 kg for TR1; 36.8 kg for FT1 and NEPD). Both are kept.
- CIGS: the Avancis SKALA entry is kept. The Solar Frontier SF170-S is listed as CIS (cadmium-free), not CIGS, and is a reference only.
  The CIGS absorber of 0.2 um comes from a lab cell (MDPI), not from a module datasheet, and is not used in geometry.
  Layer stack below the glass is not stated in any module datasheet reached.
- Flexible CIGS: Miasole FLEX-03NS (2019, Japanese-language datasheet). Substrate, bend radius and cell count are not stated.
  The adhesive backing thickness (0.9 mm) is derived as 2.5 mm (with adhesive) minus 1.6 mm (without), not a stated layer.
- OPV (Heliatek sample), now `opv_flexible.json`: the label says "prototype, for testing purposes exclusively"; the label and datasheet
  conflict on bend radius (200 vs 500 mm) and max system voltage (below 50 V vs 1000 V). Both values are kept as `unverified`
  under `mechanical_ratings.conflict_values`.
- PERC: JA Solar JAM60D00 is a bifacial mono PERC datasheet. Efficiency, glass type, rear type and cable length are not stated.
- Polycrystalline: JA Solar JAP60S10 states 120 cells (6x20), while the earlier aggregator listed 60 cells. The sourced 120 is kept; the layout must be confirmed.
- Trina Vertex N: cell type (n-type/TOPCon) is not stated in the extracted text; the model name is NEG19RC.20.
- LONGi HPBC: the datasheet describes "54-cell class" and "108 cells (6x18)"; the wording is unexplained.
- Maxeon MAX7: a 120-cell module (1913 x 1035 mm). Only the LONGi reference is modelled in geometry. Maxeon values are in `mechanical_ratings.maxeon_reference`.
- Fraunhofer ISE values (EVA 0.45 mm, cell 0.18 mm, backsheet 0.35 mm) are lab-module references. Frame footprint widths and junction box sizes/placements (except CIGS) are `typical`.

## 6. Comparison table for modelling

| id | Layers used for 2D/3D | Frame in model | Elements | Ready for production use |
|---|---|---|---|---|
| perc | 5 (glass typical, EVA, cells, EVA, rear not_found) | yes, height 30 (typical width) | 10 | no (typical glass, rear not stated) |
| topcon | 5 | yes, height 35 | 10 | no (typical glass note, rear not_found) |
| hjt | 5 | yes, height 30 | 10 | no |
| ibc | 5 | yes, height 30 | 10 | no |
| polycrystalline | 5 (glass typical, rear not_found) | yes, height 35 (typical width) | 10 | no (cell count conflict) |
| half_cell | 5 | yes, height 30 | 10 | no |
| bifacial_dual_glass | 3 (glass, cells, EVA) | yes, height 30 | 10 | no |
| shingled | 5 (glass 2.0 both sides) | yes, height 30 (typical width) | 10 | no (preliminary datasheet, typical JB) |
| cdte | 5, thickness not_found | no (frameless) | 0 | no (thicknesses not_found) |
| cigs | 1 (glass) plus junction box | no (frameless) | 2 | no |
| bipv_transparent | 5 | yes, height 35 | 10 | no |
| flexible_lightweight | 2 (laminate 1.6 mm, adhesive 0.9 mm derived) | no | 2 | no (substrate not stated) |
| opv_flexible | 1 film | no | 1 | no (prototype conflict) |

## 7. Sources (URL, accessed 2026-11-20)

- First Solar Series 7 TR1 datasheet, https://firstsolar.com/-/media/First-Solar/Technical-Documents/Series-7/Series-7-TR1-Datasheet.ashx
- First Solar Series 7 FT1 datasheet, https://firstsolar.com/-/media/First-Solar/Technical-Documents/Series-7/Series-7-FT1-Datasheet.ashx?la=en
- NEPD-5039-4377 First Solar Series 7 (environmental declaration), https://epd-global.com/getfile.php/1345010-1695811928/EPDer/Byggevarer/NEPD-5039-4377_First-Solar-Series-7-Photovoltaic-Module.pdf
- REC Alpha Pure-R product datasheet, https://www.recgroup.com/sites/default/files/2025-02/PRINT_DS_Alpha_Pure-R_ENa.pdf
- JinkoSolar JKM610-635N-66HL4M (V) F2 datasheet, https://www.jinkosolar.com/uploads/JKM610-635N-66HL4M-(V)-F2-EN.pdf
- SunPower / Maxeon MAX7 datasheet, https://sunpowerglobal.com/us/sites/default/files/2025-02/sp_max7_120c_455_ds_en_a4_mc4_553945.pdf
- LONGi Hi-MO 6 Explorer LR5-54HTH datasheet (distributor copy), https://krannich-solar.com/fileadmin/user_upload/JP/Blog/PV_EXPO2023_2023-04-18/230418_LR_5_54_HTH_415_435_M_Explorer_20230123cp_ab3059a951.pdf
- LONGi Hi-MO 6 Explorer product page (HPBC cell efficiency), https://longi.com/au/products/modules/hi-mo-6-explorer
- Trina Vertex N TSM-NEG19RC.20 bifacial dual-glass datasheet, https://pages.trinasolar.com/rs/567-KJK-096/images/Datasheet_Vertex_NEG19RC.20_EN_2023.pdf
- Hanwha Q CELLS Q.PEAK DUO XL-G10 BFG datasheet, https://cdn.shopify.com/s/files/1/0682/6786/8458/files/Qcells_Data_sheet_Q.PEAK_DUO_XL-G10-BFG_series_475-490_DA_2022-07_Rev01_NA.pdf
- Heckert Solar APOLLON 2.0 preliminary datasheet (03/2026), https://www.heckertsolar.com/media/b8/83/80/1781609715/202603_Datasheet_Apollon2.0.pdf
- TaiyangNews article on Heckert shingled module (cross-check), https://taiyangnews.info/technology/heckert-solar-shingled-matrix-technology-germany
- JA Solar JAM60D00 300-320/BP datasheet (copy via EnfSolar CDN), https://cdn.enf.com.cn/Product/pdf/Crystalline/5c25d762e6005.pdf
- JA Solar JAP60S10 275-295/SC datasheet (distributor copy), https://www.solarquotes.com.au/wp-content/uploads/2019/06/ja-solar-jap60s10-datasheet.pdf
- Avancis SKALA datasheet, https://www.avancis.de/_Resources/Persistent/c/0/8/3/c083f531a34668ad66e7642c86ae69c251bfa039/SKALA_data%20sheet_EN_220725.pdf
- Solar Frontier SF170-S S-Series data sheet (distributor copy), https://www.santansolar.com/wp-content/uploads/Data_Sheet_S-Series_SF170_ENG__DSSG1-38-PEE42_.pdf
- Miasole FLEX-03NS series datasheet (Japanese, 2019), https://miasole.com/wp-content/uploads/2022/07/flex-03n-1.7m_datasheet_jp-2019.pdf
- Sunman eArc eASMD160M-4X09 brochure (distributor copy), https://www.solar4rvs.com.au/assets/brochures/eASMD160M4x9.pdf
- CIGS research cell, 0.2 um absorber (MDPI Energies 16(7):2956), https://www.mdpi.com/1996-1073/16/7/2956
- Pfreundt et al., EU PVSEC 2019 paper 4CO43 (Fraunhofer ISE, lab-module thicknesses), https://www.ise.fraunhofer.de/content/dam/ise/de/documents/publications/conference-paper/36-eupvsec-2019/Pfreundt_4CO43.pdf
- BISOL Lumina BMO / BSO / BLO datasheet, https://res.cloudinary.com/gpceurope/image/upload/v1551963293/Datasheet-Bisol-Lumina-BMO-BSO-BLO-Datasheet_BISOL_Lumina_BMO_BSO_BLO_EN_91220.pdf
- Heliatek HeliaSol 436-2000-AFA datasheet Rev 09, https://heliatek.com/fileadmin/user_upload/pdf_documents/HeliaSol_436-2000-AFA_50-55W_-_EN_-_Rev_09.pdf
- TCL MI590 datasheet (partly unreadable), https://tcl.com/content/dam/brandsite/global/photovoltaic/product-pages/pv-module/download/tcl-mi590.pdf
- IEC TS 63209-1:2021 preview (VDE), https://www.vde-verlag.de/iec-normen/preview-pdf/info_iects63209-1{ed1.0}en.pdf
- IEC 61701:2020 publication page, https://webstore.iec.ch/publication/59588
- IEC 61215-1 preview (VDE; search result, not fetched), https://www.vde-verlag.de/iec-normen/preview-pdf/info_iec61215-1{ed2.0}b.pdf
- IEC 61730-1 preview (VDE; search result, not fetched), https://www.vde-verlag.de/iec-normen/preview-pdf/info_iec61730-1{ed3.0}b.pdf

## 8. Unverified list (for review)

1. All `unverified` values come from the cited pages above, and none is approved.
2. Frame footprint width 30 mm, and junction box size and placement (except CIGS), are `typical`. Front glass 3.2 mm is `typical` where the datasheet is silent (PERC, poly).
3. Fraunhofer ISE lab-module values (EVA 0.45 mm, cell 0.18 mm, backsheet 0.35 mm) are generic references, not product values.
4. Not found in any source: CdTe, CIGS and flexible CIGS layer thicknesses; CdTe module thickness; shingled cell size; PERC module efficiency and rear type; poly rear type; OPV layer thicknesses; Trina cell type; flexible CIGS substrate and bend radius.
5. Standards scope lines for IEC 61215-1 and 61730-1 are from search titles and datasheet wording, not from the full text.
6. Heliatek datasheet vs label conflicts (bend radius, max system voltage) are unresolved; both values are kept as `unverified`.
7. Preliminary datasheets (Heckert 03/2026) and distributor or aggregator copies (JA Solar via EnfSolar CDN and SolarQuotes, Solar Frontier via Santan Solar, Miasole 2019) need a check against the maker's current version.
8. Not reached: official Fraunhofer ISE, Canadian Solar or Meyer Burger module datasheets; the full texts of IEC 61215-1 and 61730-1.

Remaining `not_found` fields across the 13 files: 27 (cdte 5, cigs 7, bipv_transparent 4, perc 3, polycrystalline 3, topcon 2, flexible_lightweight 2, opv_flexible 1).

---

## Resumen en español

Documento de investigacion sobre trece tecnologias de modulos fotovoltaicos para modelado 2D y 3D. Se incluye una
ficha JSON por tecnologia en `harness/src/engines/calculation/pv/src/epc_pv/data/pv_modules/technologies/`, todas validadas
contra el esquema. Solo se usan datos citados de fichas de fabricantes (Jinko, REC, Maxeon, LONGi, Trina, Hanwha Q CELLS,
First Solar, Avancis, BISOL, Heliatek, TCL, Heckert, JA Solar, Solar Frontier, Miasole, Sunman), de un articulo de
TaiyangNews, de un articulo del MDPI, de un articulo de Fraunhofer ISE y de paginas IEC. Ningun valor esta marcado como verificado.
Los valores genericos figuran como `typical` y los no encontrados como `not_found`.

Cambios de esta revision: shingled con ficha Heckert APOLLON 2.0 (390 celdas, 1762 x 1134 x 30 mm); CdTe con datos de TR1,
FT1 y NEPD (peso, area, conector, cable); CIGS con Solar Frontier SF170-S como referencia; flexible separado en CIGS
flexible (Miasole FLEX-03NS) y OPV (Heliatek, ahora `opv_flexible`); PERC y policristalino con fichas de JA Solar en lugar
del agregador; espesores de EVA, celda y backsheet tomados de un articulo de Fraunhofer ISE (valores de modulo de laboratorio).

Lagunas principales: la capa de CdTe y la de CIGS no tienen espesor de capa en ninguna ficha; la ficha Heliatek contradice su
etiqueta (radio de curvatura y tension maxima; ambos valores se conservan como no verificados); el CIGS flexible no indica
sustrato ni radio de curvatura; la ficha JA Solar del policristalino indica 120 celdas. Quedan 27 campos `not_found`.
Pendiente: fichas oficiales de Fraunhofer ISE, Canadian Solar y Meyer Burger, y los textos completos de IEC 61215-1 y 61730-1.
