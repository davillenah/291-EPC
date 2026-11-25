#!/usr/bin/env python3
"""Generador referencial de SLD (unifilar BT) desde plantilla MINIMAL v2.

Una hoja (`_Sheet`) se arma por etapas, cada una una función corta: leer la entrada y el cálculo, dibujar acometida, barra, circuitos, cables y cargas,
la tabla, las referencias, el rótulo, y entregar (SVG y DXF). El dibujo no calcula: todo número sale del cálculo de epc_aea90364.
"""
import sys, os, math, json, textwrap, re
from xml.sax.saxutils import escape as xesc
from epc_draw.sld import board_table
from lxml import etree
try:
    import cairosvg  # optional: only needed for PNG previews; requires the Cairo DLL on Windows
except (ImportError, OSError):
    cairosvg = None
from epc_draw.core import roles as ROLES
from epc_draw.symbols import library_dir, resolve, UnknownSymbol

from epc_aea90364.aea_pipeline import TOPOLOGIAS_MOTOR         # which topologies are motors (the choice of symbols); the numbers come from the calculation

X0, YBAR, GAP = 58.0, 85.0, 3.0


def backup_kind(source):
    """'gen' si la acometida viene de un grupo electrógeno, 'ups' si viene de una UPS, '' si no es de respaldo (por el texto de su fuente)."""
    s = str(source or '').lower()
    if re.search(r'(^|\W)ups(\W|$)', s):
        return 'ups'
    return 'gen' if any(k in s for k in ('grupo', 'generador', 'generator', 'genset')) else ''


BLUE, RED, GREEN, BLACK = '#0000ff', '#ff0000', '#139b48', '#000000'
FONT = "Arial, Helvetica, sans-serif"
# Alturas de letra IRAM 4503 (h = altura de mayuscula Arial, 0,716 em):
H_TXT, H_TIT = 2.0, 3.0                      # mm
FS_TXT = round(H_TXT/0.716, 2)               # font-size 2,79 para h 2 mm
FS_TIT = round(H_TIT/0.716, 2)               # font-size 4,19 para h 3 mm
FS_DES = round(2.5/0.716, 2)                # designación del cable en negrita: h 2,5 mm = font 3,49
LS = 3.4                                     # interlineado (mm), ~1,7 h
BUS_END = 638.0   # barra principal y PE: hasta el limite del recuadro gris menos 5 mm
FEEDER_DX = 105.0   # separación entre las acometidas de un tablero (mm): el ancho de su texto
CABLE_H = 52.07   # símbolo lv_cable_run: origen arriba, flecha a 52,07 mm, tramo de salida hasta 60,07 mm
GAP_PE = 5.0
BOX_X0, BOX_Y0, BOX_X1 = 35.0, 20.0, 643.0   # 5 mm desde los limites internos de la hoja
MOD_LISTA = False   # lista de modificaciones (fig. 3): activar sólo cuando la hoja tenga revisiones cargadas
TABLE_COLS = [('TAG', 16), ('DESCRIPCIÓN', 120), ('P [kW]', 18), ('FASE', 14), ('Ib [A]', 18), ('In [A]', 18), ('Icu [kA]', 18),
              ('DISPOSITIVO', 150), ('CABLE F/N [mm²]', 30), ('PE [mm²]', 18), ('L [m]', 16), ('ΔU [%]', 20)]
TW, TX, HH, RH = 610.0, 30.0, 8.0, 6.0
BOARD_KEYS = ('NOMBRE', 'TENSION_V', 'SISTEMA', 'ICC_KA', 'FP_DEFAULT', 'FRECUENCIA_HZ', 'PROYECTO', 'LONG_ACOMETIDA_m')


# ---------- entrada ----------
def _calculo(env, var):
    # El dibujo no calcula: todo número sale del cálculo de epc_aea90364 (aea_pipeline y board_figures), que entrega board_design como archivos JSON.
    #   SLD_CALC_JSON    = {TAG: {In, Ib, icu, S, dU, disp}} (contrato de aea_export)
    #   SLD_CALC_DETAIL  = {TAG: {limite_pct, du_propia_pct, p_kw, pe_mm2, neutro_mm2, kind, ...}}
    #   SLD_FIGURES_JSON = cifras del tablero: barra, acometida, verificaciones y notas (board_figures)
    f = env.get(var)
    if not f:
        sys.exit(f'FALTA {var}: el unifilar solo dibuja; el cálculo lo entrega epc_aea90364 (board_design.design)')
    return json.load(open(f, encoding='utf-8'))


def _num(x):
    return float(x) if x not in (None, '') else None


def _board_header(rows, env):
    """Los datos del tablero de la plantilla; el nombre lleva el sufijo de la hoja (el nombre base es el del rótulo)."""
    tb = {}
    for row in rows:
        if row and row[0] in BOARD_KEYS:
            tb[row[0]] = row[1]
    tb['NOMBRE_BASE'] = tb['NOMBRE']   # nombre sin sufijo de hoja: es el que va al rótulo (el número de hoja está en Página)
    if env.get('SLD_TITLE_SUFFIX'): tb['NOMBRE'] = f"{tb['NOMBRE']} {env['SLD_TITLE_SUFFIX']}"
    return tb


def _upper(value):
    """Un texto de la planilla en mayúsculas y sin espacios (vacío si no hay)."""
    return str(value or '').strip().upper()


def _circuit(tag, d):
    return dict(tag=tag, desc=str(d.get('DESCRIPCION') or ''), carga=_num(d.get('CARGA')),
                unit=str(d.get('UNIDAD_CARGA') or 'kW').strip(), dest=str(d.get('DESTINO') or ''),
                parent=(str(d['PARENT_TAG']).strip() if d.get('PARENT_TAG') else None),
                topo=str(d.get('TOPOLOGY') or 'single').strip().lower(),
                fase=str(d.get('FASE') or '3F').strip().upper(), fase_asig=_upper(d.get('FASE_ASIGNADA')), L=_num(d.get('LONGITUD_m')) or 0.0,
                fp=_num(d.get('FP')), eff=_num(d.get('RENDIMIENTO')),
                kind=str(d.get('KIND') or 'auto').strip().lower(), notas=str(d.get('NOTAS') or ''),
                tipo=str(d.get('CABLE_TIPO') or 'tetra_sep').strip().lower())


def _circuits(rows):
    """Los circuitos de la plantilla por tag, y su orden."""
    hi = next(i for i, r in enumerate(rows) if r and r[0] == 'TAG')
    hdr = [str(h).strip() if h is not None else '' for h in rows[hi]]
    C, order = {}, []
    for r in rows[hi+1:]:
        if not r or r[0] is None: continue
        tag = str(r[0]).strip()
        if tag.lower().startswith(('campo', 'fila')): continue
        C[tag] = _circuit(tag, dict(zip(hdr, r)))
        order.append(tag)
    return C, order


