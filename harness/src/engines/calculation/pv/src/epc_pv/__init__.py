"""epc_pv: hourly energy yield of a grid-connected photovoltaic plant and its string layout. See README.md."""
from epc_pv.model import Options, PvError, Result
from epc_pv.pipeline import run

__version__ = "0.1.0"                                    # equals config.VERSION and pyproject.toml (the architecture test checks the last)

__all__ = ["run", "Options", "Result", "PvError", "__version__"]
