"""The project's electrical system and its phase-to-earth voltage U0 (owner decision D16).

The project defines ONE system: 230/400 V (U0 = 230 V) or 220/380 V (U0 = 220 V). The mapping line voltage -> U0 is data (`system_voltages.json` in the normative folder, read through `norm_data`); `system_u0` is the only
function that turns a nominal line voltage into U0, and every safety check (Zs, fault current, automatic disconnection, indirect contact, minimum Icc, the memo) calls it. No module
keeps its own U0 literal. The line voltage a board states without a value is the engine default of `aea_tables.json` (`tension_nominal_defecto_v`, three-phase).

Two optional board keys state the two levels of one installation when a project needs it: `TENSION_SECUNDARIO_V` (transformer secondary, the source side) and `TENSION_USO_V` (points of
use, the load side). Both default to the board's `TENSION_V`, so nothing changes unless a project states them. U0 always follows `TENSION_V` (the system defined for the project).
The same keys exist in lower case for the memo/drawing board (`voltage_v`, `secondary_voltage_v`, `use_voltage_v`)."""
from epc_load_balance import aea_demand as DEM
from epc_calc_common import norm_data
from epc_load_balance.errors import LoadBalanceError

_CACHE = {}
KEYS_NOMINAL = ("TENSION_V", "voltage_v")
KEYS_SECONDARY = ("TENSION_SECUNDARIO_V", "secondary_voltage_v")
KEYS_USE = ("TENSION_USO_V", "use_voltage_v")


def systems():
    """{line voltage [V]: U0 [V]} for the systems of D16."""
    if not _CACHE:
        rows = norm_data.read_json(norm_data.path("system_voltages.json"))["systems"]
        _CACHE.update({float(r["un_v"]): float(r["u0_v"]) for r in rows})
    return dict(_CACHE)


def default_un_v():
    """Line voltage of a board that states none (the engine default, aea_tables.json)."""
    return float(DEM.U_TRI_V)


def system_u0(un_v):
    """U0 [V] of the system whose line voltage is `un_v` (400 -> 230, 380 -> 220). A voltage that is not a D16 system is refused: the engine never guesses a U0."""
    table = systems()
    try:
        return table[float(un_v)]
    except (KeyError, TypeError, ValueError):
        raise LoadBalanceError("err_voltage_system", un_v=un_v, systems=sorted(table)) from None


def _first(board, keys):
    for key in keys:
        if board.get(key) not in (None, ""):
            return float(board[key])
    return None


def board_un_v(board):
    """Nominal line voltage of the board (TENSION_V / voltage_v), the engine default when the board states none."""
    value = _first(board, KEYS_NOMINAL)
    return default_un_v() if value is None else value


def board_u0(board):
    """U0 of the board's system."""
    return system_u0(board_un_v(board))


def board_voltages(board):
    """{'nominal_v', 'secondary_v', 'use_v'}: secondary and use default to the nominal voltage of the board."""
    nominal = board_un_v(board)
    secondary, use = _first(board, KEYS_SECONDARY), _first(board, KEYS_USE)
    return {"nominal_v": nominal, "secondary_v": nominal if secondary is None else secondary, "use_v": nominal if use is None else use}


def board_use_v(board):
    """Line voltage at the points of use (load current, voltage drop)."""
    return board_voltages(board)["use_v"]
