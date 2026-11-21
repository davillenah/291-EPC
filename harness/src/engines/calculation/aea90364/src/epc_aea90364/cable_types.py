"""The cable type of a circuit, decided before any section is sized: conductor material, insulation, number of cores and installation method; never the cross-section.

The type comes from the circuit row (what a person wrote wins), then from the role of the circuit (insulation by role, owner decision D6, `insulation_roles`), then from the design criteria. It is a
pure function of those inputs, used by the calculation pipeline before the section search and callable on its own to estimate the types of a board ahead of the calculation (flow step 3 of
docs/prsad/PRD-diagram-flow.md). It holds no value that depends on a current or a length."""
from epc_aea90364 import insulation_roles as IR

XLPE_DEFAULT_METHOD = "B2"       # B1 only has a table for PVC


def cable_type(row: dict, role: str, material_default: str, insulation_default: str) -> dict:
    """{'material', 'insulation', 'method', 'cores'} of a circuit row.

    `method` is None when neither the row nor the insulation fixes one (the ampacity engine then applies its own default); `cores` is 'single' for a single-core cable (`CABLE_TIPO` unifilar), else 'multi'."""
    insulation = row.get("AISLACION") or IR.insulation_for_role(role) or insulation_default
    method = row.get("METODO") or (XLPE_DEFAULT_METHOD if insulation == "xlpe" else None)
    cores = "single" if str(row.get("CABLE_TIPO") or "").strip().lower() == "unifilar" else "multi"
    return {"material": row.get("MATERIAL") or material_default, "insulation": insulation, "method": method, "cores": cores}


def estimate(rows: dict, roles: dict, material_default: str, insulation_default: str) -> dict:
    """{tag: cable type} for the circuit rows {tag: row} with their roles {tag: role}; deterministic, in tag order."""
    return {tag: cable_type(rows[tag], roles.get(tag), material_default, insulation_default) for tag in sorted(rows)}
