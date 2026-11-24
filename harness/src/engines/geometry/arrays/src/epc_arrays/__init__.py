"""arrays: the positions of the copies of a rectangular or polar array (luminaire grids, module tables, bolt circles).

Generic geometry engine: it holds no norm value. Pure functions, standard library only.
"""
from epc_arrays.build import polar, rectangular
from epc_arrays.errors import ArraysError

__all__ = ["polar", "rectangular", "ArraysError"]
__version__ = "0.1.0"
