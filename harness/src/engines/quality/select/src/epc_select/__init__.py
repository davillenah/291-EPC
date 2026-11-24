"""select: the records of a list that meet one or all of some conditions (quick select of circuits, symbols, sheets, lines of a list).

Generic quality engine: it holds no norm value. Pure functions, standard library only.
"""
from epc_select.build import select
from epc_select.errors import SelectError

__all__ = ["select", "SelectError"]
__version__ = "0.1.0"
