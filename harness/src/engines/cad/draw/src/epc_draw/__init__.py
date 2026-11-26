"""One drawing engine (ADR-0042): the common core (`epc_draw.core`: DXF, layers, stamp, deliverable) and one function per kind of drawing.

Every function receives all its data and returns the drawing as bytes; the caller writes the files. The old packages (`epc_dxf`, ...) are doors to what moved here."""
__version__ = "0.1.0"
