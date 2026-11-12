"""Compatibility shim (MIG-37b): `aea_icc_factors` moved to `epc_short_circuit.aea_icc_factors` (engine `short_circuit`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

from epc_short_circuit import aea_icc_factors as _moved

sys.modules[__name__] = _moved