def _children(c, order):
    return {t: [u for u in order if c[u]['parent'] == t] for t in order}


def _roots(c, order):
    """Los circuitos sin padre (o con un padre que no está en la plantilla)."""
    return [t for t in order if not c[t]['parent'] or c[t]['parent'] not in c]


def _subset(env):
    """Las raíces que pide esta hoja (SLD_SUBSET); vacío = todas."""
    return [x.strip() for x in env.get('SLD_SUBSET', '').split(',') if x.strip()]


def _phase_note(r, c):
    """La fase que carga un circuito monofásico, si se asignó (R, S o T)."""
    return f"  ·  {c['fase_asig']}" if r['ph'] == 1 and c.get('fase_asig') in ('R', 'S', 'T') else ''


def _leg_text(r, tipo):
    """La designación de la sección del cable según su tipo y sus fases."""
    S, PE, N = r['S'], r['PE'], r['N']
    if r['ph'] == 1:
        return f"2x{S} mm²" if tipo == 'tetra_inc' else f"2x{S} + PE {PE:g} mm²"
    if tipo == 'unifilar':
        return f"3x1x{S} + 1x{N} + PE {PE:g} mm²"
    if tipo == 'tetra_inc':
        return f"3x{S}/2x{PE:g} mm²"
    return f"3x{S}/{N} mm² + PE {PE:g} mm²"


