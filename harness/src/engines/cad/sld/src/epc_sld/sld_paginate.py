"""Draws an SLD in one or several sheets from ONE workbook, as a function (ADR-0038).
`paginate(lib, xlsx, out, name, lamina, modblock, maxl=18, environ=None, stamp_date=None)` splits the roots (and their descendants) into sheets of up to `maxl` leaf circuits and
draws each one in process with `sld_generator.generate`; if all fit in one sheet only <NAME> is drawn. The calculation and the sheet options come in `environ`, never from the process.
Command line (thin adapter): python -m epc_sld.sld_paginate <lib> <input.xlsx> <out_dir> <NAME> <lamina.svg> <mod_block.svg> [max_salidas=18]"""
import sys, os, openpyxl
from epc_sld import sld_generator


def paginate(lib, xlsx, out, name, lam='default', mod='default', maxl=18, environ=None, stamp_date=None):
    """Returns the names of the sheets drawn, in order (diagram sheets, then the calculation table)."""
    base = dict(os.environ if environ is None else environ)
    wb = openpyxl.load_workbook(xlsx)
    rows = list(wb['CIRCUITOS'].iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r and r[0] == 'TAG')
    hdr = list(rows[hi]); pcol = hdr.index('PARENT_TAG')
    data = [r for r in rows[hi+1:] if r and r[0]]
    tags = {str(r[0]).strip() for r in data}
    kids = {}
    for r in data:
        if r[pcol]: kids.setdefault(str(r[pcol]).strip(), []).append(str(r[0]).strip())
    def leaves(t): return 1 if t not in kids else sum(leaves(k) for k in kids[t])
    roots = [str(r[0]).strip() for r in data if not r[pcol] or str(r[pcol]).strip() not in tags]
    groups, cur, cnt = [], [], 0
    for t in roots:
        n = leaves(t)
        if cur and cnt + n > maxl:
            groups.append(cur); cur, cnt = [], 0
        cur.append(t); cnt += n
    if cur: groups.append(cur)
    TABLA = f'{name}_TABLA'                      # tabla de cálculo: lámina propia, con todos los circuitos
    nombres_diag = [name if len(groups) == 1 else f'{name}_H{k}' for k in range(1, len(groups) + 1)]
    todos = ','.join(nombres_diag + [TABLA])     # una fila de rótulo por lámina (diagramas + tabla)
    for i, g in enumerate(groups, 1):
        env = dict(base)
        env['SLD_INDEX'] = str(i); env['SLD_TOTAL'] = str(len(groups) + 1)
        env['SLD_NAMES'] = todos
        env.pop('SLD_SOLO_TABLA', None)
        env['SLD_SIN_TABLA'] = '1'
        if len(groups) == 1:
            nm = name
            for k in ('SLD_SUBSET','SLD_TITLE_SUFFIX','SLD_PREV','SLD_NEXT'): env.pop(k, None)
        else:
            nm = f'{name}_H{i}'
            env['SLD_SUBSET'] = ','.join(g)
            env['SLD_TITLE_SUFFIX'] = f'(hoja {i} de {len(groups)})'
            env['SLD_PREV'] = str(i-1) if i > 1 else ''
            env['SLD_NEXT'] = str(i+1) if i < len(groups) else ''
        sld_generator.generate(lib, xlsx, out, nm, lam, mod, environ=env, stamp_date=stamp_date)

    # hoja de tabla de cálculo (todos los circuitos, sin diagrama)
    env = dict(base)
    env['SLD_NAMES'] = todos
    env['SLD_INDEX'] = str(len(groups) + 1); env['SLD_TOTAL'] = str(len(groups) + 1)
    env['SLD_SOLO_TABLA'] = '1'
    env.pop('SLD_SIN_TABLA', None)
    for k in ('SLD_SUBSET', 'SLD_PREV', 'SLD_NEXT'): env.pop(k, None)
    env['SLD_TITLE_SUFFIX'] = '(tabla de cálculo)'
    sld_generator.generate(lib, xlsx, out, TABLA, lam, mod, environ=env, stamp_date=stamp_date)
    return nombres_diag + [TABLA]


def main(argv=None, environ=None):
    a = sys.argv[1:] if argv is None else argv
    for n in paginate(*a[:6], maxl=int(a[6]) if len(a) > 6 else 18, environ=environ):
        print(n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
