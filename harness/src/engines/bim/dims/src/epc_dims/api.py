"""The public door of the engine (COD-02): the names other packages may import. Everything else in the package is internal."""
from epc_dims import (
    DimsError,
    dimensions,
)  # noqa: F401

__all__ = ["DimsError", "dimensions"]
