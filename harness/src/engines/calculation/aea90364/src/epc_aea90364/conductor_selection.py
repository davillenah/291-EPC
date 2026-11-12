"""Compatibility shim (MIG-37b): `conductor_selection` moved to `epc_feeder_sizing.conductor_selection` (engine `feeder_sizing`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

if __name__ == "__main__":                                  # `python -m epc_aea90364.conductor_selection` keeps working
    import runpy
    runpy.run_module("epc_feeder_sizing.conductor_selection", run_name="__main__")
else:
    from epc_feeder_sizing import conductor_selection as _moved
    sys.modules[__name__] = _moved
