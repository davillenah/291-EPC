"""epc_arch: architecture recognition (walls, doors and windows) from a DXF, a vector PDF or an image. See README.md."""
from epc_draw.arch.model import Architecture, ArchError, Opening, Options, Wall
from epc_draw.arch.pipeline import Result, recognize
from epc_draw.arch.review import review
from epc_draw.arch.sources import kinds
from epc_draw.arch.sheets import template_from_svg
from epc_draw.arch.drawing import LAYERS_PATH, load_style, style_with
from epc_draw.arch.author import plan_dxf
from epc_draw.arch.contract import ElevationInput, FloorInput, building_solids, draw_elevation
from epc_draw.arch.sources.render import pdf_to_png

__version__ = "0.1.0"
__all__ = ["recognize", "Result", "Options", "Architecture", "Wall", "Opening", "ArchError", "kinds", "pdf_to_png", "review", "template_from_svg", "ElevationInput", "FloorInput", "building_solids", "draw_elevation", "LAYERS_PATH", "load_style", "style_with", "plan_dxf"]
