"""EPC drawing engine: IEC 60617 symbols, IRAM sheets and title blocks, single-line (SLD) and multi-line (MLD) diagrams."""
__version__ = "0.1.0"

import importlib
import importlib.abc
import importlib.util
import sys


class _PvDoor(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """The PV drawing modules moved into `epc_draw.pv` (ADR-0042): `epc_drawing.pv_<name>` is the module `epc_draw.pv.<name>` itself."""

    def find_spec(self, name, path=None, target=None):
        if name.startswith("epc_drawing.pv_"):
            return importlib.util.spec_from_loader(name, self)
        return None

    def create_module(self, spec):
        return importlib.import_module("epc_draw.pv." + spec.name.split(".pv_", 1)[1])

    def exec_module(self, module):
        return None


if not any(isinstance(f, _PvDoor) for f in sys.meta_path):
    sys.meta_path.insert(0, _PvDoor())


__all__ = ["DrawingError", "Pen", "PvDrawInput", "assemble", "assemble_board", "audit", "draw_pv", "box", "build", "build_board_model", "build_common", "build_sector", "calc_note", "calculate", "catalog_defaults", "catalog_file", "check_board", "check_constraints", "constraints", "design", "drawing_day", "embedment_m", "excel_rows", "faces", "groups_in", "iec_60617_for", "main", "matching", "pv_parts_colours", "read_excel", "resolve_criteria", "root", "rules", "sectors", "symbol_for", "tilted_box", "write", "write_all", "write_assembly", "write_document", "write_excel", "write_tables"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_drawing import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
