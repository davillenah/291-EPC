"""The public entry point of the multi-line diagram (OPT-02, ADR-0040): `draw(entrada, out_dir, name)`.

Same shape as `epc_draw.sld.draw`: `MldInput` holds everything the drawing needs (the board data, its calculation, the title block request, the date and the options), nothing is read from the process
environment, and the answer is the list of sheets drawn. `generate` stays as the lower-level call; `draw` only checks the input and hands it over, so the bytes are the same."""
from dataclasses import dataclass
from typing import Any, List, Mapping, Optional

from epc_draw.mld.mld_generator import XMAX, X0, generate


@dataclass(frozen=True)
class MldInput:
    """Everything the multi-line diagram needs."""
    data: Mapping[str, Any]                         # the board form data (board, circuits, titleblock)
    calc: Mapping[str, Any]                         # {"datos": {TAG: {...}}, "detalle": {TAG: {...}}} (contract of `aea_export`)
    lib: Optional[str] = None                       # symbol library folder (None: the one of epc_mld)
    maxw: float = XMAX - X0                         # usable sheet width
    stamp_date: Optional[str] = None                # ISO date that fixes every date in the files
    titleblock_request: Optional[Mapping[str, Any]] = None   # request to the title block service (None: built from `data["titleblock"]`)


def draw(entrada: MldInput, out_dir: Any, name: str, log: Optional[List[str]] = None) -> List[dict]:
    """Draws the multi-line diagram of one board into `out_dir` (SVG and DXF per sheet) and returns the sheets made. The notices go to `log` (None: printed to stderr)."""
    if not isinstance(entrada, MldInput):
        raise TypeError("draw() takes an MldInput")
    return generate(dict(entrada.data), dict(entrada.calc), out_dir, name, lib=entrada.lib, maxw=entrada.maxw, stamp_date=entrada.stamp_date,
                    titleblock_request=dict(entrada.titleblock_request) if entrada.titleblock_request is not None else None, log=log)
