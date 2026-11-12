"""rfq: the draft request for quotation (pedido de cotizacion) of a board, built from the bill of quantities and, optionally, the datasheets.

Pure functions, standard library only, no data tables. The commercial terms (suppliers, currency, deadline, delivery site, validity) are explicit inputs
with no defaults. The engine never sets a price or a commercial value, never contacts anyone and never reads a file: it builds the request document.
"""
from epc_rfq.build import build_rfq, render_rows
from epc_rfq.text import rfq_to_text

__all__ = ["build_rfq", "render_rows", "rfq_to_text"]
__version__ = "0.1.0"
