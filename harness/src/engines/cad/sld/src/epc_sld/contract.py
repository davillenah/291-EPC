"""The public entry point of the single-line diagram (DGM-16, ADR-0038): `draw(entrada, out_dir, name, maxl, stamp_date)`.

The engine is a function: `SldInput` holds everything it needs (the board workbook, the calculation, the figures, the title block request and the sheet options), nothing is read from the process
environment, and the answer is the list of sheets drawn. The files it names are the contract of `epc_aea90364` (`aea_export`, `board_figures`) and of the title block service."""
import os
import sys
from dataclasses import dataclass
from typing import List, Optional

from epc_sld.errors import SldError

FORMATS = ("A1", "A3")


@dataclass(frozen=True)
class SldInput:
    """Everything the diagram needs. Paths are files on disk; `layout_json` and `titleblock_json` are optional."""
    calc_json: str                     # {TAG: {In, Ib, icu, S, dU, disp}} (aea_export)
    detail_json: str                   # {TAG: {limite_pct, du_propia_pct, ...}}
    figures_json: str                  # bar, feeder, checks and notes (board_figures)
    board: Optional[dict] = None       # the board as data: {"tablero": {field: value}, "circuitos": [{column: value}]} (no workbook needed)
    xlsx: Optional[str] = None         # or the board workbook (sheets TABLERO and CIRCUITOS): one of the two is required
    titleblock_json: Optional[str] = None
    layout_json: Optional[str] = None  # positions the person moved by hand
    formato: str = "A1"                # "A1" or "A3"
    lib: str = "default"               # symbol library ("default" = the one of epc_symbols)
    lamina: str = "default"
    modblock: str = "default"


def _check_files(entrada: SldInput) -> None:
    for field in ("calc_json", "detail_json", "figures_json"):
        if not getattr(entrada, field):
            raise SldError("err_sld_field_missing", field=field)
    if not entrada.xlsx and entrada.board is None:
        raise SldError("err_sld_field_missing", field="board")
    for field in ("xlsx", "calc_json", "detail_json", "figures_json", "titleblock_json", "layout_json"):
        value = getattr(entrada, field)
        if value and not os.path.isfile(value):
            raise SldError("err_sld_file_missing", field=field, path=value)


def _check(entrada: SldInput, maxl) -> None:
    _check_files(entrada)
    if entrada.formato not in FORMATS:
        raise SldError("err_sld_format_invalid", value=entrada.formato)
    if isinstance(maxl, bool) or not isinstance(maxl, int) or maxl < 1:
        raise SldError("err_sld_maxl_invalid", value=maxl)


def environ_of(entrada: SldInput) -> dict:
    """The environment dictionary the sheet generator reads (the adapter between the contract and the generator); never the process environment."""
    env = {"SLD_CALC_JSON": entrada.calc_json, "SLD_CALC_DETAIL": entrada.detail_json, "SLD_FIGURES_JSON": entrada.figures_json, "SLD_FORMATO": entrada.formato}
    if entrada.titleblock_json:
        env["EPC_TITLEBLOCK_JSON"] = entrada.titleblock_json
    if entrada.layout_json:
        env["SLD_LAYOUT_JSON"] = entrada.layout_json
    return env


def draw_files(entrada: SldInput, name: str, maxl: int = 18, stamp_date: Optional[str] = None) -> dict:
    """`draw` with the sheets as data: {file name: bytes}. The engine writes nothing; the caller puts the bytes where it wants (ADR-0042). Same bytes as the files `draw` writes."""
    _check(entrada, maxl)
    from epc_sld import sld_paginate
    files, notes = sld_paginate.paginate_files(entrada.lib, entrada.board if entrada.board is not None else entrada.xlsx, name, entrada.lamina, entrada.modblock, maxl=maxl, environ=environ_of(entrada), stamp_date=stamp_date)
    for line in notes:
        print(line, file=sys.stderr)
    return files


def draw(entrada: SldInput, out_dir, name: str, maxl: int = 18, stamp_date: Optional[str] = None) -> List[str]:
    """Draws the single-line diagram of one board into `out_dir` (SVG and DXF per sheet) and returns the names of the sheets, diagram sheets first, then the calculation table.
    `stamp_date` (an ISO date) fixes every date in the files, so the same input gives the same bytes. Raises `SldError` when the input is not valid."""
    _check(entrada, maxl)
    from epc_sld import sld_paginate
    return sld_paginate.paginate(entrada.lib, entrada.board if entrada.board is not None else entrada.xlsx, str(out_dir), name, entrada.lamina, entrada.modblock, maxl=maxl, environ=environ_of(entrada), stamp_date=stamp_date)
