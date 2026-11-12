"""Compatibility shim (MIG-37b): `norm_data` moved to `epc_calc_common.norm_data` (engine `calc_common`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

from epc_calc_common import norm_data as _moved

sys.modules[__name__] = _moved
