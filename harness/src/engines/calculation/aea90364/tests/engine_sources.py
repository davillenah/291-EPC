"""Where the source files of the calculation chain are (MIG-37b).

The modules that used to live in `epc_aea90364` are spread over the packages `epc_calc_common`, `epc_load_balance`, `epc_voltage_drop`, `epc_feeder_sizing`, `epc_short_circuit`,
`epc_grounding` and `epc_selectivity`; `epc_aea90364` keeps a shim with each old module name. The source scans of the tests (no literal copies of norm data) must still read EVERY real
source file under its file name, so they ask here instead of listing one folder."""
import importlib
import os

PACKAGES = ("epc_aea90364", "epc_calc_common", "epc_load_balance", "epc_voltage_drop", "epc_feeder_sizing", "epc_short_circuit", "epc_grounding", "epc_selectivity")
SHIM_MARK = "Compatibility shim (MIG-37b)"


def _dirs():
    return [os.path.dirname(os.path.abspath(importlib.import_module(p).__file__)) for p in PACKAGES]


def _is_shim(path):
    with open(path, encoding="utf-8") as f:
        return SHIM_MARK in f.read(400)


def _files():
    out = {}
    for d in _dirs():
        for f in sorted(os.listdir(d)):
            path = os.path.join(d, f)
            if f.endswith(".py") and f not in out and not _is_shim(path):
                out[f] = path
    return out


def listdir():
    """The file names of the real source modules of the chain (the same names `os.listdir` gave for the single package)."""
    return sorted(_files())


def join(fname):
    """Full path of the real source file `fname`."""
    return _files()[fname]
