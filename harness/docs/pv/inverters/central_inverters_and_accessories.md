# Central / utility inverters, power stations and inverter-side accessories

Research for 2D/3D modelling. Facts only, from manufacturer datasheets fetched on 2026-11-20. No PDF or protected text is stored; values are short citations. Status vocabulary: `unverified` = sourced, not yet checked by a person; `typical` = generic industry value, no source; `not_found` = not found in sources, never guessed. Nothing is `verified`.

Machine-readable data: `harness/src/engines/calculation/pv/src/epc_pv/data/pv_inverters/accessories/<id>.json` (25 files, all validated with python3 jsonschema against `pv_inverter.schema.json`).

## 1. Central inverters and power stations (kind = inverter_type)

| id | Type | Rated AC | DC input | AC output | Envelope W x D x H (mm) | Weight | IP | Cooling | Status |
|---|---|---|---|---|---|---|---|---|---|
| sma_sc4000_4600up | SMA Sunny Central 4000-4600 UP | 4000-4600 kVA (35 C) | 1500 V max, 24 DC fused pairs or 32 single | 600/630/660/690 V, 50/60 Hz | 2815 x 1588 x 2318 | < 3700 kg | IP54 electronics, IP34 air duct | Intelligent air (OptiCool), 6500 m3/h | unverified |
| sungrow_sg3125hv_mv | Sungrow SG3125HV-31/-32 | 3125 kVA (50 C) | 1500 V max, 18 inputs std | 630 V (-31) / 660 V (-32), 50/60 Hz | 2280 x 1600 x 2280 (check) | 3200 kg | IP65 | Temp-controlled forced air | unverified |
| huawei_sun2000_215ktl_h0 | Huawei SUN2000-215KTL-H0 (utility string-level) | 215 kW | 1500 V, 9 MPPT, 18 terminals, 30 A/MPPT | 800 V, 3W+PE, 50/60 Hz | 1035 x 365 x 700 | <= 86 kg | IP66 | Smart Air Cooling | unverified (H0, not H3) |
| power_electronics_fs_460vac | Power Electronics FS (HE460VAC) | 1160-2300 kVA (50 C) | 1000 V max, MPPT 651-900 V | 460 VAC, 50/60 Hz (not 600-690 V) | Frame 2: 3370 x 1020 x 2080 (Frame 3: 4400, Frame 4: 5260) | 2500-4500 kg | IP21 | Forced air | unverified |
| tmeic_pvu_l0840urn | TMEIC Solar Ware Ninja PVU-L0840URN | 840 kW (25 C), 765 kW (50 C) | 1500 V max, MPPT 915-1300 V, up to 6 inputs | 630 V (+10/-12%), 50/60 Hz | 1100 x 1100 x 1991 | < 1000 kg | NEMA 3R | Heat pipes + forced air | unverified (preliminary) |
| sma_mvps_5860_6120_s4_us | SMA MVPS 5860/6120-S4-US, 40 ft station | 5866 / 6134 kVA (-25 to 35 C) | 1500 V max | 34.5 kV, 60 Hz | 12192 x 2438 x 2896 (container) | < 32 t | not found (container) | KNAN transformer | unverified (preliminary) |
| sma_mvps_8000_9200_s4_us | SMA MVPS 8000-9200-S4-US, 40 ft station | 6900-7920 kVA nominal; 8000-9200 kVA discharging | 1500 V max | 34.5 kV, 60 Hz | 12192 x 2438 x 2896 (container) | < 32 t | NEMA 3R (IP not found) | KNAN | unverified |
| sungrow_mvs3200_us | Sungrow MVS3200-US skid | 3200 kVA (40 C), 3520 (30 C) | not found | 0.8 kV LV; 12.47-34.5 kV MV, 60 Hz | 6058 x 2438 x 2896 | 14000 kg | Type 3R (IP not found) | KNAN/ONAN oil | unverified |
| ingeteam_powerstation_b_series | Ingeteam Power Station (B Series, MV skid) | up to 7.2 MVA | not found | not found | not found | not found | not found | sealed oil transformer | not_found (partial) |
| kaco_central_not_found | KACO central | not found | not found | not found | not found | not found | not found | not found | not_found |

Notes: the Huawei and Kaco rows are the H0 variant and a placeholder. KACO's fetched datasheet is a 50 kW string inverter, so it is not used as a central type. The Sungrow SG3125HV envelope (2280 x 1600 x 2280 mm) is as sourced, but it is unusual for this class and must be checked before use. The Power Electronics FS sheet is a 460 VAC platform, outside the 600-690 V target.

### 1.1 Skid / station layout (MV power stations)

