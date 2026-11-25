"""The architecture recognition engine moved into `epc_draw.arch` (ADR-0042). This package is a door: `epc_arch` and every `epc_arch.<module>` are the same objects as `epc_draw.arch` and `epc_draw.arch.<module>`."""
import importlib
import importlib.abc
import importlib.util
import sys

from epc_draw import arch as _symbols

__version__ = "0.1.0"
__all__ = list(_symbols.__all__)


class _Door(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """`import epc_arch.<name>` gives the module `epc_draw.arch.<name>` itself (one copy, so classes and settings are shared)."""

    def find_spec(self, name, path=None, target=None):
        if name.startswith("epc_arch.") and name != "epc_arch.__main__":   # `python -m epc_arch` runs the file next to this one
            return importlib.util.spec_from_loader(name, self)
        return None

    def create_module(self, spec):
        return importlib.import_module("epc_draw.arch." + spec.name.split(".", 1)[1])

    def exec_module(self, module):
        return None


if not any(isinstance(f, _Door) and f.__class__.__module__ == __name__ for f in sys.meta_path):
    sys.meta_path.insert(0, _Door())


def __getattr__(name):
    return getattr(_symbols, name)
