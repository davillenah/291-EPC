"""Compatibility shim (MIG-37b): `aea_protection` moved to `epc_selectivity.aea_protection` (engine `selectivity`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

from epc_selectivity import aea_protection as _moved

sys.modules[__name__] = _moved
