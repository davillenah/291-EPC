"""Group A, recalculation (calc-check): the engine's own low-level functions on the inputs the engine had, compared with what the stages reported.

Engine floats are compared with exact equality (same function, same inputs, same result). A value the engine rounded before reporting (the drop is rounded
to 3 decimals) is compared to within one unit of its last digit, because the inputs the stages carry are rounded too. What cannot be recomputed from the
run is reported as `CC-R00` (note); no input is ever guessed. The inputs of the installation (grouping, ambient temperature, ...) come from
`project["circuits"][tag]` in the engine's own row keys (`AGRUP_CIRCUITOS`, `TEMP_AMBIENTE_C`, `TEMP_SUELO_C`, `RESIST_TERMICA_KMW`, `CLASE`, `N_TERNAS`,
`IZ_A`, `MOMENTOS`): the entry says "these are all the inputs", a key that is absent has the engine's own default.
"""
import math

from epc_calc_check._engine import engine
from epc_calc_check._values import num
from epc_calc_check.findings import issue

ROUND_3 = 0.0011       # one unit of the last digit of a value rounded to 3 decimals (plus float noise)


def _unrecomputable(view, tag, stage, key, why):
    return issue("CC-R00", view.slug(stage), f"circuits/{tag}/{key}", None, None, "Give the engine inputs of the circuit in the project data to enable the recalculation.",
                 f"not recomputable: {why}")


def _installation(view, tag):
    """(engine installation parameters, None) or (None, reason)."""
    r8, entry = view.row(8, tag), view.circuit_inputs(tag)
    if r8 is None:
        return None, "stage 8 has no row for the circuit"
    if entry is None:
        return None, "the project data does not declare the engine inputs of the circuit"
    if r8.get("route"):
        return None, "the cable has a route of several segments (the engine needs the segments)"
    row = {"MATERIAL": r8.get("material"), "AISLACION": r8.get("insulation"), "METODO": r8.get("method"), **entry}
    try:
        return engine().AMP.parametros(row), None
    except (ValueError, TypeError) as exc:
        return None, f"the installation parameters are not valid for the engine: {exc}"


def _iz(view, tag):
    par, why = _installation(view, tag)
    s, phases = view.number(8, tag, "s_mm2"), view.number(4, tag, "phases")
    if par is None or s is None or phases is None:
        return [_unrecomputable(view, tag, 8, "iz_a", why or "section or phases missing")]
    try:
        expected = engine().AMP.iz(par, view.value(8, tag, "s_mm2"), int(phases))
    except ValueError as exc:
        return [_unrecomputable(view, tag, 8, "iz_a", f"the engine does not tabulate it: {exc}")]
    reported = view.value(8, tag, "iz_a")
    if reported == expected:
        return []
    return [issue("CC-R01", view.slug(8), f"circuits/{tag}/iz_a", reported, expected, "Find which stage or mapping changed Iz; re-run the stage.",
                  f"epc_aea90364.aea_ampacity.iz(parameters, {s}, {int(phases)}) = {expected}")]


def _voltage(view):
    return num(view.project.get("voltage_v")) or num((view.outputs(7).get("board") or {}).get("voltage_v"))


def _drop_inputs(view, tag):
    """(inputs of the engine drop function, None) or (None, reason)."""
    par, why = _installation(view, tag)
    names = ("ib", "fases", "fp", "largo", "s")
    vals = (view.number(4, tag, "ib_a"), view.number(4, tag, "phases"), view.number(4, tag, "fp"), view.number(9, tag, "length_m"), view.number(8, tag, "s_mm2"))
    if par is None or None in vals or _voltage(view) is None or view.value(7, tag, "type") is None:
        return None, why or "a current, length, section, phases, power factor, voltage or circuit type is missing"
    return (par, dict(zip(names, vals))), None


