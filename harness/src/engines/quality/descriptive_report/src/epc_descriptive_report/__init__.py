"""descriptive_report: the descriptive report (memoria descriptiva) of a board as structured data (and its Spanish plain-text rendering).

Pure functions, standard library only. It DESCRIBES the installation from structures already produced (the design-basis document, the circuit summary, the
terminal-list totals, the BOQ totals); it calculates nothing and invents nothing: the only operation on the data is counting. The engine owns no data.
"""
from epc_descriptive_report.build import build_descriptive_report
from epc_descriptive_report.text import descriptive_report_to_text
from epc_descriptive_report.errors import DescriptiveReportError

__all__ = ["build_descriptive_report", "descriptive_report_to_text", "DescriptiveReportError"]
__version__ = "0.1.0"
