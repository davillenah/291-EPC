"""Compatibility shim (MIG-37b): `cable_thermal` moved to `epc_feeder_sizing.cable_thermal` (engine `feeder_sizing`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

if __name__ == "__main__":                                  # `python -m epc_aea90364.cable_thermal` keeps working
    import runpy
    runpy.run_module("epc_feeder_sizing.cable_thermal", run_name="__main__")
else:
    from epc_feeder_sizing import cable_thermal as _moved
    sys.modules[__name__] = _moved
