"""The shading and irradiation section of the PV calculation memorandum (PV-17): the loss by shading of the abacus and the irradiation by orientation of the disk, both read from `result["charts"]`.

Nothing is calculated here: a value is read from the engine result, or it is written 'not available'. The plant orientation is matched to the nearest cell of the disk (a reading, not an interpolation).
"""
from epc_report.pv.calc_memo import _calc
from epc_report.pv.figures import abacus_figure, disk_figure
from epc_report.pv.texts import tr


def _nearest(values, wanted):
    return min(range(len(values)), key=lambda i: abs(values[i] - wanted))


def _shade(lang, abacus):
    pts = len(abacus.get("profile") or [])
    data = tr(lang, "horizon_pts", n=pts) if pts else tr(lang, "no_horizon")
    result = tr(lang, "shade_result", loss=abacus["loss_pct"], tilt=abacus["tilt_deg"], az=abacus["azimuth_deg"])
    return _calc(lang, "C-14", "c_shade", data, tr(lang, "shade_formula"), tr(lang, "not_returned"), result, "-", "not_verified")


def _disk(lang, disk, spec):
    best, tilts = disk["best"], disk["tilt_deg"]
    result = tr(lang, "disk_best", tilt=best["tilt_deg"], az=best["azimuth_deg"], kwh=best["kwh_m2"])
    if isinstance(spec, dict) and spec.get("tilt_deg") is not None and spec.get("azimuth_deg") is not None:
        i, j = _nearest(tilts, spec["tilt_deg"]), _nearest(disk["azimuth_deg"], spec["azimuth_deg"] % 360)
        result += "; " + tr(lang, "disk_plant", tilt=tilts[i], az=disk["azimuth_deg"][j], pct=disk["pct"][i][j])
    data = tr(lang, "disk_data", t0=tilts[0], t1=tilts[-1], hours=disk["hours"])
    return _calc(lang, "C-15", "c_disk", data, tr(lang, "disk_formula"), tr(lang, "not_returned"), result, tr(lang, "disk_crit"), "not_verified")


def shading_blocks(lang, result, specs):
    """The blocks of the section; empty when the engine result carries no charts (the section is then left out, not invented)."""
    charts = result.get("charts") or {}
    if not charts.get("abacus") or not charts.get("disk"):
        return []
    first = next(iter(specs.values()), None)
    return ([{"type": "h", "text": tr(lang, "h_shade")}, {"type": "p", "text": tr(lang, "l_shade")}] + _shade(lang, charts["abacus"]) + ([abacus_figure(lang, charts["abacus"])] if charts["abacus"].get("cells") else [])
            + _disk(lang, charts["disk"], first) + [disk_figure(lang, charts["disk"])] + [{"type": "p", "text": tr(lang, "t_shade")}])
