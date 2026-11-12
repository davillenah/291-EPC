"""Simultaneity of the current of parent circuits (owner decision D14).

A parent circuit (board, feeder, sectional line, incoming supply) carries the sum of the currents of its children times a simultaneity factor. A terminal circuit (a leaf) is sized at full load:
no factor ever touches it. Where the factor comes from depends on the installation type, which the project states explicitly (criteria key `installation_type`):
  dwelling -> Table 771.9.II by degree of electrification (criteria `electrification_grade`), through `aea_demand.coef_simultaneity_771`;
  other    -> the factor defined for the board or project (criteria `simultaneity_factor`); when none is given, Table 771.9.III (`aea_demand.coef_simultaneidad_conjunto`) by the
              number of child circuits (units) and the degree of electrification.
No installation type, an unknown one, or a missing input the rule needs -> the plain sum, exactly as before, and a warning says why (never a guess). A parent with fewer than two children has
nothing to be simultaneous with and keeps the plain sum. Every number comes from the engine tables; the sentence for the memo is generated from the values."""
import json
from pathlib import Path

from epc_aea90364 import aea_demand as DEM

_FILE = Path(__file__).resolve().parent / "data" / "installation_types.json"
_CACHE = {}
TABLE_DWELLING = "771.9.II"
TABLE_DEFAULT = "771.9.III"
TABLE_PROJECT = "project"


def _vocabulary():
    if not _CACHE:
        _CACHE.update(json.loads(_FILE.read_text(encoding="utf-8")))
    return _CACHE


def installation_kind(value):
    """'dwelling' | 'other' for an explicit installation type listed in the data; None for a value that is absent or not listed."""
    key = str(value or "").strip().lower()
    voc = _vocabulary()
    return next((kind for kind in ("dwelling", "other") if key in voc[kind]), None)


def _valid_factor(value):
    f = float(value)
    if not 0.0 < f <= 1.0:
        raise ValueError(f"simultaneity_factor must be in (0, 1], got {value!r}")
    return f


def _valid_grade(value):
    grade = str(value or "").strip().lower()
    if grade and grade not in DEM.COEF_GRADO_771:
        raise ValueError(f"electrification_grade must be one of {sorted(DEM.COEF_GRADO_771)}, got {value!r}")
    return grade or None


def resolve(criterios):
    """The simultaneity policy of a project: {'kind', 'grade', 'factor'} or None (plain sum) plus the reason when something is missing -> (policy, issue)."""
    cr = criterios or {}
    raw = cr.get("installation_type")
    if raw in (None, ""):
        return None, None
    kind = installation_kind(raw)
    if kind is None:
        return None, f"installation_type {raw!r} is not a known type: the current of the parent circuits is the plain sum of their children (simultaneity not applied)"
    grade = _valid_grade(cr.get("electrification_grade"))
    factor = None if cr.get("simultaneity_factor") in (None, "") else _valid_factor(cr["simultaneity_factor"])
    if kind == "dwelling" and grade is None:
        return None, "dwelling without electrification_grade: Table 771.9.II cannot be read, the current of the parent circuits is the plain sum of their children (simultaneity not applied)"
    if kind == "other" and factor is None and grade is None:
        return None, "no simultaneity_factor and no electrification_grade: Table 771.9.III cannot be read, the current of the parent circuits is the plain sum of their children (simultaneity not applied)"
    return {"kind": kind, "grade": grade, "factor": factor, "installation_type": str(raw).strip().lower()}, None


def factor_for(policy, n_units):
    """(factor, table, grade) for a parent with n_units children; (1.0, None, None) when nothing applies (no policy, or fewer than two units)."""
    if not policy or n_units < 2:
        return 1.0, None, None
    if policy["kind"] == "dwelling":
        return DEM.coef_simultaneity_771(policy["grade"]), TABLE_DWELLING, policy["grade"]
    if policy["factor"] is not None:
        return policy["factor"], TABLE_PROJECT, policy["grade"]
    return DEM.coef_simultaneidad_conjunto(n_units, policy["grade"]), TABLE_DEFAULT, policy["grade"]


def parent_current(policy, currents):
    """(Ib of the parent, record or None): the sum of the children times the factor; the record says what was applied (None when the plain sum stands)."""
    plain = sum(currents)
    f, table, grade = factor_for(policy, len(currents))
    if table is None:
        return plain, None
    return plain * f, {"factor": f, "table": table, "grade": grade, "units": len(currents), "installation_type": policy["installation_type"], "plain_a": round(plain, 3)}


def describe(records):
    """The memo sentence for the parent circuits that got a factor ({tag: record}); '' when none did. Generated from the values."""
    groups = {}
    for tag, r in records.items():
        groups.setdefault((r["table"], r["factor"], r["grade"], r["installation_type"]), []).append(tag)
    parts = []
    for (table, f, grade, kind), tags in groups.items():
        src = "the factor defined for the project" if table == TABLE_PROJECT else f"Table {table}"
        gr = f", electrification grade {grade}" if grade else ""
        parts.append(f"{', '.join(tags)}: {src} ({kind}{gr}), factor {f:g}")
    if not parts:
        return ""
    return "Simultaneity (D14) applied to the current of parent circuits: " + "; ".join(parts) + ". Terminal circuits are sized at full load."
