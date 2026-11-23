"""The types of the contract: options, result and the error."""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from epc_hvac.config import SCHEMA_VERSION
from epc_hvac.messages import text


class HvacError(ValueError):
    """The input is not valid: `str(error)` is the English text, `es` the Spanish one, `code` the stable code (ADR-0039)."""

    def __init__(self, code: str, **params):
        t = text(code, **params)
        super().__init__(t["en"])
        self.code, self.en, self.es = code, t["en"], t["es"]


@dataclass
class Options:
    """No option yet: the typical values live in `data/typical.json`."""


@dataclass
class Result:
    spaces: List[Dict[str, Any]] = field(default_factory=list)
    totals: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "counts": {"spaces": len(self.spaces)}, "warnings": list(self.warnings), "totals": self.totals, "spaces": self.spaces}
