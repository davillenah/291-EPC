"""Phase balance of a board: which phase each single-phase circuit loads, so that the three phases come out as even as possible, and the unbalance between them.

Ported from the old web backend (`sld/loadschedule.py`): a three-phase circuit loads a third of its apparent power on each phase; the single-phase circuits the engineer assigned keep their phase,
and the others go biggest first, each on the least loaded phase. The unbalance and its limit are those of `aea_demand.imbalance_phases` (the limit is a norm record, pending review).
"""
from math import sqrt

from epc_load_balance import aea_demand

LETTERS = ("R", "S", "T")


def apparent_kva(ib_a, voltage_v, phases):
    """S [kVA] of a circuit from its design current: three-phase sqrt(3)*U*I, single-phase (phase voltage U/sqrt(3))*I; `phases` is 1 or 3. None when a datum is missing."""
    if not ib_a or not voltage_v:
        return None
    return (sqrt(3) * voltage_v * ib_a if phases == 3 else voltage_v / sqrt(3) * ib_a) / 1000.0


def _place(split, load, tag, kva, phase):
    """Put the whole of a single-phase circuit on phase `phase` (0, 1 or 2)."""
    split[tag] = [kva if i == phase else 0.0 for i in range(3)]
    load[phase] += kva


def _three_phase(circuits):
    """({tag: a third of the circuit on each phase}, the load of each phase) of the three-phase circuits."""
    split = {tag: [kva / 3.0] * 3 for tag, kva, phases, _ in circuits if phases == 3}
    third = sum(kva for _, kva, phases, _ in circuits if phases == 3) / 3.0
    return split, [third, third, third]


def assign_phases(circuits):
    """`circuits`: [(tag, kva, phases, assigned)] of the circuits that carry load (assigned: 'R', 'S', 'T' or ''). Returns {tag: [R, S, T] kVA}."""
    split, load = _three_phase(circuits)
    singles = [c for c in circuits if c[2] != 3]
    for tag, kva, _, assigned in (c for c in singles if c[3] in LETTERS):
        _place(split, load, tag, kva, LETTERS.index(assigned))
    for tag, kva, _, _ in sorted((c for c in singles if c[3] not in LETTERS), key=lambda c: (-c[1], c[0])):
        _place(split, load, tag, kva, load.index(min(load)))
    return split


def balance(circuits):
    """{circuits: {tag: [R, S, T]}, totals: [R, S, T], unbalance_pct, complies, limit_pct}; the unbalance is that of the three phases (`aea_demand.imbalance_phases`)."""
    split = assign_phases(circuits)
    totals = [sum(v[i] for v in split.values()) for i in range(3)]
    check = aea_demand.imbalance_phases(totals)
    return {"circuits": split, "totals": totals, "unbalance_pct": check["desequilibrio_pct"], "complies": check["cumple"], "limit_pct": aea_demand.DESEQUILIBRIO_MAX_PCT}
