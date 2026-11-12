"""Compatibility shim (MIG-37b): `current_and_loads` moved to `epc_load_balance.current_and_loads` (engine `load_balance`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

if __name__ == "__main__":                                  # `python -m epc_aea90364.current_and_loads` keeps working
    import runpy
    runpy.run_module("epc_load_balance.current_and_loads", run_name="__main__")
else:
    from epc_load_balance import current_and_loads as _moved
    sys.modules[__name__] = _moved
