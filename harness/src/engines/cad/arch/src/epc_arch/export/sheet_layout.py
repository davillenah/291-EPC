"""The sheet around the plan: frame, title block, graphic scale and north arrow, all in layer A-TITLE and in paper millimetres."""
from typing import Tuple

from epc_arch.drawing import Drawing, Poly, TextItem
from epc_arch.model import Architecture

LAYER = "A-TITLE"


def _rect(x0: float, y0: float, x1: float, y1: float, fill=None) -> Poly:
    return Poly(((x0, y0), (x1, y0), (x1, y1), (x0, y1)), LAYER, closed=True, fill=fill)


def _block(d: Drawing, arch: Architecture, style, x0: float, y0: float, x1: float, y1: float) -> None:
    d.items.append(_rect(x0, y0, x1, y1))
    rows = 4
    h = (y1 - y0) / rows
    for k in range(1, rows):
        d.items.append(Poly(((x0, y0 + k * h), (x1, y0 + k * h)), LAYER))
    pad = 3.0
    scale = f"1:{d.scale}" if arch.units_per_metre else "S/E"
    d.items += [TextItem(d.title, (x0 + pad, y0 + h * 0.7), "TXT_50", LAYER, bold=True),
                TextItem(f"ESCALA {scale}", (x0 + pad, y0 + h * 1.7), "TXT_35", LAYER),
                TextItem(d.document or arch.source, (x0 + pad, y0 + h * 2.7), "TXT_25", LAYER),
                TextItem(f"HOJA {d.sheet}", (x0 + pad, y0 + h * 3.7), "TXT_25", LAYER)]


def add_scale_bar(d: Drawing, arch: Architecture, x: float, y: float) -> None:
    if not arch.units_per_metre:
        return
    metres = 5
    seg = 1000.0 / d.scale
    for i in range(metres):
        d.items.append(_rect(x + i * seg, y, x + (i + 1) * seg, y + 1.5))
    d.items += [TextItem("0", (x, y - 1.5), "TXT_25", LAYER, "middle"), TextItem(f"{metres} m", (x + metres * seg, y - 1.5), "TXT_25", LAYER, "middle")]


def _north(d: Drawing, x: float, y: float) -> None:
    d.items += [Poly(((x, y), (x, y + 14.0)), LAYER), Poly(((x, y), (x - 2.5, y + 6.0), (x + 2.5, y + 6.0)), LAYER, closed=True),
                TextItem("N", (x, y - 1.5), "TXT_35", LAYER, "middle")]


def add_sheet(d: Drawing, arch: Architecture, style, free: Tuple[float, float, float, float]) -> None:
    W, H = d.size
    mg = style.sheet["margin_mm"]
    bw, bh = style.sheet["block_mm"] if W >= 420 else style.sheet["block_min_mm"]
    d.items.append(_rect(mg["left"], mg["other"], W - mg["other"], H - mg["other"]))
    _block(d, arch, style, W - mg["other"] - bw, H - mg["other"] - bh, W - mg["other"], H - mg["other"])
    add_scale_bar(d, arch, mg["left"] + 10.0, H - mg["other"] - 8.0)
    _north(d, free[2] - 10.0, free[1] + 8.0)
