"""Compatibility shim (MIG-37b): `aea_tables` moved to `epc_calc_common.aea_tables` (engine `calc_common`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

from epc_calc_common import aea_tables as _moved

sys.modules[__name__] = _moved
