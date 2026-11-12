# epc_voltage_drop

Status: **implemented**

Calculation engine split out of `epc_aea90364` in MIG-37b: voltage drop of a circuit by the moment method, limits and maximum length.

## Modules
`aea_voltage_drop`, `voltage_drop`. The modules were moved unchanged (same code, same line numbers); `epc_aea90364` keeps a shim with each old module name that is the same module object, so `from epc_aea90364 import <module>` still works.

## Depends on
`epc_calc_common`. It never imports `epc_aea90364`.

## Tests
`python -m unittest discover -s tests` from this folder (put every engine `src/` on `PYTHONPATH`, as the gate does). The remaining unit tests of these modules are in `../aea90364/tests` and run through the shims.
