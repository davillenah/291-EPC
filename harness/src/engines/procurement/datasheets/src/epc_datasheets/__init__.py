"""datasheets: draft equipment datasheet records of a calculated board (manufacturer-catalog candidates per requirement).

Pure functions, standard library only. The catalog is an argument; `load_catalog_dir` is the one explicit I/O function and is called only when the caller
gives a folder. Nothing is calculated and no winner is chosen: a product is a candidate only when catalog numbers satisfy the requirement by comparison.
"""
from epc_datasheets.build import build_datasheets, render_rows, requirements_from_circuits
from epc_datasheets.catalog import load_catalog_dir

__all__ = ["build_datasheets", "load_catalog_dir", "render_rows", "requirements_from_circuits"]
__version__ = "0.1.0"
