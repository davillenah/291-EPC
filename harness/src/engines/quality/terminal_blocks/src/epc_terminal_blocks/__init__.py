"""terminal_blocks: the terminal-block list (planilla de bornes) of a calculated board.

Pure functions. The terminal size table is data (`data/terminal_sizes.json`, pending review). Sections and currents are inputs from the calculation
engines: nothing is calculated here.
"""
from epc_terminal_blocks.build import build_terminal_list, conductors, render_rows
from epc_terminal_blocks.sizes import accepting_size, clear_cache, terminal_sizes

__all__ = ["build_terminal_list", "render_rows", "conductors", "terminal_sizes", "accepting_size", "clear_cache"]
__version__ = "0.1.0"
