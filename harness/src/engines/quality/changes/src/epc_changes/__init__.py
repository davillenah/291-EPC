"""changes: change control between revision A and revision B of a list of records (circuits, symbols, sheets, lines of a list).

Generic quality engine: it holds no norm value. Pure functions, standard library only.
"""
from epc_changes.build import compare
from epc_changes.errors import ChangesError

__all__ = ["compare", "ChangesError"]
__version__ = "0.1.0"
