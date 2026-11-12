"""Compatibility shim (MIG-37b): `policy` moved to `epc_calc_common.policy` (engine `calc_common`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

from epc_calc_common import policy as _moved

sys.modules[__name__] = _moved
