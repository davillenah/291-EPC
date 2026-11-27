"""Moved to `epc_report.core.report_docx` (ADR-0043). This module is a door: it is the same module object."""
import sys

from epc_report.core import report_docx as _moved

sys.modules[__name__] = _moved
