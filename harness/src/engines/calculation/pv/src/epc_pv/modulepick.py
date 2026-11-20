"""The module that installs the most power on a given structure.

The person gives the structure; the harness tries every module of the catalog (and, where the layout allows it, both orientations of the modules) and keeps the one whose total installed power
(modules that fit x their rated power) is the highest, even when a smaller module holds so many more that the whole is larger. Only the geometry decides: no module is preferred by brand or price.
The counting itself is the caller's (`count(record, orientation) -> modules that fit`), so the same pick serves a ground site, a flat roof and roof planes.
Catalog values are pending review.
"""
from pathlib import Path
from epc_pv import catalog
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

AUTO = "auto"
_DATA = Path(__file__).parent / "data"


def modules() -> List[Dict[str, Any]]:
    """The catalog modules that can be placed: those whose data sheet gives the size (a record without dimensions cannot be fitted on a structure, and none is made up)."""
    return [r for r in catalog.module_records() if r.get("dimensions_mm")]


def block(record: Dict[str, Any]) -> Dict[str, Any]:
    """The module block of an array for a catalog record (its id and model kept for the reports)."""
    return dict(record["module"], id=record["id"], model=record["model"])


def best(count: Callable[[Dict[str, Any], Optional[str]], int], orientations: Sequence[Optional[str]] = (None,), top: int = 5) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """(best row, the `top` rows by installed power): a row is {record, orientation, modules, dc_kwp}; ties go to the larger count, then to the catalog order."""
    rows = []
    for rec in modules():
        for orientation in orientations:
            n = int(count(rec, orientation))
            rows.append({"record": rec, "orientation": orientation, "modules": n, "dc_kwp": round(n * float(rec["module"]["pmax_w"]) / 1000.0, 3)})
    ranked = sorted(rows, key=lambda r: (-r["dc_kwp"], -r["modules"]))
    return ranked[0], ranked[:top]


def summary(rows: List[Dict[str, Any]]) -> str:
    """The alternatives as one line (same in both languages: names and numbers)."""
    return "; ".join(f"{r['record']['model']}{' ' + r['orientation'] if r['orientation'] else ''}: {r['modules']} x {r['record']['module']['pmax_w']:g} W = {r['dc_kwp']:g} kWp" for r in rows)
