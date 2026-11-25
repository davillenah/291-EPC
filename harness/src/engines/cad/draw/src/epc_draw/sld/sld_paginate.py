"""Draws an SLD in one or several sheets from ONE workbook, as a function (ADR-0038).
`paginate(lib, xlsx, out, name, lamina, modblock, maxl=18, environ=None, stamp_date=None)` splits the roots (and their descendants) into sheets of up to `maxl` leaf circuits and
draws each one in process with `sld_generator.generate`; if all fit in one sheet only <NAME> is drawn. The calculation and the sheet options come in `environ`, never from the process.
Command line (thin adapter): python -m epc_draw.sld.sld_paginate <lib> <input.xlsx> <out_dir> <NAME> <lamina.svg> <mod_block.svg> [max_salidas=18]"""
import sys, os
from epc_draw.sld import board_table, sld_generator


def _circuits(xlsx):
    """(rows, index of the PARENT_TAG column) of the CIRCUITOS sheet, header excluded."""
    rows = board_table.load(xlsx)[1]
    hi = next(i for i, r in enumerate(rows) if r and r[0] == 'TAG')
    return [r for r in rows[hi+1:] if r and r[0]], list(rows[hi]).index('PARENT_TAG')


def _leaf_count(tag, kids):
    return 1 if tag not in kids else sum(_leaf_count(k, kids) for k in kids[tag])


def _roots_and_kids(data, pcol):
    """The root tags (no parent, or a parent outside the board) and the children of each tag."""
    tags = {str(r[0]).strip() for r in data}
    kids = {}
    for r in data:
        if r[pcol]:
            kids.setdefault(str(r[pcol]).strip(), []).append(str(r[0]).strip())
    roots = [str(r[0]).strip() for r in data if not r[pcol] or str(r[pcol]).strip() not in tags]
    return roots, kids


def _sheet_groups(data, pcol, maxl):
    """The roots (with their descendants) split into sheets of up to `maxl` leaf circuits."""
    roots, kids = _roots_and_kids(data, pcol)
    groups, cur, cnt = [], [], 0
    for t in roots:
        n = _leaf_count(t, kids)
        if cur and cnt + n > maxl:
            groups.append(cur)
            cur, cnt = [], 0
        cur.append(t)
        cnt += n
    return groups + ([cur] if cur else [])


def _diagram_sheet(base, name, i, groups, names):
    """(sheet name, its environment) for diagram sheet `i` (1-based)."""
    env = dict(base, SLD_INDEX=str(i), SLD_TOTAL=str(len(groups) + 1), SLD_NAMES=names, SLD_SIN_TABLA='1')
    env.pop('SLD_SOLO_TABLA', None)
    if len(groups) == 1:
        for k in ('SLD_SUBSET', 'SLD_TITLE_SUFFIX', 'SLD_PREV', 'SLD_NEXT'):
            env.pop(k, None)
        return name, env
    env.update(SLD_SUBSET=','.join(groups[i-1]), SLD_TITLE_SUFFIX=f'(hoja {i} de {len(groups)})',
               SLD_PREV=str(i-1) if i > 1 else '', SLD_NEXT=str(i+1) if i < len(groups) else '')
    return f'{name}_H{i}', env


def _table_sheet(base, n_groups, names):
    """The environment of the calculation-table sheet (all circuits, no diagram)."""
    env = dict(base, SLD_NAMES=names, SLD_INDEX=str(n_groups + 1), SLD_TOTAL=str(n_groups + 1), SLD_SOLO_TABLA='1', SLD_TITLE_SUFFIX='(tabla de cálculo)')
    for k in ('SLD_SIN_TABLA', 'SLD_SUBSET', 'SLD_PREV', 'SLD_NEXT'):
        env.pop(k, None)
    return env


def _sheets(lib, xlsx, name, maxl, environ, make):
    """Draws every sheet with `make(sheet name, environment)` and returns the names, diagram sheets first, then the calculation table."""
    base = dict(os.environ if environ is None else environ)
    data, pcol = _circuits(xlsx)
    groups = _sheet_groups(data, pcol, maxl)
    table = f'{name}_TABLA'                                    # calculation table: its own sheet, with all the circuits
    diagrams = [name if len(groups) == 1 else f'{name}_H{k}' for k in range(1, len(groups) + 1)]
    names = ','.join(diagrams + [table])                       # one title block row per sheet (diagrams + table)
    for i in range(1, len(groups) + 1):
        make(*_diagram_sheet(base, name, i, groups, names))
    make(table, _table_sheet(base, len(groups), names))
    return diagrams + [table]


def paginate(lib, xlsx, out, name, lam='default', mod='default', maxl=18, environ=None, stamp_date=None):
    """Returns the names of the sheets drawn, in order (diagram sheets, then the calculation table)."""
    return _sheets(lib, xlsx, name, maxl, environ, lambda sheet, env: sld_generator.generate(lib, xlsx, out, sheet, lam, mod, environ=env, stamp_date=stamp_date))


def paginate_files(lib, xlsx, name, lam='default', mod='default', maxl=18, environ=None, stamp_date=None):
    """`paginate` with the sheets as data: ({file name: bytes}, notes). Nothing is written."""
    files, notes = {}, []

    def make(sheet, env):
        made, said = sld_generator.generate_files(lib, xlsx, sheet, lam, mod, environ=env, stamp_date=stamp_date)
        files.update(made)
        notes.extend(said)
    _sheets(lib, xlsx, name, maxl, environ, make)
    return files, notes


def main(argv=None, environ=None):
    a = sys.argv[1:] if argv is None else argv
    for n in paginate(*a[:6], maxl=int(a[6]) if len(a) > 6 else 18, environ=environ):
        print(n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
