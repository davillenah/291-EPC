"""Group B, invariants (calc-check): comparisons between the numbers the engine reported. No new number is produced; limits and factors come from the engine.

A quantity that is missing is skipped here (group C reports a missing key). The engine rounds `Ib` to one decimal and the drops to three; the comparisons
use the values as reported, the way the engine's own verdicts do.
"""
from epc_calc_check._engine import engine
from epc_calc_check._values import num
from epc_calc_check.findings import issue

KA_TO_A = 1000.0       # unit conversion kA -> A
DROP_ROUND = 0.0016    # three roundings of 0.0005 (parent, own and sum)


def _bad(view, rule, stage, tag, key, found, expected, action, evidence):
    return issue(rule, view.slug(stage), f"circuits/{tag}/{key}", found, expected, action, evidence)


def _i2_exact(view, tag):
    """I2 from the engine function when the device kind and In are known, else the reported (rounded) I2."""
    in_a, kind = view.number(8, tag, "in_a"), view.value(11, tag, "device_kind")
    if in_a is not None and in_a > 0 and kind is not None:
        return engine().PROT.i2_convencional(in_a, "mccb" if kind == "mccb" else "mcb")
    return view.number(8, tag, "i2_a")


def _overload(view, tag):
    ib, in_a, iz = (view.number(8, tag, k) for k in ("ib_a", "in_a", "iz_a"))
    if None in (ib, in_a, iz) or ib <= in_a <= iz:
        return []
    return [_bad(view, "CC-B01", 8, tag, "iz_a", {"ib_a": ib, "in_a": in_a, "iz_a": iz}, "ib_a <= in_a <= iz_a", "Increase the section or reduce the protection rating.",
                 "stage 8 row compared with the engine condition In <= Iz")]


def _i2_limit(view, tag):
    iz, i2 = view.number(8, tag, "iz_a"), _i2_exact(view, tag)
    if iz is None or i2 is None:
        return []
    k = engine().policy.k_max_i2_iz()
    if i2 <= k * iz:
        return []
    return [_bad(view, "CC-B02", 8, tag, "i2_a", i2, f"<= {k} x Iz = {k * iz}", "Increase the section or reduce the protection rating.", "epc_aea90364.policy.k_max_i2_iz")]


def _drop_verdict(view, tag):
    own, acc, lim, iz = (view.number(9, tag, "own_pct"), view.number(9, tag, "accumulated_pct"), view.number(9, tag, "limit_pct"), view.number(8, tag, "iz_a"))
    s = view.number(8, tag, "s_mm2")
    if None in (own, acc, lim) or s is None:
        return []
    expected = bool(iz is not None and acc <= lim)                       # D17: the limit of the type is compared with the accumulated drop
    out = []
    for stage in (8, 9):
        reported = view.value(stage, tag, "compliant")
        if isinstance(reported, bool) and reported != expected:
            out.append(_bad(view, "CC-B03", stage, tag, "compliant", reported, expected, "Review the verdict with the engineer of record; re-run the stage.",
                            f"accumulated {acc} % (own {own} %) <= limit {lim} % of the type, Iz present: {expected}"))
    return out


def _drop_limit(view, tag):
    lim, limits = view.number(9, tag, "limit_pct"), view.outputs(9).get("limits_pct")
    if lim is None or not isinstance(limits, dict) or not limits or lim in limits.values():
        return []
    return [_bad(view, "CC-B04", 9, tag, "limit_pct", lim, sorted(limits.values()), "Use a limit the engine reports.", "stage 9 limits_pct")]


def _breaking(view, tag):
    icu, icc, flag = view.number(10, tag, "icu_ka"), view.number(10, tag, "icc_a"), view.value(10, tag, "breaking_ok")
    if icu is None or icc is None or not isinstance(flag, bool) or flag == (icu * KA_TO_A >= icc):
        return []
    return [_bad(view, "CC-B05", 10, tag, "breaking_ok", flag, icu * KA_TO_A >= icc, "Review the verdict with the engineer of record.",
                 f"Icu {icu} kA against Icc {icc} A")]


def _busbar(view, tag):
    icc, busbar, low = view.number(10, tag, "icc_a"), num(view.outputs(10).get("busbar_icc_ka")), view.number(10, tag, "icc_min_a")
    out = []
    if icc is not None and busbar is not None and abs(icc - busbar * KA_TO_A) > 0.5:
        out.append(_bad(view, "CC-B06", 10, tag, "icc_a", icc, busbar * KA_TO_A, "Use the busbar Icc of the board.", f"busbar Icc {busbar} kA"))
    if icc is not None and low is not None and low > icc:
        out.append(_bad(view, "CC-B06", 10, tag, "icc_min_a", low, f"<= {icc}", "Icc min cannot exceed Icc max.", "stage 10 row"))
    return out