def _own_drop(view, tag, par, v):
    e = engine()
    moments = view.circuit_inputs(tag).get("MOMENTOS")
    i_du = e.VD.corriente_extremo(v["ib"], "iluminacion") if view.value(7, tag, "type") == "iluminacion" and not moments else v["ib"]
    fases = int(v["fases"])
    u = _voltage(view)
    un = u if fases == 3 else u / math.sqrt(3)
    r = e.AMP.resistencia_ohm_km(v["s"], par["material"], e.AMP.temp_conductor(par, view.project.get("conductor_temp_c", e.conductor_temp_c)))
    if v["largo"] == 0:
        return 0.0
    return e.VDG.caida_tension(fases, i_du, v["largo"], r, e.CO.X_CABLE_OHM_KM, v["fp"], un)["delta_u_pct"]


def _drop(view, tag):
    inputs, why = _drop_inputs(view, tag)
    if inputs is None:
        return [_unrecomputable(view, tag, 9, "own_pct", why)]
    try:
        expected = round(_own_drop(view, tag, *inputs), 3)
    except (ValueError, KeyError, TypeError) as exc:
        return [_unrecomputable(view, tag, 9, "own_pct", f"the engine refused the inputs: {exc}")]
    reported = view.number(9, tag, "own_pct")
    if reported is not None and abs(reported - expected) <= ROUND_3:
        return []
    return [issue("CC-R02", view.slug(9), f"circuits/{tag}/own_pct", view.value(9, tag, "own_pct"), expected, "Find which stage or mapping changed the drop; re-run the stage.",
                  "epc_aea90364.voltage_drop.caida_tension on the same current, length, section, power factor and voltage (rounded to 3 decimals)")]


def _sections(view, tag):
    s = view.number(8, tag, "s_mm2")
    if s is None:
        return []
    e, out = engine(), []
    for key, func in (("pe_mm2", e.CO.pe_section), ("neutral_mm2", e.CO.neutral_section)):
        expected = func(view.value(8, tag, "s_mm2"))
        if view.value(8, tag, key) != expected:
            out.append(issue("CC-R03", view.slug(8), f"circuits/{tag}/{key}", view.value(8, tag, key), expected, "Find which stage or mapping changed the section; re-run the stage.",
                             f"engine rule function for {key} on s_mm2 = {s}"))
    return out


def _i2(view, tag):
    in_a, reported = view.number(8, tag, "in_a"), view.value(8, tag, "i2_a")
    kind = view.value(11, tag, "device_kind")
    if in_a is None or kind is None or in_a <= 0:
        return []
    expected = round(engine().PROT.i2_convencional(in_a, "mccb" if kind == "mccb" else "mcb"), 1)
    if reported == expected:
        return []
    return [issue("CC-R04", view.slug(8), f"circuits/{tag}/i2_a", reported, expected, "Find which stage or mapping changed I2; re-run the stage.",
                  f"epc_aea90364.aea_protection.i2_convencional({in_a}, {'mccb' if kind == 'mccb' else 'mcb'})")]


def _icu(view):
    busbar = view.outputs(10).get("busbar_icc_ka")
    if num(busbar) is None:
        return []
    series = engine().series_icu
    expected = next((v for v in series if v >= busbar), series[-1])
    return [issue("CC-R05", view.slug(10), f"circuits/{r.get('circuit')}/icu_ka", r.get("icu_ka"), expected,
                  "Find which stage or mapping changed Icu; re-run the stage.", f"first value of the engine Icu series not below {busbar} kA")
            for r in view.rows(10) if r.get("icu_ka") != expected]


def _icc_min_note(view):
    if not view.rows(10):
        return []
    return [issue("CC-R00", view.slug(10), "circuits/*/icc_min_a", None, None, "None: Icc min is checked only through its invariants (CC-B06, CC-B07).",
                  "not recomputable: it needs the cumulative cable impedance along the chain of parent circuits, which the stage outputs do not carry")]


def check_recalc(view):
    for tag in view.tags():
        for step in (_iz, _drop, _sections, _i2):
            yield from step(view, tag)
    yield from _icu(view)
    yield from _icc_min_note(view)