def _pair(v):
    """Un desplazamiento [dx, dy] en mm; lo que no sea un par de números vale 0."""
    try:
        return float(v[0]), float(v[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return 0.0, 0.0


def _mark(tag, idx):
    """Los atributos con que un símbolo de la cadena de un circuito dice cuál es (circuito y lugar en la cadena); los demás no llevan."""
    return f' data-tag="{xesc(tag)}" data-idx="{idx}"' if tag else ''


def _bind(page, tx, ty, k):
    return f'<g transform="translate({tx:.2f},{ty:.2f}) scale({k:.4f})">' + '\n'.join(page) + '</g>'


def _symbol_texts(tree, typed):
    """Los textos de un símbolo que van fuera de su grupo: los de sus datos (label_slots) y, si `typed`, la etiqueta del tipo de dispositivo (MCB, MCCB, KM...)."""
    texts = tree.xpath("//*[@id='label_slots']") + (tree.getroot().findall('{http://www.w3.org/2000/svg}text') if typed else [])
    return ''.join(etree.tostring(t_, encoding='unicode') for t_ in texts)


def _file_in(lib, sid):
    """iec-symbols >= 0.4.14 names files 291_E_LV_SLD_IEC60617_<id without 'lv_'>.svg; older libraries used <id>.svg: try both."""
    for name in (sid + '.svg', f"291_E_LV_SLD_IEC60617_{sid[3:] if sid.startswith('lv_') else sid}.svg"):
        f = os.path.join(lib, name)
        if os.path.exists(f):
            return f
    return os.path.join(lib, sid + '.svg')


class _SheetLabels:
    @staticmethod
    def annotate(frag):
        """La etiqueta del tipo de dispositivo (MCB, MCCB, KM...) es anotación, como los textos del símbolo."""
        for t_ in frag.xpath("./*[local-name()='text']"):
            t_.set('data-layer', 'sld.text')


class _Sheet:
    """Una hoja del unifilar: lo que se lee, lo que se va dibujando (`d`, en el orden en que se apila) y las medidas que una etapa le pasa a la siguiente."""

    def __init__(self, lib, xlsx, out, name, lamina, modblock, env):
        self.env, self.xlsx, self.out, self.name, self.lamina, self.modblock = env, xlsx, out, name, lamina, modblock
        self.stamp_date = env.get('EPC_STAMP_DATE') or None    # opcional: la fecha del plano (ISO) fija la emisión del rótulo y los sellos del DXF; sin ella, la de hoy
        self.default_lib = lib == 'default'
        self.lib = str(library_dir('sld-lv-symbol')) if self.default_lib else lib       # símbolos: epc_symbols
        self.cat = {i['id']: i for i in json.load(open(os.path.join(self.lib, '_catalog.json'), encoding='utf-8-sig'))['symbols']}
        self.pre, self.det, self.fig = (_calculo(env, v) for v in ('SLD_CALC_JSON', 'SLD_CALC_DETAIL', 'SLD_FIGURES_JSON'))
        self.formato = env.get('SLD_FORMATO', 'A1')            # A1 (por defecto) o A3 (diagrama reducido a la zona útil A3)
        self.a3 = self.formato == 'A3'
        self.s_diag = (400.0 - 35.0) / 608.0 if self.a3 else 1.0       # escala del diagrama y tabla en A3
        self.txt_vis = FS_TXT / self.s_diag if self.s_diag != 1.0 else None   # A3: texto del diagrama y tabla a 2 mm visibles (None = tamaño normal)
        self.sp = 1.6 if self.txt_vis is not None else 1.0   # A3: más separación entre líneas de texto (2 mm) para que no se solapen
        self.d, self.used, self.leaves, self.cache = [], set(), [], {}
        self.blocks = []                    # (desde, hasta, circuito de cabecera): lo que se dibujó de cada circuito, para poder moverlo (SLD_LAYOUT_JSON)
        self.shift_all, self.shift, self.bus_end = (0.0, 0.0), {}, BUS_END
        self.rol = 'sld.diagram'            # rol de las líneas que se dibujan ahora (la tabla y las referencias son anotación: sld.text)
        self.sin_tabla = env.get('SLD_SIN_TABLA', '') == '1'   # la tabla de cálculo sale en su propia lámina
        self.solo_tabla = env.get('SLD_SOLO_TABLA', '') == '1'

    # ---------- entrada y cifras ----------
    def read_board(self):
        board_rows, circuit_rows = board_table.load(self.xlsx)
        self.tb = _board_header(board_rows, self.env)
        self.v, self.icc, self.fpdef = float(self.tb['TENSION_V']), float(self.tb['ICC_KA']), float(self.tb.get('FP_DEFAULT') or 0.85)
        self.c, self.order = _circuits(circuit_rows)
        self.read_structure()
        self.prev_h, self.next_h = self.env.get('SLD_PREV', ''), self.env.get('SLD_NEXT', '')
        self.read_figures()

    def read_structure(self):
        """Quién cuelga de quién, qué raíces entran en esta hoja y el paso entre circuitos que cabe en ella."""
        self.kids = _children(self.c, self.order)
        sub = _subset(self.env)
        self.roots = [t for t in _roots(self.c, self.order) if (not sub or t in sub)]
        self.drawn = set(u for t in self.roots for u in self.descendants(t))
        nl = max(1, len([t for t in self.drawn if not self.kids[t]]))
        self.pitch = min(68.0, (539.0 if sub else 540.0) / nl)   # hoja paginada: 40 mm reservados a la derecha de la barra para 'continua en hoja'
        self.place_roots()
        self.read_layout()

    def descendants(self, t): return [t] + [u for k in self.kids[t] for u in self.descendants(k)]

    def place_roots(self):
        """De qué circuito de la barra cuelga cada uno y dónde está el eje de cada uno de ellos (antes de moverlo)."""
        self.root_of = {u: r for r in self.roots for u in self.descendants(r)}
        self.root_x, x = {}, X0
        for r in self.roots:
            self.root_x[r] = x + self.gw(r) / 2; x += self.gw(r)

    def feeder_to_bus(self, x, k):
        """El cable de una acometida (0 es la primera) desde su Q-GRAL hasta las barras; las dos del interruptor de transferencia llegan a las barras por él."""
        joined = self.transfer_index() and k in (0, self.transfer_index())
        if not joined:
            self.line(x, 75, x, YBAR)

    def feeder_text_x(self, x, f):
        """Dónde empieza el texto de una acometida: a la derecha de su eje o, si viene de una UPS, a la derecha de su caja."""
        return x + (13 if backup_kind(f.get('source')) == 'ups' else 6)

    def transfer_index(self):
        """La posición (1 es la segunda acometida) de la primera acometida de un grupo electrógeno: la que forma la transferencia con la de la red; 0 si no hay."""
        return next((k for k, f in enumerate(self.extra_feeders(), 1) if backup_kind(f.get('source')) == 'gen'), 0)

    def extra_feeders(self):
        """Las acometidas que se dibujan además de la primera (la que está sobre el primer circuito)."""
        return (self.fig.get('feeders') or [])[1:]

    def extra_feeder_x(self, k):
        """El eje de la acometida k (1 es la segunda): una a continuación de la otra, a FEEDER_DX mm."""
        return X0 + self.gw(self.roots[0]) / 2 + k * FEEDER_DX      # el eje de la primera es el del primer circuito (draw_service)

    def bar_start(self, xa):
        """Dónde empieza la barra: en la acometida o, si se movió un circuito más a la izquierda, en ese circuito."""
        return min([xa] + [self.root_x[t] + self.dx(t) for t in self.roots])

    # ---------- posiciones movidas a mano ----------
    def read_layout(self):
        """Las posiciones que se movieron a mano (SLD_LAYOUT_JSON: {"all": [dx, dy], "circuits": {TAG: [dx, 0]}}, en mm): el conjunto se mueve en los dos ejes y cada circuito que cuelga de la barra, a lo ancho."""
        path = self.env.get('SLD_LAYOUT_JSON', '')
        data = json.load(open(path, encoding='utf-8')) if path and os.path.exists(path) else {}
        self.shift_all = _pair(data.get('all'))
        self.shift = {t: _pair(v)[0] for t, v in (data.get('circuits') or {}).items() if t in self.root_x}
        xs = [self.root_x[t] + self.dx(t) for t in self.roots]
        self.bus_end = max(BUS_END, max(xs) + 5.0) if xs else BUS_END          # la barra llega hasta el último circuito
        self.bus_end = max(self.bus_end, self.extra_feeder_x(len(self.extra_feeders())) + 5.0) if self.extra_feeders() else self.bus_end   # y hasta la última acometida

    def dx(self, t): return self.shift.get(self.root_of.get(t, t), 0.0)

    def mark(self, start, tag):
        """Anota que lo dibujado desde `start` hasta ahora es del circuito de cabecera `tag`."""
        if len(self.d) > start: self.blocks.append((start, len(self.d), tag))

    def apply_layout(self):
        """Agrupa lo dibujado de cada circuito en su <g data-circuit> (movido lo que se pidió) y todo el diagrama en <g data-block="all">: así el SVG se puede mover por grupos y el DXF sale donde se dejó."""
        out, pos = [], 0
        for start, end, tag in sorted(self.blocks):
            out += self.d[pos:start]
            dx = self.shift.get(tag, 0.0)
            tr = f' transform="translate({dx:.2f},0)"' if dx else ''
            out.append(f'<g data-circuit="{xesc(tag)}"{tr}>' + '\n'.join(self.d[start:end]) + '</g>')
            pos = end
        out += self.d[pos:]
        ax, ay = self.shift_all
        tr = f' transform="translate({ax:.2f},{ay:.2f})"' if (ax or ay) else ''
        self.d = [f'<g data-block="all"{tr}>' + '\n'.join(out) + '</g>']

    def read_figures(self):
        """Las cifras del cálculo (solo se leen)."""
        self.r = {}
        for t in self.order:
            pc, dt_ = self.pre[t], self.det[t]
            self.r[t] = dict(Ib=pc['Ib'], P=dt_['p_kw'], In=pc['In'], icu=pc['icu'], S=pc['S'], PE=dt_['pe_mm2'], N=dt_['neutro_mm2'], dv=dt_['du_propia_pct'], lim=dt_['limite_pct'],
                             motor=dt_['topologia'] in TOPOLOGIAS_MOTOR, ph=dt_['fases'], fp=dt_['fp'], L=dt_['largo_m'], parent=bool(self.kids[t]), kind=dt_['kind'], disp=pc['disp'])

    # ---------- cadenas de símbolos ----------
    def chain(self, t):
        """Los símbolos del circuito, en el orden en que se dibujan: los elige el cálculo (solución estándar de epc_aea90364); aquí solo se les da lugar."""
        return [(it['symbol'], {**({'poles': it['label']} if it['label'] else {}), **it['slots']}) for it in self.det[t]['cadena']]

    def load_of(self, t):
        r = self.r[t]
        if r['motor']:
            return ('lv_motor_3ph', {'power_kw': f"{r['P']:.1f} kW", 'current': f"{r['Ib']:.1f} A", 'tag': t})
        return ('lv_load_box_kw', {'tag': t})

    # ---------- helpers SVG ----------
    def sym_file(self, sid):
        """Symbol SVG path. With the default library the file comes from `epc_symbols.resolve` (no engine builds a symbol file name, SYM-02); a library given by path keeps the file-name rule."""
        return self._registry_file(sid) if self.default_lib else _file_in(self.lib, sid)

    def _registry_file(self, sid):
        try:
            return str(resolve(sid, 'sld').svg)
        except UnknownSymbol:
            return os.path.join(self.lib, sid + '.svg')

    def fragment(self, sid, typed=False):
        """El símbolo como árbol listo para rellenar (el SVG se lee una vez por símbolo); `typed`: con la etiqueta del tipo de dispositivo (MCB, MCCB, KM...) que el símbolo lleva fuera de su grupo."""
        key = (sid, typed)
        if key not in self.cache:
            tree = etree.parse(self.sym_file(sid))
            el = tree.xpath(f"//*[@id='{sid}']")
            node = el[0] if el else tree.getroot()
            self.cache[key] = etree.tostring(node, encoding='unicode') + _symbol_texts(tree, typed)
        return etree.fromstring('<g xmlns="http://www.w3.org/2000/svg">' + self.cache[key] + '</g>')

    @staticmethod
    def tidy_slots(frag):
        for sl in frag.xpath(".//*[@id='label_slots']"):
            sl.attrib.pop('id', None); sl.set('fill', '#000000'); sl.set('data-layer', 'sld.text')      # los textos de un símbolo son anotación
            for t_ in sl.iter():
                t_.attrib.pop('font-weight', None)
        _SheetLabels.annotate(frag)
        for p in frag.xpath(".//*[@id='ports']") + frag.xpath(".//*[local-name()='metadata']"):
            if p.getparent() is not None: p.getparent().remove(p)
        frag.attrib.pop('id', None)

    @staticmethod
    def drop_bus_label(frag):
        """Quita el 'BUS' fijo de cada nodo de barra: se rotula solo en el extremo izquierdo."""
        for t_ in frag.xpath(".//*[local-name()='text']"):
            if ''.join(t_.itertext()).strip() == 'BUS' and t_.getparent() is not None:
                t_.getparent().remove(t_)

    @staticmethod
    def fill_slots(frag, slots):
        for el in frag.xpath(".//*[@data-key]"):
            val = slots.get(el.get('data-key'))
            if val is not None and str(val).strip() != '':
                el.text = str(val)
                for ch in list(el): el.remove(ch)
            elif el.getparent() is not None:
                el.getparent().remove(el)

    def sym_svg(self, sid, slots, x, y, mark=''):
        if not os.path.exists(self.sym_file(sid)):
            print('AVISO: falta símbolo', sid, '-> recuadro ??', file=sys.stderr)
            return (f'<g class="sym" data-layer="sld.diagram"{mark} transform="translate({x:.2f},{y:.2f})">'
                    '<rect x="-5" y="0" width="10" height="10" fill="none" stroke="#0000ff" stroke-width="0.25"/>'
                    '<text x="0" y="6.4" font-size="3.47" text-anchor="middle" font-family="Arial, sans-serif" fill="#000000">??</text></g>')
        frag = self.fragment(sid, bool(mark))                            # los dispositivos de la cadena de un circuito (los que llevan marca) muestran su tipo
        self.tidy_slots(frag)
        if sid == 'lv_busbar_node': self.drop_bus_label(frag)
        self.fill_slots(frag, slots)
        return f'<g class="sym" data-layer="sld.diagram" data-sid="{sid}"{mark} transform="translate({x:.2f},{y:.2f})">' + etree.tostring(frag, encoding='unicode') + '</g>'

    def place(self, sid, slots, x, y, tag='', idx=0):
        """Pone un símbolo; los de la cadena de un circuito llevan su circuito y su lugar en la cadena (data-tag, data-idx) para poder cambiarlos desde el dibujo."""
        mark = _mark(tag, idx)
        self.used.add(sid); self.d.append(self.sym_svg(sid, slots, x, y, mark))

    def bottom_off(self, sid):
        if sid not in self.cat: return 10.0 if not os.path.exists(self.sym_file(sid)) else 5.0
        p = [q for q in self.cat[sid].get('ports', []) if q['id'] == 'bottom']
        return p[0]['y'] if p else self.cat[sid]['size']['h']

    def line(self, x1, y1, x2, y2, col=BLUE, w=0.25, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.d.append(f'<line data-layer="{self.rol}" x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{col}" stroke-width="{w}"{d}/>')

    def T(self, x, y, s, size=FS_TXT, bold=False, anchor='start', col=BLACK):
        if self.txt_vis is not None: size = self.txt_vis
        b = ' font-weight="bold"' if bold else ''
        self.d.append(f'<text data-layer="sld.text" x="{x:.2f}" y="{y:.2f}" font-size="{size}" font-family="{xesc(FONT)}" text-anchor="{anchor}" fill="{col}"{b}>{xesc(str(s))}</text>')

    def draw_chain(self, elems, xc, y, tag=''):
        prev = None; yy = y
        for i, (sid, sl) in enumerate(elems):
            if prev is not None: self.line(xc, prev, xc, yy)
            self.place(sid, sl, xc, yy, tag, i)
            prev = yy + self.bottom_off(sid)
            yy = prev + GAP
        return prev

    def gw(self, t): return self.pitch if not self.kids[t] else sum(self.gw(k) for k in self.kids[t])

    def layout(self, t, x_left, y_top, top=False):
        w = self.gw(t); xc = x_left + w/2
        if top: self.place('lv_busbar_node', {}, xc, YBAR - 0.78)   # sin etiqueta por nodo: la barra se rotula una sola vez
        # datos de protección van en los slots del propio símbolo (sin bloque duplicado)
        bottom = self.draw_chain(self.chain(t), xc, y_top, t)
        if not self.kids[t]:
            self.leaves.append((t, xc, bottom))
            return
        yb = bottom + 6
        self.line(xc, bottom, xc, yb)
        xs = []; x = x_left
        for k in self.kids[t]:
            kw = self.gw(k); xk = x + kw/2; xs.append(xk)
            self.layout(k, x, yb + 4)
            self.line(xk, yb, xk, yb + 4)
            x += kw
        self.line(xs[0], yb, xs[-1], yb)

    # ---------- diagrama ----------
    def draw_header(self):
        tb = self.tb
        self.T(638, 28, tb['NOMBRE'], size=FS_TIT, bold=True, anchor='end')   # dentro del recuadro, esquina superior derecha: nombre del tablero
        self.T(638, 28 + 3.4*self.sp, f"Sistema {tb['SISTEMA']} · {self.v:.0f} V · {int(tb.get('FRECUENCIA_HZ') or 50)} Hz · FP {self.fpdef:g} · Icc {self.icc:g} kA", anchor='end')

    def draw_service(self):
        """La acometida (cable de entrada y Q-GRAL) y la barra principal."""
        self.xa = X0 + self.gw(self.roots[0]) / 2          # eje de la acometida = eje del primer circuito
        xa, line, T = self.xa, self.line, self.T
        self.place('lv_cable_arrow_in', {}, xa, 30)
        line(xa, 35, xa, 40, RED)
        self.place('lv_mccb_basic', {'tag': 'Q-GRAL'}, xa, 40)
        self.feeder_to_bus(xa, 0)
        bus_start = 40.0 if self.prev_h else self.bar_start(xa)   # hoja con barra que viene: la barra llega al borde izquierdo del recuadro + 5 mm
        line(bus_start, YBAR, self.bus_end, YBAR, BLUE, 0.7)
        if self.prev_h: T(bus_start, YBAR - 2, f"← VIENE DE HOJA {self.prev_h}", bold=True)
        if self.next_h: T(self.bus_end, YBAR + 4.6, f"CONTINÚA EN HOJA {self.next_h} →", anchor="end", bold=True)
        self.bdp = self.fig['bar']['in_a']
        T(xa + 4, YBAR - 2, 'BUS', bold=True)                  # extremo izquierdo, una sola vez
        T(self.bus_end, YBAR - 6, f"BARRA PRINCIPAL {self.bdp} A · {self.v:.0f} V · {self.tb['SISTEMA']}", anchor='end')  # extremo derecho, sobre la barra
        T(self.bus_end, YBAR - 2, f"Icc {self.icc:g} kA · 3F+N", anchor='end')

    def draw_extra_feeders(self):
        """Las demás acometidas del tablero: cada una con su cable de entrada, su Q-GRAL y su texto, sobre la misma barra."""
        sp = self.sp
        for k, f in enumerate(self.extra_feeders(), 1):
            x = self.extra_feeder_x(k)
            self.draw_feeder_head(x, f)
            tx = self.feeder_text_x(x, f)
            self.place('lv_mccb_basic', {'tag': f"Q-{f['name']}"[:14]}, x, 40)
            self.feeder_to_bus(x, k)
            self.T(tx, 31.5, f"{f['name']} / {f['length_m']:g} m", size=FS_DES, bold=True)
            self.T(tx, 31.5 + 4.2*sp, 'Seccion y proteccion: Pendiente' if f['pending'] else f"{f['S_mm2']} mm² · XLPE/Cu IRAM 2178")
            self.draw_transfer(x, f, tx)
            self.T(tx, 31.5 + 8.4*sp, ((f['source'] + ' · ') if f.get('source') else '') + ('' if f['pending'] or f['In'] is None else f"In {f['In']:g} A") + ('' if f['pending'] or f['du_pct'] is None else f" · ΔU {f['du_pct']:.2f} %")
                   + (' · en paralelo' if f.get('together') else ''))

    def draw_feeder_head(self, x, f):
        """Lo que está arriba de la acometida: la flecha del cable que ingresa o, si viene de un grupo electrógeno o de una UPS, su símbolo IEC 60617 (el círculo G 3~ o la caja UPS) en lugar de la flecha."""
        kind = backup_kind(f.get('source'))
        if kind == 'gen':
            self.place('lv_generator', {}, x, 17.5)                 # el círculo ocupa 20 a 30 mm
            self.line(x, 30, x, 40, RED)
        elif kind == 'ups':
            self.place('lv_ups', {}, x, 17.5)                       # la caja y sus patas llegan justo al Q-GRAL (40 mm)
        else:
            self.place('lv_cable_arrow_in', {}, x, 30)
            self.line(x, 35, x, 40, RED)

    def draw_transfer(self, x, f, tx=None):
        """Lo que une una acometida de respaldo con la de la red: el enclavamiento del interruptor de transferencia (grupo electrógeno) o el by-pass de la UPS."""
        kind = backup_kind(f.get('source'))
        if kind == 'gen' and x == self.extra_feeder_x(self.transfer_index()):
            self.draw_transfer_switch(x)
        elif kind == 'ups':
            self.T(tx, 31.5 + 9.0*self.sp, 'UPS · BY-PASS MANUAL', bold=True)

    def draw_transfer_switch(self, x):
        """El interruptor de transferencia (ATS, IEC 60617): dos entradas (la acometida de la red y la del grupo electrógeno), enclavadas entre sí, y una salida única hacia las barras."""
        mid, top, box_y, box_h, half = (self.xa + x) / 2, 75.0, 79.0, 4.6, 8.0
        join = box_y + box_h / 2
        for xi, edge in ((self.xa, mid - half), (x, mid + half)):
            self.line(xi, top, xi, join)                                  # la entrada baja del Q-GRAL hasta el nivel del interruptor...
            self.line(xi, join, edge, join)                               # ...y entra por su lado
        self.d.append(f'<g class="sym" data-layer="{self.rol}" data-sid="lv_ats_box"><rect x="{mid - half:.2f}" y="{box_y:.2f}" width="{2 * half:.2f}" height="{box_h:.2f}" fill="#ffffff" stroke="{BLUE}" stroke-width="0.25"/></g>')
        self.T(mid, box_y + box_h - 1.3, 'ATS', anchor='middle', bold=True, col=BLUE)
        self.line(mid, box_y + box_h, mid, YBAR)                          # la salida única a las barras
        self.T(mid, box_y - 1.6, 'ENCLAVAMIENTO RED / GRUPO', anchor='middle', bold=True)

    def first_feeder_name(self):
        """«ACOMETIDA», o el nombre de la primera cuando el tablero tiene varias."""
        many = self.fig.get('feeders') or []
        return many[0]['name'] if len(many) > 1 and many[0]['name'] else 'ACOMETIDA'

    def draw_feeder_text(self):
        """El texto de la acometida, junto al cable de entrada (horizontal, sobre el Q-GRAL): el cable y su protección vienen del tablero superior."""
        ac, xa, sp, v = self.fig['feeder'], self.xa, self.sp, self.v
        self.T(xa + 6, 31.5, f"{self.first_feeder_name()} / {ac['length_m']:g} m", size=FS_DES, bold=True)
        self.T(xa + 6, 31.5 + 4.2*sp, 'Seccion y proteccion: Pendiente (tablero superior)' if ac['pending'] else f"{ac['S_mm2']} mm² · XLPE/Cu IRAM 2178")
        self.T(xa + 6, 31.5 + 8.4*sp, f"Barra {v:.0f} V · In {self.bdp} A · Icc {self.icc:g} kA" + ('' if ac['pending'] or ac['du_pct'] is None else f" · ΔU {ac['du_pct']:.2f} %"))

    def draw_boards(self):
        x = X0
        for t in self.roots:
            start = len(self.d)
            self.layout(t, x, YBAR + 4.22, top=True); x += self.gw(t)
            self.mark(start, t)

    def leg_strings(self, t):
        r = self.r[t]
        return [(f"{t} / {r['L']:g} m", FS_DES, 0.66), (_leg_text(r, self.c[t]['tipo']) + _phase_note(r, self.c[t]), FS_TXT, 0.58), ("XLPE/Cu  IRAM 2178", FS_TXT, 0.58)]

    def draw_outputs(self):
        """Los cables de salida y las cargas, bajo la última rama."""
        leaves, line = self.leaves, self.line
        # longitud estimada (mm) de la leyenda mas larga: ancho medio Arial ~0,58 em (negrita ~0,66 em)
        leg_max = max(len(txt) * fs * k for t, _, _ in leaves for txt, fs, k in self.leg_strings(t))
        low = max(a for _, _, a in leaves)
        # barra PE a 3 mm de la base de los simbolos; texto de leyenda a GAP_PE mm por encima de la barra
        self.y_out = max(low + 3 + GAP_PE + 2 + 8 + leg_max, low + CABLE_H + 8 + 3)  # ta = y_out-8, la flecha del símbolo queda en ta
        self.leg_tops = []
        for t, xc, ab in leaves:
            start = len(self.d)
            ta = self.y_out - 8                       # flecha de salida (lv_cable_run) a 8 mm de la carga
            r = self.r[t]
            l2 = self.leg_strings(t)[1][0]
            o = ta - CABLE_H                          # origen del símbolo lv_cable_run (extremo superior del tramo)
            assert o >= ab - 1e-6, f'cable {t}: tramo superior demasiado corto ({o - ab:.1f} mm)'
            line(xc, ab, xc, o, RED)
            self.place('lv_cable_run', {'cable_tag': f"{t} / {r['L']:g} m", 'cable_spec': l2, 'cable_insulation': 'XLPE/Cu IRAM 2178'}, xc, o, t, 'cable')
            self.leg_tops.append(ta - 2 - max(len(f"{t} / {r['L']:g} m"), len(l2), len('XLPE/Cu IRAM 2178')) * 2.3)
            lsid, lsl = self.load_of(t)
            self.place(lsid, lsl, xc, self.y_out)
            self.mark(start, self.root_of[t])

    def draw_earth_bar(self):
        y_pe = max(ab for _, _, ab in self.leaves) + 3; x_pe0 = 46   # debajo de todos los simbolos de ramas, encima de leyendas
        print('PE y', round(y_pe,1), 'leyendas desde', round(min(self.leg_tops),1), file=sys.stderr)                     # barra PE encima de las leyendas de cable (como en la referencia)
        x_cab1 = min(xc + self.dx(t) for t, xc, _ in self.leaves)          # primer cable de salida
        self.line(x_pe0, y_pe, self.bus_end, y_pe, GREEN, 0.25, '10 1 2 1')
        self.place('lv_earth_pe', {'tag': 'PE'}, x_pe0, y_pe)
        self.T(x_cab1 - 5, y_pe - 1.5, 'BARRA PE', anchor='end', col=GREEN)   # 5 mm antes de la linea roja

    def draw_box(self):
        """Recuadro gris de linea entrecortada fina: engloba el tablero; las cargas quedan fuera (en campo)."""
        self.box_y1 = self.y_out - 2.0
        self.d.append(f'<rect data-layer="sld.diagram" x="{BOX_X0:.2f}" y="{BOX_Y0:.2f}" width="{BOX_X1-BOX_X0:.2f}" height="{self.box_y1-BOX_Y0:.2f}" fill="none" stroke="#808080" stroke-width="0.25" stroke-dasharray="4 2"/>')

    def walk(self, t):
        self.tree.append(t)
        for k in self.kids[t]: self.walk(k)

    # ---------- tabla de circuitos (bajo el diagrama) ----------
    def row_values(self, t):
        c, r = self.c[t], self.r[t]
        return [t, c['desc'][:55], f"{r['P']:.2f}", c['fase'], f"{r['Ib']:.1f}", f"{r['In']}", f"{r['icu']}",
                r['disp'][:85], ('—' if r['parent'] else f"{r['S']}"), f"{r['PE']:g}",
                ('—' if r['parent'] else f"{r['L']:g}"), ('—' if r['parent'] else f"{r['dv']:.2f}")]

    def draw_table(self):
        self.k_tab = len(self.d)   # A3: marca de inicio de la tabla
        self.rol = 'sld.text'      # desde aquí, tabla de circuitos y columna de referencias: anotación
        line, T = self.line, self.T
        tot = sum(w for _, w in TABLE_COLS); cw = [w*TW/tot for _, w in TABLE_COLS]
        self.ty = ty = 575.0 - HH - len(self.tree)*RH
        line(TX, ty, TX + TW, ty, BLACK, 0.25)
        xx = TX
        for (h, _), w in zip(TABLE_COLS, cw):
            T(xx + 1, ty + 5.4, h, bold=True); xx += w
        line(TX, ty + HH, TX + TW, ty + HH, BLACK, 0.25)
        ry = ty + HH
        for t in self.tree:
            xx = TX
            for v, w in zip(self.row_values(t), cw):
                T(xx + 1, ry + 4.2, v); xx += w
            ry += RH
            line(TX, ry, TX + TW, ry, BLACK, 0.25)
        xx = TX
        for w in cw:
            line(xx, ty, xx, ry, BLACK, 0.25); xx += w
        line(TX + TW, ty, TX + TW, ry, BLACK, 0.25)
        self.ry = ry
        if self.sin_tabla: del self.d[self.k_tab:]   # la tabla no va en las hojas del diagrama
        self.k_ref = len(self.d)   # A3: marca de inicio de la columna de referencias

    # ---------- columna derecha (referencias, cálculos, verificación) ----------
    def reference_layout(self):
        """Dónde y con qué tamaños van las tres columnas: A3 las pone una al lado de la otra junto al rótulo; A1 en la columna derecha."""
        if self.a3:
            yfin_tab = 20.0 + (self.box_y1 - 20.0) * self.s_diag + (18.0 if self.sin_tabla else 18.0 + (HH + len(self.tree) * RH) * self.s_diag)
            return dict(RX=30.0, XC=122.0, XV=178.0, Y0=yfin_tab + 3.0, TIT=FS_TXT, LSR=3.6, WRAP=30, WRAPC=36, LSC=3.0)
        self.line(648, 15, 648, 500, BLACK, 0.25)
        return dict(RX=655.0, XC=655.0, XV=655.0, Y0=22.0, TIT=FS_TIT, LSR=5.5, WRAP=80, WRAPC=80, LSC=LS)

    def below(self, g, y):
        """Dónde empieza la columna que sigue: A3 las pone una al lado de la otra (misma altura); A1, una debajo de la otra (si no, se montan)."""
        return g['Y0'] if self.a3 else y + 5

    def draw_references(self, g):
        """Las referencias (símbolos y trazos); devuelve dónde terminan."""
        T, line, y = self.T, self.line, g['Y0']
        T(g['RX'], y, 'REFERENCIAS', size=g['TIT'], bold=True); y += 6
        for sid in sorted(self.used):
            legend = self.cat.get(sid, {}).get('legend')           # the legend text of a symbol lives in the symbol catalog (DGM-13a)
            if not legend: continue
            sg, ds = legend['abbr'], legend['es']
            T(g['RX'], y, sg, bold=True); T(g['RX'] + 18, y, ds); y += g['LSR']
        line(g['RX'], y, g['RX'] + 14, y, BLACK, 0.7); T(g['RX'] + 18, y + 1, 'Barra de potencia BDP (trazo 0,7)'); y += g['LSR']
        line(g['RX'], y, g['RX'] + 14, y, GREEN, 0.25, '10 1 2 1'); T(g['RX'] + 18, y + 1, 'Barra PE / proteccion (verde)')
        return y + g['LSR']

    def draw_calculations(self, g, y):
        """Los cálculos referenciales desde `y`; devuelve dónde terminan."""
        self.T(g['XC'], y, 'CALCULOS (referencial)', size=g['TIT'], bold=True); y += 6
        for ln in self.fig['lines']:
            for w_ in textwrap.wrap(ln, g['WRAPC'] if self.a3 else 80):
                self.T(g['XC'], y, w_); y += g['LSC']
        return y

    def draw_verification(self, g, y):
        """Las verificaciones del tablero con su estado, desde `y`; devuelve dónde terminan."""
        T, wrap, lsc = self.T, g['WRAP'], g['LSC']
        T(g['XV'], y, 'VERIFICACION', size=g['TIT'], bold=True); y += 6
        for c in self.fig['checks']:
            txt, ok = c['text'], c['ok']
            st = 'PENDIENTE' if ok is None else 'OK' if ok else 'REVISAR'
            wr = textwrap.wrap(txt, wrap)
            for i, w_ in enumerate(wr):
                T(g['XV'], y, w_ + (f'  [{st}]' if i == len(wr) - 1 else '')); y += lsc
            y += 0.5
        if self.fig['differential_missing']:
            for w_ in textwrap.wrap('Sin diferencial: ' + ', '.join(self.fig['differential_missing']), wrap):
                T(g['XV'], y, w_, col='#b00000'); y += lsc
        return y + 1.5

    def draw_notes(self, g, y):
        T, lsc = self.T, g['LSC']
        if self.a3:
            for ln in textwrap.wrap('Calculo referencial; no reemplaza la memoria de calculo.', g['WRAP']):
                T(g['XV'], y, ln); y += lsc
            return
        notes = self.fig['note']   # A1: notas al pie de la columna derecha, como antes
        ny = max(y + 4, 500 - LS*len(textwrap.wrap(notes, 115)) - 2)
        T(g['XV'], ny - 3, 'NOTAS', size=g['TIT'], bold=True)
        for i, ln in enumerate(textwrap.wrap(notes, 115)):
            T(g['XV'], ny + i*LS, ln)

    def draw_side_columns(self):
        g = self.reference_layout()
        self.txt_vis = None   # de aquí en adelante, el texto usa su tamaño (referencias en A3 ya van a 2 mm)
        y_ref = self.draw_references(g)
        y_calc = self.draw_calculations(g, self.below(g, y_ref))
        self.draw_notes(g, self.draw_verification(g, self.below(g, y_calc)))
        if self.solo_tabla: self.d = self.d[self.k_tab:self.k_ref]   # hoja solo de tabla: la tabla de circuitos sale en su propia lámina

    # ---------- rótulo + modificaciones + export ----------
    def title_block(self):
        """El rótulo de la hoja y su bloque de modificaciones: se piden al servicio de epc_titleblock, o se leen de las láminas dadas."""
        if self.lamina != 'default':
            return open(self.lamina, encoding='utf-8').read(), open(self.modblock, encoding='utf-8').read()
        from epc_draw.titleblock import service as TBS     # los datos del proyecto vienen en EPC_TITLEBLOCK_JSON; sin Excel ni subprocesos
        env, name = self.env, self.name
        pedido = json.load(open(env['EPC_TITLEBLOCK_JSON'], encoding='utf-8')) if env.get('EPC_TITLEBLOCK_JSON') else {}
        nombres = env.get('SLD_NAMES', name).split(',')
        campos = {'denominacion': self.tb.get('NOMBRE_BASE'), 'denominacion_2': 'TABLA DE CÁLCULO DE CIRCUITOS' if name.endswith('_TABLA') else 'DIAGRAMA UNIFILAR BT',
                  'proyecto': self.tb.get('PROYECTO'), 'pagina': f'{nombres.index(name) + 1} / {len(nombres)}'}
        res = TBS.render({**pedido, 'sheets': [{'name': name, 'format': self.formato, 'fields': campos}]})
        for w in res['warnings']: print('AVISO', w, file=sys.stderr)
        return res['sheets'][0]['svg'], res['sheets'][0]['modifications_block']

    def issue_date(self):
        """La fecha de emisión del rótulo (dd/mm/aaaa): la fecha del plano si se dio (`EPC_STAMP_DATE`), la de hoy si no."""
        from epc_draw.core import stamp
        return stamp.issue_day(self.stamp_date)

    def fill_title(self, lam, mod):
        """Rellena los campos del rótulo; lo que el SLD no calcula (empresa, cliente, códigos...) queda en blanco, no quedan {clave} visibles."""
        lam = ROLES.tag_iram_sheet(lam)   # marco y rótulo de la plantilla IRAM, con su rol de capa
        vals = {'cliente': 'No indicado', 'denominacion': self.tb['NOMBRE'], 'denominacion_2': 'DIAGRAMA UNIFILAR BT',
                'empresa': '—', 'plano_n': str(self.tb.get('PROYECTO') or ''), 'plano_propio': self.name,
                'escala': 'S/E', 'emision': self.issue_date(), 'reemplaza': '—', 'notas': 'Referencial: ver columnas de calculo'}
        pend = set(re.findall(r'\{([a-z_0-9]+)\}', lam)) | set(re.findall(r'\{([a-z_0-9]+)\}', mod))
        vacios = sorted(k for k in pend if k not in vals)
        for k in vacios: vals[k] = ''
        if vacios: print('AVISO rótulo sin datos del proyecto (quedan en blanco):', ', '.join(vacios), file=sys.stderr)
        for k, v in vals.items():
            lam = lam.replace('{' + k + '}', xesc(v))
        inner = mod[mod.find('>', mod.find('<svg')) + 1: mod.rfind('</svg>')]
        for k, v in vals.items():
            inner = inner.replace('{' + k + '}', xesc(v))
        return lam, inner

    def body_a3(self):
        """A3: el recuadro del diagrama ocupa todo el ancho de la zona útil con 5 mm a izquierda, derecha y arriba."""
        s = (400.0 - 35.0) / (BOX_X1 - BOX_X0)                         # recuadro 35..643 (608 mm A1) -> 35..400 mm A3
        yt = 20.0 + (self.box_y1 - 20.0) * s + 18.0                    # tabla de circuitos bajo el diagrama (debajo de las etiquetas de carga)
        d, kt, kr = self.d, self.k_tab, self.k_ref
        print(f'A3: escala diagrama {s:.3f}, referencias {1.0:.3f}', file=sys.stderr)
        return '\n'.join(_bind(page, tx, ty, k) for page, k, tx, ty in [
            (d[:kt], s, 35.0 - 35.0*s, 20.0 - 20.0*s),
            (d[kt:kr], s, 35.0 - 30.0*s, yt - self.ty*s),
            (d[kr:], 1.0, 0.0, 0.0)])

    def body(self):
        if self.solo_tabla:     # hoja de tabla: la tabla ocupa el ancho de la zona útil, arriba a la izquierda (5 mm de margen)
            st = min(1.0, (400.0 - 30.0) / 610.0) if self.a3 else 1.0
            return f'<g transform="translate({30.0 - 30.0*st:.2f},{20.0 - self.ty*st:.2f}) scale({st:.4f})">' + '\n'.join(self.d) + '</g>'
        if self.a3: return self.body_a3()
        return '\n'.join(self.d)

    @staticmethod
    def insert(lam, body):
        m = re.search(r'<g id="dibujo">.*?</g>', lam, re.S)
        if m and '<!-- insertar' in m.group(0):
            return lam[:m.start()] + '<g id="dibujo">' + body + '</g>' + lam[m.end():]
        print('AVISO: no se encontró la casilla dibujo en la lámina; el diagrama va en un grupo aparte', file=sys.stderr)
        idx = lam.rfind('</svg>')
        return lam[:idx] + '<g id="diagrama_SLD">' + body + '</g>\n' + lam[idx:]

    def assemble(self):
        lam, mod = self.title_block()
        lam, inner = self.fill_title(lam, mod)
        if MOD_LISTA and 'id="modificaciones_IRAM4508"' not in lam:   # el SVG del plugin ya trae la lista si la fila lo indica
            self.d.append(f'<g transform="translate(652,507.5)">{inner}</g>')
        final = self.insert(lam, self.body())
        left = re.findall(r'>\{[a-z_0-9]+\}<', final)
        if left: print('AVISO placeholders sin reemplazar:', left[:5])
        etree.fromstring(final.encode('utf-8'))
        return final

    def accumulated_drop(self, tag):
        """Voltage drop (%) from the source to the circuit, as the calculation reports it (its own plus the upstream ones); the own drop when the calculation gives none."""
        acc = self.det[tag].get('du_acum_pct')
        return acc if isinstance(acc, (int, float)) else self.r[tag]['dv']

    def files(self, final):
        """The sheet as data: ({file name: bytes}, notes). The SVG, its DXF through epc_dxf (layers of the catalog, symbols as blocks, colour and stroke weight) and the calculation summary; nothing is written."""
        from epc_draw.core import deliverable as DL
        made = DL.convert_bytes(final, symbol_library=self.lib, a3=self.a3, stamp_date=self.stamp_date, seed=self.name)
        summ = {t: dict(In=self.r[t]['In'], Ib=round(self.r[t]['Ib'], 1), icu=self.r[t]['icu'], S=self.r[t]['S'], dU=round(self.r[t]['dv'], 2), disp=self.r[t]['disp']) for t in self.tree}
        files = {self.name + '.svg': final.encode('utf-8'), self.name + '.dxf': made['dxf'],
                 self.name + '_calculo.json': json.dumps(summ, ensure_ascii=False, indent=1).encode('utf-8')}
        return files, made['messages']

    def report(self):
        dvmax = max((self.accumulated_drop(t) for t in self.order), default=0.0)     # the calculation's du_pct is the drop up to the circuit: own + the upstream ones
        print('OK', self.name, 'circuitos', len(self.tree), 'y_out', round(self.y_out, 1), 'fin tabla', round(self.ry, 1), 'dU max', round(dvmax, 2))

    def export(self, final):
        """Writes the sheet in the folder `out`: the writer of this engine; `files` makes the bytes."""
        files, notes = self.files(final)
        os.makedirs(self.out, exist_ok=True)
        for fname, data in files.items():
            try:
                with open(os.path.join(self.out, fname), 'wb') as f:
                    f.write(data)
            except PermissionError:
                if not fname.endswith('.dxf'):
                    raise
                notes = [f'AVISO no se pudo escribir {fname}: está abierto en otro programa (cerrarlo y volver a generar)']
        for ln in notes:
            print(ln, file=sys.stderr)
        self.report()
        return {"name": self.name, "svg": os.path.join(self.out, self.name + '.svg'), "circuits": len(self.tree)}

    def build(self):
        return self.export(self.drawn())

    def build_files(self):
        """The sheet as data: ({file name: bytes}, notes); nothing is written."""
        files = self.files(self.drawn())
        self.report()
        return files

    def drawn(self):
        self.read_board()
        self.draw_header(); self.draw_service(); self.draw_extra_feeders(); self.draw_feeder_text(); self.draw_boards()
        self.draw_outputs(); self.draw_earth_bar(); self.draw_box(); self.apply_layout()
        self.tree = []
        for t in self.roots: self.walk(t)
        self.draw_table()
        self.draw_side_columns()
        return self.assemble()


def _environment(environ, stamp_date):
    env = dict(os.environ if environ is None else environ)
    if stamp_date:
        env['EPC_STAMP_DATE'] = str(stamp_date)
    return env


def generate_files(lib, xlsx, name, lamina='default', modblock='default', environ=None, stamp_date=None):
    """`generate` with the sheet as data: ({file name: bytes}, notes). The caller writes the bytes where it wants (ADR-0042)."""
    return _Sheet(lib, xlsx, None, name, lamina, modblock, _environment(environ, stamp_date)).build_files()


def generate(lib, xlsx, out, name, lamina='default', modblock='default', environ=None, stamp_date=None) -> dict:
    """Draws one sheet of the single-line diagram of a board (SVG, and the DXF through epc_dxf). It only draws: the calculation comes in files named by the environment
    (SLD_CALC_JSON, SLD_CALC_DETAIL, SLD_FIGURES_JSON, EPC_TITLEBLOCK_JSON) and so do the options of the sheet (SLD_SUBSET, SLD_NAMES, SLD_PREV, SLD_NEXT, SLD_TITLE_SUFFIX, SLD_FORMATO A1|A3,
    SLD_SIN_TABLA, SLD_SOLO_TABLA); `environ` is where they are read from (the process environment by default). `stamp_date` (or EPC_STAMP_DATE: an ISO date) is optional: it is the date of the drawing (title block issue date, DXF creation and update times
    and GUIDs derived from it), so the same inputs give the same files; without it the clock and random GUIDs are used. Nothing runs when the module is imported."""
    return _Sheet(lib, xlsx, out, name, lamina, modblock, _environment(environ, stamp_date)).build()


def main(argv=None, environ=None) -> int:
    """python -m epc_draw.sld.sld_generator LIB XLSX OUT NAME LAMINA MODBLOCK (what sld_paginate runs for each sheet)."""
    args = sys.argv[1:] if argv is None else argv
    generate(*args[:6], environ=environ)
    return 0


if __name__ == '__main__':
    sys.exit(main())