Sourced layout is the container envelope only. Internal positions of the inverter, MV transformer, RMU and LV panel are not dimensioned in any fetched source.

| Element | Source value | Status |
|---|---|---|
| 40 ft high-cube container (SMA MVPS 5860/6120 and 8000-9200) | 12192 x 2896 x 2438 mm (W x H x D) | unverified |
| MV transformer, KNAN natural ester, Dy11 / YNd11 / YNy0 | kVA per unit and kV ratings not found | not_found |
| MV switchgear, 3 panels (2 cable with load-break, 1 transformer with breaker) | IAC A FL 25 kA 1 s (5860/6120); IAC A FL 20 kA 1 s (8000-9200) | unverified |
| Named RMU model | not found | not_found |
| LV panel | not dimensioned | typical (no value) |
| Sungrow MVS3200-US skid: 6058 x 2896 x 2438 mm, 14000 kg, LV 0.8 kV, MV 12.47-34.5 kV | sourced | unverified |

## 2. Inverter-side accessories (kind = accessory)

| id | Item | Key ratings | Envelope (mm) | Status |
|---|---|---|---|---|
| dc_combiner_16_phoenix_scb_sol_sc16st | DC combiner, 16 strings (Phoenix Contact 1694157) | 1500 V MPP; fuses 15/16/20/25/30/32 A, 10.3 x 85 mm; T2 SPD; DC switch present | not found | unverified |
| dc_spd_type2_abb_ovr_pv_t2 | DC SPD type 2 (ABB OVR PV T2) | 1000/1500 V; In 20/15 kA; Up 4/5 kV (IEC 61643-31) | width 54 mm; H, D not found | unverified |
| dc_switch_disconnector_nhp_nl432pv | DC switch-disconnector (NHP NL432PV) | 1500 V DC, 32 A, 4P, IP66 front, plastic | 99 x 180 x 107 (W x H x D) | unverified |
| ac_disconnect_abb_othv | AC switch-disconnector (ABB OTHV) | 800 / 1000 V AC; 160-2500 A (IEC 60947-3); 3P/4P; padlockable | not found | unverified |
| ac_distribution_box_generic_not_found | AC combiner / distribution box | none sourced | not found | not_found |
| rapid_shutdown_jms_f_reference | Rapid shutdown (NEC 690.12) | Voc 60 V, 15 A, Type 4X, screwless | 89 x 95.5 x 16.5 (L x W x H) | unverified (identity mismatch, see section 4) |
| optimizer_solaredge_p400 | SolarEdge P400 optimizer | 80 V in, 15 A out, 99.5 %, IP68 | 153 x 129 x 33.5 (L x W x H) | unverified |
| optimizer_tigo_ts4_a_o_725w | Tigo TS4-A-O 725 W optimizer | 80 V in, Isc 22 A, Imp 16 A, 99.6 %, IP68 | 139.7 x 138.4 x 22.9 | unverified |
| datalogger_sma_data_manager_m_edmm10 | SMA Data Manager M (EDMM-10) | 10-30 V DC, 4 W, 2 RJ45, RS485, USB, IP20 | 161.1 x 67.2 x 89.7 (W x D x H) | unverified |
| datalogger_huawei_smartlogger3000a | Huawei SmartLogger3000A | AC 100-240 V / DC 12-24 V, 8 W, 3 RS485, 2 Ethernet, IP20 | 225 x 43.6 x 160 (W x D x H) | unverified |
| datalogger_solar_log_1200 | Solar-Log 1200 | up to 100 inverters; Ethernet, RS485/422, RS485, S0 | not found | unverified (partial) |
| energy_meter_sma_emeter20 | SMA EMETER-20 | 230/400 V, direct to 63 A, 1 %, IP2X | 70 x 65 x 88 (W x D x H) | unverified |
| energy_meter_huawei_dtsu666_h_100a | Huawei DTSU666-H, 100 A CT set | RS485 Modbus-RTU 9600, DIN35, accuracy +-0.5 %/1 % | 72 x 65.5 x 100 (W x D x H) | unverified |
| inverter_mounting_bracket_and_shade_cover_not_found | Inverter bracket and shade cover | none sourced | not found | not_found |
| pv_cable_h1z2z2k_gland_set | PV cable H1Z2Z2-K 1x6 mm2 and gland set | 1.0/1.0 kV AC, 1.5/1.5 kV DC, 90 C, EN 50618 | 6 mm2 diameter not captured | unverified (partial) |

## 3. Common physical parts (per unit, where sourced)

