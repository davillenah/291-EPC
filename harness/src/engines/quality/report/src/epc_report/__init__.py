"""One report engine (ADR-0043, proposed): the common kernel (`epc_report.core`: PDF, DOCX and XLSX writers, cover page, logos, transmittal) and, later, one function per kind of report.

The calculation engines only calculate; this engine composes and exports. Step 1 of the move: the writers of `epc_drawing.export` live here; `epc_drawing.export.<module>` stays a door to them."""
__version__ = "0.1.0"
