"""EPC drawing engine: IEC 60617 symbols, IRAM sheets and title blocks, single-line (SLD) and multi-line (MLD) diagrams."""
__version__ = "0.1.0"

__all__ = ["DrawingError", "Pen", "assemble", "assemble_board", "audit", "box", "build", "build_board_model", "build_common", "build_sector", "calc_note", "calculate", "catalog_defaults", "catalog_file", "check_board", "check_constraints", "constraints", "design", "drawing_day", "embedment_m", "excel_rows", "faces", "groups_in", "iec_60617_for", "main", "matching", "pv_parts_colours", "read_excel", "resolve_criteria", "root", "rules", "sectors", "symbol_for", "tilted_box", "write", "write_all", "write_assembly", "write_document", "write_excel"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_drawing import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