- Combiner (`dc_combiner_16_phoenix_scb_sol_sc16st`): 16 string fuse holders (quantity 16 sourced), 1 DC switch-disconnector, 1 DC SPD type 2. Enclosure, DIN rail, glands, lock, gasket and labels are generic (`typical`, no values).
- DC SPD: 1 module, 3 DIN-rail modules wide (54 mm).
- Optimizers: 1 housing, 2 leads, 1 mounting feature (P400: single bolt, hole pattern not found).
- Loggers and meters: housing, RJ45 Ethernet, RS485, DIN-rail mount. Mounting-hole spacing is not found for any item, so no mounting-hole elements were written.

## 4. Gaps and issues (read before use)

1. Kaco: no central inverter datasheet found (only a 50 kW string unit).
2. Ingeteam Power Station: only the 1.17-7.2 MVA range; dimensions, voltages, IP and weight not found.
3. Sungrow MVS3200-US: DC input values not found (the source title refers to a 1500 V string inverter).
4. Rapid shutdown: the file named as an SMA SunSpec RSD datasheet (files.sma.de) has content identifying the model as JMS-F. The publisher is unconfirmed, so this entry is a reference only.
5. Mounting-hole patterns are not found for any item, so no hole elements were written; the 2D/3D model needs drawings for these.
6. Mounting brackets and shade covers: no datasheet found.
7. AC combiner / distribution box: no datasheet found.
8. PV cable: outer diameter, weight per km and bending radius for 6 mm2 were not captured (the source gives ranges). The gland set is generic.
9. Huawei SUN2000-215KTL-H3 was not found; the H0 datasheet was used.
10. The Power Electronics FS sheet is a mirror (EnfSolar), not the manufacturer URL. The SolarEdge P400 sheet is a mirror (vanmeterinc) too.
11. Solar-Log 1200: dimensions, weight, IP, power supply not found.
12. Certifications were not captured for several items.

## 5. Sources

| id | Document | Publisher | URL |
|---|---|---|---|
| S01 | SC4xxxUP datasheet (SC 4000-4600 UP) | SMA | https://files.sma.de/downloads/SC4xxxUP-DS-en-33.pdf |
| S02 | SG3125HV-31/-32 datasheet V19 | Sungrow | https://info-support.sungrowpower.com/application/pdf/2024/12/28/DS_20241224_SG3125HV-31_SG3125HV-32_Datasheet_V19_EN.pdf |
| S03 | SUN2000-215KTL-H0 datasheet | Huawei | https://solar.huawei.com/admin/asset/v1/pro/view/1f323ce3ca7c41a89cdb56ad7cadfd66.pdf |
| S04 | Power Electronics FS (HE460VAC) product sheet, mirror | Power Electronics | https://cdn.enfsolar.com/Product/pdf/Inverter/597029e754a4d.pdf |
| S05 | Solar Ware Ninja PVU-L0840URN | TMEIC | https://www.tmeic.com/sites/default/files/assets/files/Solar%20Ware%20Ninja%20PVU-L0840URN-0424-web.pdf |
| S06 | MVPS 5860/6120-S4-US datasheet (preliminary) | SMA America | https://files.sma.de/downloads/MVPS5.8-6.1-US-DS-en_us-18.pdf |
| S07 | MVPS 8000-9200-S4-US datasheet | SMA America | https://files.sma.de/downloads/MVPS8.0-9.2-US-DS-en_us-21.pdf |
| S08 | MVS3200-US datasheet V19 | Sungrow | https://info-support.sungrowpower.com/application/pdf/2025/01/14/DS_20250107_MVS3200-US_Datasheet_V19_EN(NA).pdf |
| S09 | Ingeteam Power Station B Series catalog excerpt | Ingeteam (via DirectIndustry) | https://pdf.directindustry.com/pdf/ingeteam-gmbh/powerstation-fsk-b-series/4563152-1038086.html |
| S10 | SCB SOL SC 16ST, order 1694157 | Phoenix Contact | https://www.phoenixcontact.com/en-gb/products/string-combiner-box-scb-sol-sc-16st-p-1-xf-00231-1694157 |
| S11 | OVR PV T2 | ABB | https://new.abb.com/low-voltage/products/system-pro-m/surge-protective-devices-ovr-old/ovr-pv-t2 |
| S12 | NL432PV DC isolator | NHP | https://www.nhp.com.au/product/NL432PV |
| S13 | OTHV disconnectors | ABB | https://electrification.us.abb.com/products/switches-disconnects/othv-disconnects |
| S14 | Rapid shutdown datasheet (content: JMS-F) | not confirmed | https://files.sma.de/downloads/SMASunSpecRSD-DS-en-23.pdf |
| S15 | P400/P401/P485/P505 datasheet, mirror | SolarEdge | https://media.vanmeterinc.com/image/upload/v1715561357/marketing/solar/inverters/SolarEdge/SolarEdge%20P%20Series/P400-P401-P485-P505.pdf |
| S16 | TS4-A-O 725 W data sheet, reseller copy | Tigo | https://ressupply.com/documents/tigo/TS4-A-O_(725W)_Data_Sheet.pdf |
| S17 | Data Manager M EDMM-10 datasheet | SMA | https://files.sma.de/downloads/EDMM-10-DS-en-42.pdf |
| S18 | SmartLogger3000A Europe datasheet, distributor copy | Huawei | https://solar-distribution.baywa-re.pl/out/media/08-000429_SmartLogger3000A-Europe.pdf |
| S19 | Solar-Log 1200 datasheet, distributor copy | Solar-Log | https://www.vpsolar.com/download/catalog/Monitoraggio/Solar-Log/Solar-Log-1200/SolarLog_Datasheet_Solar-Log_1200_EN.pdf |
| S20 | EMETER-20 datasheet | SMA | https://files.sma.de/downloads/EMETER-20-DS-en-30.pdf |
| S21 | DTSU666-H 100 A specifications | Huawei | https://solar.huawei.com/en/products/DTSU666-H-100A/specs |
| S22 | TECSUN(PV) H1Z2Z2-K datasheet | Prysmian | https://www.prysmian.com/sites/www.prysmian.com/files/media/documents/Tecsun-PV-_H1Z2Z2-K.pdf |
| S23 | PEBS-L weatherproof enclosure datasheet (reference only) | Segen | https://portal.segen.co.uk/reseller/docs/Datasheet_PEBS-L%20Weatherproof%20Enclosure.pdf |
| S24 | ERS01324DC datasheet (alternative DC switch, reference) | not confirmed | https://cdn.yesss.co.uk/documents/2395600_03_ERS01324DC_Datasheet_ca72413a4f24ed57e235ecb6e947033b.pdf |
| S25 | blueplanet 50.0 TL3 (string, reference only) | KACO | https://krannich-solar.com/fileadmin/user_upload/GR/Products/Inverter/Kaco/DTS_BP-50TL3-en_M___XL.pdf |
| S26 | Requirements for mounting, STP TL-30 manual | SMA | https://manuals.sma.de/STPTL-30/en-US/391431051.html |

