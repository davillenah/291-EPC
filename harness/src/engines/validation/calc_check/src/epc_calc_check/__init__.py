"""calc_check: deterministic checks of what the engines produced, without trusting the stage code that produced it (PRD section 5, segregation of duties).

`check_run(run_result, project=..., files=..., run_id=...)` returns findings (finding.schema.json). Pure Python; the only engine it calls is `epc_aea90364`,
and only when a check runs.
"""
from epc_calc_check.rules import RULES
from epc_calc_check.runner import GROUP_DOCUMENTS, GROUP_FORMAT, GROUP_INVARIANTS, GROUP_MANIFESTS, GROUP_RECALC, GROUPS, check_run

__all__ = ["check_run", "RULES", "GROUPS", "GROUP_RECALC", "GROUP_INVARIANTS", "GROUP_FORMAT", "GROUP_DOCUMENTS", "GROUP_MANIFESTS"]
__version__ = "0.1.0"
