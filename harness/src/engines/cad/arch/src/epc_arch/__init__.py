"""epc_arch: architecture recognition (walls, doors and windows) from a DXF, a vector PDF or an image. See README.md."""
from epc_arch.model import Architecture, ArchError, Opening, Options, Wall
from epc_arch.pipeline import Result, recognize
from epc_arch.review import review
from epc_arch.sources import kinds
from epc_arch.sheets import template_from_svg
from epc_arch.drawing import LAYERS_PATH, load_style, style_with
from epc_arch.contract import ElevationInput, FloorInput, building_solids, draw_elevation
from epc_arch.sources.render import pdf_to_png

__version__ = "0.1.0"
__all__ = ["recognize", "Result", "Options", "Architecture", "Wall", "Opening", "ArchError", "kinds", "pdf_to_png", "review", "template_from_svg", "ElevationInput", "FloorInput", "building_solids", "draw_elevation", "LAYERS_PATH", "load_style", "style_with"]