## 6. Unverified list (all values need a person to check against the datasheet)

- Every sourced value above is `unverified`. None is `verified`.
- `typical` (no source): all generic parts flagged `typical` in the JSON files (DIN rails, glands, locks, gaskets, labels, grounding terminals, generic cable leads, LV panel in the MV stations).
- `not_found`: Kaco central; Ingeteam dimensions, weight, voltages and IP; AC combiner box; mounting bracket and shade cover; Solar-Log 1200 dimensions and power; MVS3200 DC voltage; MVPS transformer kVA per unit and RMU model; NL432PV weight and padlock; PV cable 6 mm2 diameter, weight and bending radius; SmartLogger antenna dimensions; mounting-hole patterns for all items.

---

## Resumen en español

**Qué se hizo.** Se consultaron hojas técnicas de fabricantes (vía búsqueda web y lectura de las fuentes, sin almacenar PDF ni texto protegido) para inversores centrales, estaciones de potencia en skid y accesorios del lado del inversor. Se generaron 25 archivos JSON en `harness/src/engines/calculation/pv/src/epc_pv/data/pv_inverters/accessories/`, todos validados con python3 jsonschema contra `pv_inverter.schema.json` (0 fallos).

**Resultados.** Diez archivos de inversor o estación: ocho con datos sourced (SMA SC 4000-4600 UP, Sungrow SG3125HV-MV, Huawei SUN2000-215KTL-H0, Power Electronics FS 460 VAC, TMEIC PVU-L0840URN, SMA MVPS 5860/6120 y 8000-9200, Sungrow MVS3200-US), más Ingeteam B Series (parcial) y Kaco (no encontrado). Y 15 archivos de accesorios. Cuatro archivos tienen estado `not_found` completo: Kaco central, Ingeteam (solo rango de potencia), caja combinadora CA y soporte/cubierta del inversor.

**Huecos.** No hay dimensiones de montaje (agujeros) para ningún elemento; no hay fuente para el transformador MT por unidad ni el modelo de RMU; el SMA RSD consultado identifica el modelo JMS-F, por lo que se usa solo como referencia; la variante H3 de Huawei no se encontró; el cable 1x6 mm2 no tiene diámetro exterior capturado.

**Qué debe revisar una persona.** Todo valor sourced está en `unverified`. Nada se marcó `verified`. La envolvente del Sungrow SG3125HV (2280 x 1600 x 2280 mm) debe comprobarse con el plano.

**Sources.** Ver sección 5 (S01-S26) con URL.
