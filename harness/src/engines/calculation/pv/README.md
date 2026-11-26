# epc_pv

Photovoltaic engine: the hourly energy yield of a grid-connected plant and the string layout of its arrays against the inverter limits. Pure Python, no dependencies, deterministic (same input, same output; no clock, no randomness, no network).

## What it does
- Sun position (NOAA equations, about 0.01 degree) and extraterrestrial irradiance (Spencer) of every hour of the weather file.
- Plane-of-array irradiance of every array: Hay-Davies (default) or isotropic sky diffuse, ground reflection, and the ASHRAE angle-of-incidence loss on the direct part.
- Cell temperature (Faiman), DC power (PVWatts), combined losses, and the inverter curve with clipping (PVWatts inverter).
- String layout: modules in series from the cold open-circuit voltage, the hot maximum-power voltage and the MPPT window; whole strings; inverter count from a DC/AC ratio or given; input-current check per MPPT.
- Per array and in total: DC and AC energy, monthly energy, specific yield, performance ratio, capacity factor, peak power and the energy lost by clipping.
- Every text the user can see (warnings, errors, labels) comes in English and Spanish.

## How it is used
```
python -m epc_pv INPUT.json --out DIR       # writes DIR/pv_yield.json
```
or `from epc_pv import run; run(document).as_dict()`. Input and output follow `src/epc_pv/schema/*.schema.json`; the result carries `schema_version`, `counts`, `warnings` (each with `code`, `en`, `es`) and `labels`. An invalid input raises `PvError` (`str(e)` is English, `e.es` Spanish; the CLI prints both and exits 1).

**Orientation and roof:** `epc_pv.orient.optimal` chooses the tilt and azimuth of a fixed plane for the site (facing the equator, tilt searched with the yield engine on the weather year), so the person does not have to know them; `epc_pv.plan_roof` places the modules on roof planes (portrait or landscape, margins, obstacles) and returns one array per plane. Stage 3 uses both when the `pv` section leaves the orientation out or carries a `roof`, and says what it chose in a finding. A roof's real pitch and azimuth, when known, win over the engine's choice. Several planes are several arrays (one orientation per array, so one MPPT never mixes orientations). `epc_pv.roofdxf.read` takes the planes, obstacles and optional tilt/azimuth from an ASCII DXF of the roof (layers `291-W-ROOF-N`, `291-W-OBST-ROOF-N`, `291-W-ROOF-NOTE`; rectangles aligned with the axes; units from `$INSUNITS`). The drawings come from `epc_drawing.pv_roof`. Not covered: wind uplift and ballast (no wind value in the norm register; every roof result carries the warning `roof_wind_pending`), shade cast by obstacles on the modules, planes that are not axis-aligned rectangles.

**PVGIS weather step:** `python -m epc_pv.weather --lat LAT --lon LON --utc-offset -3 --out DIR` asks the `tmy` tool of PVGIS (European Commission JRC, `re.jrc.ec.europa.eu`, v5.3) once and writes `DIR/weather_pvgis.json` with the engine `weather` block and its `source` (database, years, coordinates, date of the query, citation, status `pending review`). It is a separate data step: `epc_pv.run` still never reads the network. The typical year joins months of different years, so every hour is moved to one reference year (no leap day) and to local standard time; wind is at 10 m as PVGIS gives it. Tests use a recorded-shape answer, never the network.

The weather is an input: hourly `ghi`, `dni`, `dhi` (W/m2), `temp_air_c` and `wind_ms` from a typical-year file (PVGIS TMY or a measured year). The engine never reads the network. Azimuth is measured from north, clockwise: in the southern hemisphere a plane facing the sun has azimuth 0.

