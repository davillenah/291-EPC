# epc-report

One report engine (ADR-0043, proposed): the calculation engines only calculate; this engine composes and exports the reports. Same logic as the drawing engine (`epc_draw`, ADR-0042): one kernel and, later, one function per kind of report, each receiving all its data as arguments and returning bytes.

## Kernel (`epc_report.core`)

The writers moved here from `epc_drawing.export` with the same output: `report_pdf` (A4 PDF with cover, headings, paragraphs, bullets, tables, figures), `report_docx` (Word without libraries), `logo`, `tables_xlsx`, `transmittal_pdf`. The old names (`epc_drawing.export.report_pdf`, ...) are doors: the same module objects.

## Called as a function

`report_pdf.render_bytes(report, date=None)` and `report_docx.render_bytes(report, date=None)` return the file as bytes and write nothing (`render(report, dst)` is a thin caller). A logo in the cover is a path, bytes or `{"data": bytes}`. With a `date` the same report always gives the same bytes and the clock is not read.

## Kinds of report (`epc_report.pv`, ...)

`epc_report.pv.yield_study.pv_yield_report(document, project, module_weight_kg=None)`: the PV yield study as a report structure, built from the result of `epc_pv` alone (the weight of a module comes from the caller). Moved from `disciplines/electrical_lv/stages/rendering.py` with the same output. `epc_report.core.blocks` holds the blocks every report is made of (`table`, `notes`, `cell`).

## Audit of the report set (`epc_report.core.audit`)

`audit(reports)` returns the findings of a set of reports (missing title, empty report, empty section, duplicate heading, table row of the wrong width, unresolved placeholder, bad value, and the same `facts` key with different values in two documents), each with English and Spanish text. `audit_loop(reports, corrector, max_iterations=5)` audits, calls the corrector (a function the caller gives that returns corrected report dicts, so a correction never leaves this engine), and audits again; it stops when no error is left, when nothing changed, or after five rounds at most. The reviews are internal to the harness: nothing is reported to the owner beyond the final result.

## Not done yet

- The Excel and transmittal writers still take a destination path (the PDF and Word writers already return bytes).
- The text of the PV yield study is still English only (the discipline translates titles and columns afterwards); proper Spanish text comes with the templates.
- The other kinds of report (PV calculation memorandum, summary, descriptive, savings and economic memorandums) and the text templates as data in English and Spanish.
- The auditor agent in the roster (path scope limited to `engines/quality/report`, needs a permission rule) that supplies the corrector.
- The reports built in `epc_aea90364.board_memo` and in `disciplines/electrical_lv/stages/rendering.py` move here later.

Tests: `python -m unittest discover -s tests` (needs `matplotlib`, `openpyxl`, `pillow`, `pypdfium2`).
