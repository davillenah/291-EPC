"""dims: automatic exterior dimensions (total and chains by edge) from straight walls and openings.

Generic building engine: it holds no norm value. The distances that shape the result are inputs. Pure functions, standard library only.
"""
from epc_dims.build import dimensions
from epc_dims.errors import DimsError

__all__ = ["dimensions", "DimsError"]
__version__ = "0.1.0"