**Equipment data (`epc_pv.equipment`):** inverters (derived from `data/pv_inverters/inverters`, one record per model; a model without a plain number for a needed value is a gap, see `inverter_gaps()`), mounting structures (`structures()`, `foundation(id)`: the embedment depth is the record's, never assumed), module formats and technologies, inverter accessories and the feasibility references. Give `structure_id` in the `layout` (or `flat_roof`, a roof structure) to carry the foundation into the layout and the 3D model (buried parts on layer `291-WS-FNDN-N`). All values are pending review.

## Depends on
Nothing (standard library). `pvlib` is used only by the developer tool `tests/validation/make_reference.py` to write the reference of the validation; it is never installed with the product.

## Validation
`tests/test_validation.py` compares 1000 synthetic projects (1 MWp to 500 MWp, one to three arrays each, sites all over Argentina, four module types and four inverter types) with pvlib 0.16.1 using the same models. The target is 99.98 %: the annual DC and AC energy and the plane-of-array irradiation of every array within 0.02 % of pvlib, and identical layouts (modules, inverters, modules in series). The default run checks every 40th project; `EPC_PV_FULL=1` checks the 1000. The strings are also checked by invariants on the input numbers (voltage and current limits), because pvlib has no string sizing. The comparison proves the engine calculates what pvlib calculates with the same models; it does not prove agreement with a real plant.

## Known limits
- **The values are typical and not confirmed** (`data/params.json`): losses, thermal model, inverter curve, incidence modifier, short-circuit factor. The result says so in `warnings`; do not size or sell a plant with it until the owner confirms them on the norms page.
- The sun is evaluated at the timestamp of each value (an hourly mean is not centred); no bifacial gain, no soiling by season, no battery.
- Diffuse and ground light are not reduced by the incidence modifier. The Perez transposition model is not included.
- The coefficient of the maximum-power voltage is the module's `beta_vmp_pct_c` (data sheet) when given; otherwise it is taken equal to that of the open-circuit voltage and the result says so (`wind_proxy`).
- DC cables, protections and the connection to the low-voltage board are not calculated here (next step, with `epc_aea90364`).
- The formulas are in `docs/formulas.md`.

## Shading (2026-11-26)

`epc_pv.shading` computes the shade of the direct beam from geometry, with no norm value: the far horizon (`site.horizon`: points `{azimuth_deg, elevation_deg}`, joined by straight lines around the circle, azimuth clockwise from north; the sun below the profile gives no direct beam) and the shade of one row on the next (`arrays[].row_shading`: `slope_m`, `pitch_m`, `n_rows`; the sun is taken in the plane normal to the rows, the front row is never shaded, the share of a row shaded is the share of its direct beam lost). Only the direct part is reduced; the diffuse and ground parts stay. When either is given, the typical `losses_pct.shading` is not added to that array (no double count) and the array result carries `shading_loss_pct` (yearly plane-of-array energy lost) with the warning `shading_computed`. Without them nothing changes. Near obstacles (`arrays[].near_obstacles`, `epc_pv.nearshade`): the array as a tilted rectangle and the obstacles as boxes on the ground, in a local frame (x east, y north, metres); the sun ray is cast from a grid of 16 points of the array and the share of points in the sun multiplies the direct beam (with the rows and the horizon). Not covered: obstacles that are not boxes, electrical mismatch by shaded cells (the loss is proportional to the area), diffuse-sky obstruction.

## Tracker (2026-11-26)

`arrays[].tracker` (`axis_azimuth_deg`, `max_angle_deg`, `backtracking` default true, `gcr` with backtracking) replaces the fixed plane with a horizontal single-axis tracker: `epc_pv.tracker` gives the rotation angle of every instant (ideal angle in the plane normal to the axis, backtracking from the ground coverage ratio, clipped to the maximum angle) and the plane it gives, and the irradiance is computed on that plane instant by instant. `tilt_deg` and `azimuth_deg` are not needed. A tracker array takes no `row_shading` or `near_obstacles` (error `err_tracker_shade`). The layout, strings and drawings are not changed by the tracker (the 3D tracker structure is not modelled). Checked with closed-form cases (sun over the axis, east and west symmetry, clipping, backtracking); there is no pvlib reference for it in this environment.

## Life of the plant (2026-11-26)

`assumptions.degradation` (`{"pct_per_year": 0.5, "years": 25}`, no default: the value comes from the module data sheet or from the owner) adds `lifetime_ac_kwh` (year 1 is the run, each later year keeps `1 - degradation` of the year before, compound) to every array and to the totals, with `lifetime_total_ac_kwh`. Without the block nothing changes. `epc_pv.lifetime`.

## Irradiation disk (2026-11-26)
`epc_pv.disk.compute(doc)` gives the annual irradiation on every fixed plane of a site (tilt 0 to 90, azimuth 0 to 360 from north, clockwise) and its percentage of the best plane: the polar "disk" of the solar resource studies. Same transposition and sun position as the yield; the document needs `site` and `weather` only. `pct_at` reads any tilt and azimuth by bilinear interpolation, `refine` gives a finer grid for drawing. The drawing is `epc_draw.pv.disk.render` (DXF blocks, colour or grey palette). Formula: `kwh_m2 = sum(G_poa) dt`, `pct = 100 kwh_m2 / max(kwh_m2)`.
