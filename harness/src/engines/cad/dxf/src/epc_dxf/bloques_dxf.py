"""Símbolos SLD como bloques DXF (INSERT) tomados de iec60617-symbol-generator.

Flujo (sld_generator.py):
  1. separar(svg_final, lib): quita del SVG los símbolos que tienen bloque DXF y devuelve
     su posición absoluta (mm, coordenadas SVG = mm) y sus valores de atributos.
  2. el SVG sin esos símbolos pasa por el convertidor del plugin y capas_dxf.
  3. insertar(dxf, lib, instancias, alto_mm): importa cada bloque (una sola definición),
     y coloca un INSERT por aparición con su escala (A3 = escala del grupo) y sus atributos.
Las capas de los bloques se reasignan a las capas 291-* del SLD.
"""
import io
import json
import os, re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from lxml import etree
import ezdxf
from ezdxf.addons import importer
from epc_dxf import layers as _L
from epc_dxf import stamp as _stamp



def _comp(a, b):
    """Compone transformaciones afines simples (k, tx, ty): p -> k*p + t.  a∘b."""
    return (a[0] * b[0], a[0] * b[1] + a[1], a[0] * b[2] + a[2])


def _af(t):
    res = (1.0, 0.0, 0.0)
    for nombre, args in re.findall(r'(translate|scale)\(([^)]*)\)', t or ''):
        v = [float(x) for x in re.split(r'[\s,]+', args.strip()) if x]
        op = (1.0, v[0], v[1] if len(v) > 1 else 0.0) if nombre == 'translate' else (v[0], 0.0, 0.0)
        res = _comp(res, op)
    return res


def _absoluta(el):
    cadena = []
    n = el
    while n is not None:
        cadena.append(n.get('transform'))
        n = n.getparent()
    res = (1.0, 0.0, 0.0)
    for t in reversed(cadena):
        res = _comp(res, _af(t))
    return res


@dataclass(frozen=True)
class SymbolLibrary:
    """The DXF blocks of a symbol library as data (ADR-0042): the engine reads no folder, the caller hands this in.
    `catalog` is {symbol id: DXF file name}; `files` is {file name: DXF text}, decoded as ezdxf does when it reads a file."""
    catalog: Mapping[str, str]
    files: Mapping[str, str]

    def file_of(self, sid):
        """The file of a symbol id (SYM-00): the file the library's catalog names for it, or `<id>.dxf`; None when the library has none."""
        if not sid:
            return None
        return next((n for n in (self.catalog.get(sid), sid + '.dxf') if n and n in self.files), None)


def _dxf_text(path: Path) -> str:
    """The text of an ASCII DXF file, read with the encoding its header names and the error handling `ezdxf.readfile` uses."""
    from ezdxf.filemanagement import dxf_file_info
    with open(path, 'rt', encoding=dxf_file_info(str(path)).encoding, errors='surrogateescape') as f:
        return f.read()


def load_library(folder) -> SymbolLibrary:
    """Reads a symbol folder once into data: its `_catalog.json` (id -> DXF name; its `file` field names the SVG, the DXF has the same stem) and every `.dxf` in it. This is the caller's side of the door."""
    folder = Path(folder)
    ruta = folder / '_catalog.json'
    catalog = {}
    if ruta.is_file():
        with open(ruta, encoding='utf-8-sig') as f:
            catalog = {i['id']: os.path.splitext(i['file'])[0] + '.dxf' for i in json.load(f).get('symbols', []) if i.get('id') and i.get('file')}
    return SymbolLibrary(catalog, {p.name: _dxf_text(p) for p in sorted(folder.glob('*.dxf'))})


def as_library(lib) -> SymbolLibrary:
    """A `SymbolLibrary`, or the folder that holds one (read once)."""
    return lib if isinstance(lib, SymbolLibrary) else load_library(lib)


def _bloque_disponible(lib, sid):
    return lib.file_of(sid) is not None


def separar(svg_texto, lib):
    """Devuelve (svg_sin_simbolos, instancias). Instancia: sid, X, Y (mm SVG), k, valores."""
    lib = as_library(lib)
    raiz = etree.fromstring(svg_texto.encode('utf-8'))
    instancias = []
    for g in raiz.xpath("//*[@class='sym' and @data-sid]"):
        sid = g.get('data-sid')
        if not _bloque_disponible(lib, sid):
            continue
        kx, tx, ty = _absoluta(g)
        valores = {}
        for el in g.xpath(".//*[@data-key]"):
            t = ''.join(el.itertext()).strip()
            if t:
                valores[el.get('data-key').upper()] = t
        instancias.append(dict(sid=sid, X=tx, Y=ty, k=kx, valores=valores))
        g.getparent().remove(g)
    return etree.tostring(raiz, encoding='unicode'), instancias


def _importar(doc, lib, sid):
    """Imports the library block of a symbol id into the document (once) and returns the block name, the one the library file gives it."""
    src = ezdxf.read(io.StringIO(lib.files[lib.file_of(sid)]))
    propios = [b.name for b in src.blocks if not b.name.startswith('*')]
    nombre = sid.upper() if sid.upper() in propios else (propios[0] if propios else sid.upper())
    imp = importer.Importer(src, doc)
    if nombre not in doc.blocks:
        imp.import_block(nombre)
    imp.finalize()
    return nombre


def insertar(dxf_path, lib, instancias, alto_mm, catalog=None, stamp=None, doc=None, write=True):
    cat = _L.resolve(catalog)
    lib = as_library(lib)
    doc = _stamp.document(dxf_path, doc)
    msp = doc.modelspace()
    sids = sorted({i['sid'] for i in instancias})
    bloque_de = {sid: _importar(doc, lib, sid) for sid in sids}
    nombres = list(bloque_de.values())
    # capas de los bloques -> capas del SLD (colores, alturas y estilos de texto: los del plugin, sin cambios)
    for nombre in nombres:
        for e in doc.blocks.get(nombre):
            e.dxf.layer = {'SIMBOLO': _L.name('sld.diagram', cat), 'ROTULO': _L.name('sld.text', cat), '0': _L.name('sld.diagram', cat)}.get(e.dxf.layer, _L.name('sld.diagram', cat))
    for capa in ('SIMBOLO', 'ROTULO'):
        if capa in doc.layers:
            try:
                doc.layers.remove(capa)
            except ezdxf.DXFValueError:      # a protected layer, or one still in use: it stays (COD-11: only this error is expected)
                pass
    for i in instancias:
        k = i['k']
        ref = msp.add_blockref(bloque_de[i['sid']], (i['X'], alto_mm - i['Y']),
                               dxfattribs={'layer': _L.name('sld.diagram', cat), 'xscale': k, 'yscale': k, 'zscale': k})
        tags = [a.dxf.tag for a in doc.blocks.get(bloque_de[i['sid']]).query('ATTDEF')]
        ref.add_auto_attribs({t: i['valores'].get(t, '') for t in tags})
        for a in ref.attribs:
            a.dxf.layer = _L.name('sld.text', cat)
    _stamp.save_if(doc, dxf_path, stamp, write)
    return len(instancias), len(sids)
