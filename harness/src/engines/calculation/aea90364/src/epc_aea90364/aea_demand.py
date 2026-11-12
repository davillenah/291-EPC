"""Compatibility shim (MIG-37b): `aea_demand` moved to `epc_load_balance.aea_demand` (engine `load_balance`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

from epc_load_balance import aea_demand as _moved

sys.modules[__name__] = _moved
