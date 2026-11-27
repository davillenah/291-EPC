"""A workbook of tables: one sheet per table, the first row its column titles. Used to issue the tables of the documents (cable list, load schedule, studies) as Excel files."""
from pathlib import Path
from typing import List, Sequence, Tuple

MAX_SHEET_NAME = 31                           # the limit of Excel
FORBIDDEN = "[]:*?/" + chr(92)


def sheet_name(wanted: str, taken: Sequence[str]) -> str:
    """A valid and unique sheet name: at most 31 characters, none of the forbidden ones, numbered when it is already taken."""
    base = "".join("_" if ch in FORBIDDEN else ch for ch in wanted)[:MAX_SHEET_NAME] or "sheet"
    name, n = base, 1
    while name in taken:
        n += 1
        suffix = f"~{n}"
        name = base[:MAX_SHEET_NAME - len(suffix)] + suffix
    return name


def write_tables(path: Path, tables: List[Tuple[str, Sequence[str], Sequence[Sequence]]]) -> bool:
    """Write `tables` ([(sheet name, columns, rows)]) to the workbook `path`; False (nothing written) when there is no table."""
    if not tables:
        return False
    from openpyxl import Workbook
    book = Workbook()
    book.remove(book.active)
    for wanted, columns, rows in tables:
        sheet = book.create_sheet(sheet_name(wanted, book.sheetnames))
        sheet.append(list(columns))
        for row in rows:
            sheet.append(list(row))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    book.save(path)
    return True
