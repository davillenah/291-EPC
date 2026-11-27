"""Moved to `epc_report.core.transmittal_pdf` (ADR-0043). This module is a door: it is the same module object."""
import sys

from epc_report.core import transmittal_pdf as _moved

sys.modules[__name__] = _moved
