"""walls: straight walls from an axis and a thickness or a layer assembly, with L, T and X join records and corner geometry (mitre, butt, square).

Generic building engine: it holds no norm value, no material catalog and no thickness. Plan geometry only; pure functions, standard library only.
"""
from epc_walls.build import outlines
from epc_walls.assembly import bands
from epc_walls.errors import WallsError
from epc_walls.joins import derive

__all__ = ["outlines", "bands", "derive", "WallsError"]
__version__ = "0.1.0"