def _trip(view, tag):
    low, k_max, in_a, flag = view.number(10, tag, "icc_min_a"), view.number(10, tag, "k_max"), view.number(8, tag, "in_a"), view.value(10, tag, "trip_ok")
    if low is None or k_max is None or in_a is None or not isinstance(flag, bool) or flag == (low >= k_max * in_a):
        return []
    return [_bad(view, "CC-B07", 10, tag, "trip_ok", flag, low >= k_max * in_a, "Review the verdict with the engineer of record.",
                 f"Icc min {low} A against k_max {k_max} x In {in_a} A")]


def _flags(view, tag):
    ib, in_a, iz = (view.number(8, tag, k) for k in ("ib_a", "in_a", "iz_a"))
    i2, out = _i2_exact(view, tag), []
    if None in (ib, in_a):
        return out
    checks = (("overload_ok", iz is not None and ib <= in_a <= iz), ("coordination_ok", iz is not None and i2 is not None and i2 <= engine().policy.k_max_i2_iz() * iz))
    for stage in (8, 11):
        for key, expected in checks:
            reported = view.value(stage, tag, key)
            if isinstance(reported, bool) and reported != expected:
                out.append(_bad(view, "CC-B08", stage, tag, key, reported, expected, "Review the verdict with the engineer of record; re-run the stage.",
                                f"Ib {ib}, In {in_a}, Iz {iz}, I2 {i2}"))
    return out


def _min_section(view, tag):
    s, smin, sint = (view.number(8, tag, k) for k in ("s_mm2", "min_section_mm2", "s_internal_mm2"))
    out = []
    if s is not None and smin is not None and s < smin:
        out.append(_bad(view, "CC-B09", 8, tag, "s_mm2", s, f">= {smin}", "Use a section not below the minimum.", "epc_aea90364.aea_conductors.section_min_circuit"))
    if s is not None and sint is not None and s < sint:
        out.append(_bad(view, "CC-B09", 8, tag, "s_mm2", s, f">= internal section {sint}", "The outgoing cable cannot be thinner than the internal wiring.", "stage 8 row"))
    return out


def _accumulated(view, tag):
    own, acc = view.number(9, tag, "own_pct"), view.number(9, tag, "accumulated_pct")
    parent = view.value(4, tag, "parent")
    base = view.number(9, parent, "accumulated_pct") if parent else 0.0
    if own is None or acc is None or base is None or abs(acc - (base + own)) <= DROP_ROUND:
        return []
    return [_bad(view, "CC-B10", 9, tag, "accumulated_pct", acc, base + own, "The accumulated drop is the parent's plus the own drop.",
                 f"parent {parent or '-'} accumulated {base} + own {own}")]


def _differential(view, tag):
    needs = view.value(7, tag, "type") == "tomacorrientes"
    diff, flag = view.value(12, tag, "differential"), view.value(12, tag, "differential_ok")
    if view.row(12, tag) is None:
        return []
    if needs and not isinstance(diff, dict):
        return [_bad(view, "CC-B11", 12, tag, "differential", diff, "a differential (socket-outlet circuit)", "Add the high-sensitivity differential.", "stage 7 type tomacorrientes")]
    if isinstance(diff, dict) and isinstance(flag, bool) and flag != diff.get("cumple"):
        return [_bad(view, "CC-B11", 12, tag, "differential_ok", flag, diff.get("cumple"), "The flag must equal the differential verdict.", "stage 12 row")]
    return []


def _series(view, tag):
    e, out = engine(), []
    for stage, key, series in ((8, "in_a", e.series_in), (10, "icu_ka", e.series_icu), (8, "s_mm2", e.series_s)):
        value = view.number(stage, tag, key)
        if value is not None and value not in series:
            out.append(_bad(view, "CC-B12", stage, tag, key, value, "a value of the engine series", "Use a standard value.", f"series {list(series)}"))
    return out


STEPS = (_overload, _i2_limit, _drop_verdict, _drop_limit, _breaking, _busbar, _trip, _flags, _min_section, _accumulated, _differential, _series)


def check_invariants(view):
    for tag in view.tags():
        for step in STEPS:
            yield from step(view, tag)
