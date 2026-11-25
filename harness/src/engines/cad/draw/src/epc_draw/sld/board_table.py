"""The board table the single-line diagram draws from: the TABLERO rows (field, value) and the CIRCUITOS rows (a header, then one row per circuit).

It comes either from a workbook (the plugin's example, and the command line) or straight from data (`{"tablero": {field: value}, "circuitos": [{column: value}], "columnas": [column, ...]}` (the last is optional)), so a caller that already
holds the data does not write a file for the generator to read back (DGM-16 step 4, OPT-03). Both give the same rows, so the drawing is the same."""
from typing import List, Tuple


def _from_data(source: dict) -> Tuple[List[tuple], List[tuple]]:
    board = [("DATOS DEL TABLERO",), ("CAMPO", "VALOR")] + [(k, v) for k, v in source["tablero"].items()]
    header: List[str] = list(source.get("columnas") or [])      # the columns in their order (so an empty board still has its header)
    for row in source["circuitos"]:
        header += [k for k in row if k not in header]
    circuits = [("CIRCUITOS",), tuple(header)] + [tuple(row.get(k) for k in header) for row in source["circuitos"]]
    return board, circuits


def _from_workbook(path) -> Tuple[List[tuple], List[tuple]]:
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    return list(wb["TABLERO"].iter_rows(values_only=True)), list(wb["CIRCUITOS"].iter_rows(values_only=True))


def load(source) -> Tuple[List[tuple], List[tuple]]:
    """(TABLERO rows, CIRCUITOS rows) of a workbook path or of a data dictionary."""
    return _from_data(source) if isinstance(source, dict) else _from_workbook(source)
