# epc-report

One report engine (ADR-0043, proposed): the calculation engines only calculate; this engine composes and exports the reports. Same logic as the drawing engine (`epc_draw`, ADR-0042): one kernel and, later, one function per kind of report, each receiving all its data as arguments and returning bytes.

## Kernel (`epc_report.core`)

The writers moved here from `epc_drawing.export` with the same output: `report_pdf` (A4 PDF with cover, headings, paragraphs, bullets, tables, figures), `report_docx` (Word without libraries), `logo`, `tables_xlsx`, `transmittal_pdf`. The old names (`epc_drawing.export.report_pdf`, ...) are doors: the same module objects.

## Not done yet

- The writers still take a destination path and read the clock (PDF creation date, zip times) and the logo files: the next steps make them return bytes and take date and logos as data (ADR-0043 steps b and d).
- One function per kind of report (PV yield first, then the PV calculation memorandum, summary, savings and economic memorandums) and the text templates as data in English and Spanish.
- The reports built in `epc_aea90364.board_memo` and in `disciplines/electrical_lv/stages/rendering.py` move here later.

Tests: `python -m unittest discover -s tests` (needs `matplotlib`, `openpyxl`, `pillow`, `pypdfium2`).
