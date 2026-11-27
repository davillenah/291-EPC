"""epc_pv: hourly energy yield of a grid-connected photovoltaic plant and its string layout. See README.md."""
from epc_pv.model import Options, PvError, Result
from epc_pv.layout import check as check_layout, plan as plan_layout
from epc_pv.roof import plan as plan_roof
from epc_pv.pipeline import run
from epc_pv.feasibility import add_inverters_for_current, economic_summary, technical_summary

__version__ = "0.1.0"                                    # equals config.VERSION and pyproject.toml (the architecture test checks the last)

__all__ = ["add_inverters_for_current", "economic_summary", "technical_summary", "run", "plan_layout", "check_layout", "plan_roof", "Options", "Result", "PvError", "__version__"]
