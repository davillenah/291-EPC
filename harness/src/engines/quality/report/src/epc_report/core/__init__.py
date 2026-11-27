"""Kernel of the report engine: the writers and the pieces every report shares (ADR-0043, proposed).

Moved byte for byte from `epc_drawing.export` (same output). Modules: `report_pdf`, `report_docx`, `logo`, `tables_xlsx`, `transmittal_pdf`."""

__all__ = ["logo", "report_docx", "report_pdf", "tables_xlsx", "transmittal_pdf"]
