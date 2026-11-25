"""The DXF output moved into `epc_draw.core` (ADR-0042). This package is a door: `epc_dxf` and every `epc_dxf.<module>` are the same objects as `epc_draw.core` and `epc_draw.core.<module>`."""
import importlib
import importlib.abc
import importlib.util
import sys

from epc_draw import core as _core

__version__ = "0.1.0"
__all__ = list(_core.__all__)


class _Door(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """`import epc_dxf.<name>` gives the module `epc_draw.core.<name>` itself (one copy, so classes and settings are shared)."""

    def find_spec(self, name, path=None, target=None):
        if name.startswith("epc_dxf."):
            return importlib.util.spec_from_loader(name, self)
        return None

    def create_module(self, spec):
        return importlib.import_module("epc_draw.core." + spec.name.split(".", 1)[1])

    def exec_module(self, module):
        return None


if not any(isinstance(f, _Door) for f in sys.meta_path):
    sys.meta_path.insert(0, _Door())


def __getattr__(name):
    return getattr(_core, name)
