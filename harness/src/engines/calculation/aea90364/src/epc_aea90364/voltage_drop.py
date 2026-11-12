"""Compatibility shim (MIG-37b): `voltage_drop` moved to `epc_voltage_drop.voltage_drop` (engine `voltage_drop`). The old name stays for one release and IS the new module (same object), so every public and private name, module-level attribute and monkeypatch behaves as before."""
import sys

if __name__ == "__main__":                                  # `python -m epc_aea90364.voltage_drop` keeps working
    import runpy
    runpy.run_module("epc_voltage_drop.voltage_drop", run_name="__main__")
else:
    from epc_voltage_drop import voltage_drop as _moved
    sys.modules[__name__] = _moved
