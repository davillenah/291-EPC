"""Compatibility shim (MIG-37b): `aea_earthing` moved to `epc_grounding.aea_earthing` (engine `grounding`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

from epc_grounding import aea_earthing as _moved

sys.modules[__name__] = _moved
