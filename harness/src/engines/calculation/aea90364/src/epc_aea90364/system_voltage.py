"""Compatibility shim (MIG-37b): `system_voltage` moved to `epc_load_balance.system_voltage` (engine `load_balance`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

from epc_load_balance import system_voltage as _moved

sys.modules[__name__] = _moved
