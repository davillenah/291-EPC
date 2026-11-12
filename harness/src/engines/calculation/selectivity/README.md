# epc_selectivity

Status: **implemented**

Calculation engine split out of `epc_aea90364` in MIG-37b: protection against indirect contact by supply scheme and coordination of the protective devices.

## Modules
`aea_protection`. The modules were moved unchanged (same code, same line numbers); `epc_aea90364` keeps a shim with each old module name that is the same module object, so `from epc_aea90364 import <module>` still works.

## Depends on
`epc_calc_common`, `epc_grounding`, `epc_load_balance`. It never imports `epc_aea90364`.

## Tests
`python -m unittest discover -s tests` from this folder (put every engine `src/` on `PYTHONPATH`, as the gate does). The remaining unit tests of these modules are in `../aea90364/tests` and run through the shims.
