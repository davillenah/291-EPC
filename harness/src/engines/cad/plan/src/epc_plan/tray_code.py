"""The names of the tray models of the project (`tray_names.json`): our own, free of any maker. A pure function of its arguments.

    code(kind, width_mm, height_mm, fitting="straight")   -> "BN-ESC-300x90", "BN-ESC-C90-300x90", "BN-ESC-300x90-18Z"
    fitting_of(part, angle_deg)                           -> the fitting name of a part of a run ("elbow" at 90 degrees is "elbow90")
    name(kind, fitting="straight")                        -> {"en": ..., "es": ...}
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from epc_plan.core import PlanError

PART_FITTINGS = {"straight": "straight", "tee": "tee", "cross": "cross", "reducer": "reduction_central"}


@lru_cache(maxsize=1)
def _names() -> Dict[str, Any]:
    return json.loads((Path(__file__).with_name("tray_names.json")).read_text(encoding="utf-8"))


def fitting_of(part: str, angle_deg: Optional[float] = None) -> Optional[str]:
    """The fitting name of a part of a run (None for a part that is not a tray fitting, such as a support)."""
    if part == "elbow":
        return "elbow45" if angle_deg is not None and abs(angle_deg - 45) < 1 else "elbow90" if angle_deg is not None and abs(angle_deg - 90) < 1 else "elbow_adjustable"
    return PART_FITTINGS.get(part)


def code(kind: str, width_mm: float, height_mm: float, fitting: str = "straight", gauge: str = "", finish: str = "") -> str:
    names = _names()
    if kind not in names["kinds"] or fitting not in names["fittings"]:
        raise PlanError("err_tray_kind", kind=kind, kinds=", ".join(names["kinds"]))
    parts = [names["prefix"], names["kinds"][kind]["code"], names["fittings"][fitting]["code"], f"{round(width_mm)}x{round(height_mm)}"]
    return "-".join(p for p in parts if p) + (f"-{gauge}{finish}" if gauge or finish else "")      # BN-ESC-300x90-18Z when the sheet is given


def name(kind: str, fitting: str = "straight") -> Dict[str, str]:
    names = _names()
    k, f = names["kinds"][kind]["name"], names["fittings"][fitting]["name"]
    return {lang: f"{f[lang]} ({k[lang]})" for lang in ("en", "es")}


def part(key: str, size: str) -> Dict[str, Any]:
    """The own code and the bilingual name of a support or fastener: SB-BUL-M8x25. `key` is one of the parts of `tray_names.json` (`hardware`)."""
    hw = _names()["hardware"]
    if key not in hw["parts"]:
        raise PlanError("err_tray_kind", kind=key, kinds=", ".join(hw["parts"]))
    item = hw["parts"][key]
    return {"code": "-".join((hw["prefix"], item["code"], size)), "name": dict(item["name"])}
