"""The types of the contract: options, result and the error (its message is in English and Spanish)."""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from epc_pv.config import SCHEMA_VERSION
from epc_pv.messages import LABELS, text


class PvError(ValueError):
    """The input is not valid: the message says what to correct, in English (`str`) and in Spanish (`es`)."""

    def __init__(self, code: str, **params):
        t = text(code, **params)
        super().__init__(t["en"])
        self.code, self.en, self.es = code, t["en"], t["es"]


@dataclass
class Options:
    """`transposition`: sky-diffuse model on the tilted plane, `haydavies` (default) or `isotropic`."""
    transposition: str = "haydavies"


@dataclass
class Result:
    arrays: List[Dict[str, Any]] = field(default_factory=list)
    totals: Dict[str, Any] = field(default_factory=dict)
    warnings: List[Dict[str, str]] = field(default_factory=list)
    hours: int = 0

    def as_dict(self) -> Dict[str, Any]:
        counts = {"arrays": len(self.arrays), "inverters": sum(a["inverters"] for a in self.arrays), "modules": sum(a["modules"] for a in self.arrays), "hours": self.hours}
        return {"schema_version": SCHEMA_VERSION, "counts": counts, "warnings": list(self.warnings), "labels": LABELS, "totals": self.totals, "arrays": self.arrays}
