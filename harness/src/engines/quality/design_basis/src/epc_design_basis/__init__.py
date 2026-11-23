"""design_basis: the design-basis document of a project as structured data (and its Spanish plain-text rendering).

Pure functions, standard library only. The profile, the criteria, the assumptions and the requirements are copied; the limits the calculation engines will
apply are READ from those engines' own accessors (imported lazily, only for reading) and never typed here. A limit that cannot be read is an issue, never
a default. The engine owns no data and does not read the norm register: the caller may pass the review status of the register records it knows.
"""
from epc_design_basis.build import build_design_basis_document
from epc_design_basis.text import design_basis_to_text
from epc_design_basis.errors import DesignBasisError

__all__ = ["build_design_basis_document", "design_basis_to_text", "DesignBasisError"]
__version__ = "0.1.0"
