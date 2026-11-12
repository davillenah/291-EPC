"""boq: the draft bill of quantities (computo) of a calculated board. Quantities only: no prices, no costs.

Pure functions, standard library only, no data tables. Lengths, sections and currents are inputs from the calculation engines: nothing is calculated here
except sums, counts and the explicit wastage factor the caller gives.
"""
from epc_boq.build import build_boq, render_rows

__all__ = ["build_boq", "render_rows"]
__version__ = "0.1.0"
