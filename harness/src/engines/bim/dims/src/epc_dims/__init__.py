"""dims: automatic exterior dimensions (total and chains by edge) from straight walls and openings.

Generic building engine: it holds no norm value. The distances that shape the result are inputs. Pure functions, standard library only.
"""
from epc_dims.build import dimensions
from epc_dims.errors import DimsError
from epc_dims.scales import annotation_size, paper_size

__all__ = ["dimensions", "annotation_size", "paper_size", "DimsError"]
__version__ = "0.1.0"
