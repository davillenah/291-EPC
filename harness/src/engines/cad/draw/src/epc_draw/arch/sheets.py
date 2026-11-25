"""The sheet an architecture is drawn on. The engine takes the IRAM sheet as DATA (`template=`, a `SheetTemplate` read from the SVG that `epc_titleblock` makes) and never makes it itself: it does not import
`epc_titleblock` and starts no process (COD-01, DGM-16). Without a template it draws on its own simple frame. The command line, which is an adapter, fetches the sheet (`cli_v2.iram_template`)."""
from epc_draw.arch.export.sheet_iram import SheetTemplate, load_template

FORMATS = ("A0", "A1", "A2", "A3", "A4")
DEFAULT_FORMAT = "A1"


def template_from_svg(svg: str) -> SheetTemplate:
    """The sheet of an IRAM SVG (the one `epc_titleblock.build(...)["svg"]` gives), ready for `template=`."""
    return load_template(svg)
