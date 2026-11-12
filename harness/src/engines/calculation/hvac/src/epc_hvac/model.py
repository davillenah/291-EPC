"""The types of the contract: options, result and the error."""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from epc_hvac.config import SCHEMA_VERSION


class HvacError(ValueError):
    """The input is not valid: the message says what to correct."""


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
