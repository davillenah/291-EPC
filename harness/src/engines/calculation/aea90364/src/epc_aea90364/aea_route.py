"""Compatibility shim (MIG-37b): `aea_route` moved to `epc_feeder_sizing.aea_route` (engine `feeder_sizing`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

from epc_feeder_sizing import aea_route as _moved

sys.modules[__name__] = _moved
