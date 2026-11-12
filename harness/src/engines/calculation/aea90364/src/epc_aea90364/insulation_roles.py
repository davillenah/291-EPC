"""Insulation by the role of the circuit (owner decision D6).

There is no global default insulation. The role of a circuit (the `type_circuit` of aea_pipeline) decides it: feeders, incoming supplies and sectional lines take XLPE; terminal lighting
and terminal receptacle circuits take PVC. The table is data (`data/insulation_by_role.json`). A role that D6 does not cover (motor circuits) is absent: the caller keeps its criteria value.
An insulation written on the circuit row (column AISLACION) always wins over the role; that is how a special terminal circuit states another insulation."""
import json
from pathlib import Path

_FILE = Path(__file__).resolve().parent / "data" / "insulation_by_role.json"
_CACHE = {}


def roles_table():
    """The role -> insulation table ({'seccional': 'xlpe', ...})."""
    if not _CACHE:
        _CACHE.update(json.loads(_FILE.read_text(encoding="utf-8"))["by_role"])
    return dict(_CACHE)


def insulation_for_role(role):
    """'xlpe' | 'pvc' for a role D6 covers; None for a role it does not (the caller then keeps the criteria insulation)."""
    return roles_table().get(role)
