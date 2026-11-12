"""Compatibility shim (MIG-37b): `aea_voltage_drop` moved to `epc_voltage_drop.aea_voltage_drop` (engine `voltage_drop`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

from epc_voltage_drop import aea_voltage_drop as _moved

sys.modules[__name__] = _moved
