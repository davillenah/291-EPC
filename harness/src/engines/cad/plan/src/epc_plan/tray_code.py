"""The names of the tray models of the project (`tray_names.json`): our own, free of any maker. A pure function of its arguments.

    code(kind, width_mm, height_mm, fitting="straight")   -> "BN-ESC-300x90", "BN-ESC-C90-300x90"
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


def code(kind: str, width_mm: float, height_mm: float, fitting: str = "straight") -> str:
    names = _names()
    if kind not in names["kinds"] or fitting not in names["fittings"]:
        raise PlanError("err_tray_kind", kind=kind, kinds=", ".join(names["kinds"]))
    parts = [names["prefix"], names["kinds"][kind]["code"], names["fittings"][fitting]["code"], f"{round(width_mm)}x{round(height_mm)}"]
    return "-".join(p for p in parts if p)


def name(kind: str, fitting: str = "straight") -> Dict[str, str]:
    names = _names()
    k, f = names["kinds"][kind]["name"], names["fittings"][fitting]["name"]
    return {lang: f"{f[lang]} ({k[lang]})" for lang in ("en", "es")}
