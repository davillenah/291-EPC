"""cutlist: the one-dimensional cutting plan of bars, trays, conduits, profiles or cables. Generic: it holds no norm value, no catalog and no price.

Pure functions, standard library only. Stock lengths, saw kerf, part lengths and cut angles are inputs; the engine places parts into stock bars (best fit
decreasing), keeps the kerf of every cut and marks the angles the person must check.
"""
from epc_cutlist.build import build_cutlist, render_rows
from epc_cutlist.errors import CutlistError

__all__ = ["build_cutlist", "render_rows", "CutlistError"]
__version__ = "0.1.0"
