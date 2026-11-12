"""Compatibility shim (MIG-37b): `short_circuit` moved to `epc_short_circuit.short_circuit` (engine `short_circuit`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

if __name__ == "__main__":                                  # `python -m epc_aea90364.short_circuit` keeps working
    import runpy
    runpy.run_module("epc_short_circuit.short_circuit", run_name="__main__")
else:
    from epc_short_circuit import short_circuit as _moved
    sys.modules[__name__] = _moved
