"""Energy over the life of the plant from a yearly degradation the user gives (no default: the value comes from the module data sheet or the owner's decision).

Year 1 is the energy of the run; each later year keeps `1 - degradation` of the year before (compound). The block is `assumptions.degradation`: `{"pct_per_year": 0.5, "years": 25}`.
"""
from typing import Any, Dict, List, Optional

from epc_pv.messages import bi
from epc_pv.model import PvError


def parse(assumptions: Any) -> Optional[Dict[str, float]]:
    """The checked degradation block, or None when the document gives none."""
    block = (assumptions or {}).get("degradation") if isinstance(assumptions, dict) else None
    if block is None:
        return None
    if not isinstance(block, dict):
        raise PvError("err_type", name="assumptions.degradation", kind=bi("an object", "un objeto"))
    missing = [k for k in ("pct_per_year", "years") if k not in block]
    if missing:
        raise PvError("err_missing", where="assumptions.degradation", names=", ".join(missing))
    pct, years = _number(block["pct_per_year"], "pct_per_year", 0.0, 100.0), _number(block["years"], "years", 1.0, 100.0)
    return {"pct_per_year": pct, "years": int(years)}


def _number(value: Any, key: str, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as e:
        raise PvError("err_type", name=f"assumptions.degradation.{key}", kind=bi("a number", "un número")) from e
    if not low <= number <= high:
        raise PvError("err_range", name=f"assumptions.degradation.{key}", rule=bi(f"from {low:g} to {high:g}", f"de {low:g} a {high:g}"), value=number)
    return number


def project(first_year_kwh: float, life: Dict[str, float]) -> List[float]:
    """The yearly energy over the years of `life`: year 1 as given, then compound degradation."""
    keep = 1.0 - life["pct_per_year"] / 100.0
    return [round(first_year_kwh * keep ** n, 3) for n in range(life["years"])]
