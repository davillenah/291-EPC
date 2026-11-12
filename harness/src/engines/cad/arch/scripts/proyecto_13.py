"""Proyecto 13 de autoría propia, hecho para probar el motor `epc_arch`: hospital de baja complejidad de tres niveles en planta de L (36 × 24 m).

  PB   guardia (admisión, espera, dos consultorios, shock room, observación), imágenes (radiología, tomógrafo), laboratorio, farmacia, hall de acceso,
       núcleo con escalera y ascensores, ala de servicios con tres SS.HH.                      (19 locales, 1 pasillo principal y 1 de ala)
  N1   internación: ocho habitaciones, enfermería, sala de médicos, estar de familiares y de pacientes, baño asistido
  N2   quirófanos y terapia intensiva: tres quirófanos, terapia intensiva de 12 × 7 m, esterilización, lavado quirúrgico, vestuarios, recuperación

Cada nivel se dibuja con muros de 30 cm (exteriores y núcleo), 15 cm (compartidos) y 12 cm (entre húmedos), puertas con su arco de giro (0,80 a 1,40 m), ventanas
con tres trazos, escalera con huellas, ascensor con su cruz, ejes con burbujas, cotas encadenadas y un rótulo `PB-07 · 8,75 m²` por local. Se escribe un DXF en metros y un
PNG de cada nivel, se pasan por el motor y se compara lo que reconoce con lo dibujado (que es la verdad: sale del mismo modelo).

Uso: python scripts/proyecto_13.py [--sin-exportar]       Salida: out/proyectos/13/ (ignorada por git): DXF, PNG, verdad.json, informe.json, informe.md
"""
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import ezdxf
from ezdxf.enums import TextEntityAlignment
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
SALIDA = RAIZ / "out" / "proyectos" / "13"
W, H = 3600, 2400                                              # cm
PX_POR_CM = 0.6
MARGEN = 650                                                   # cm alrededor del edificio en el PNG (ejes, cotas y rótulo)
N_ = {"n": (0, 1), "s": (0, -1), "w": (1, 0), "e": (-1, 0)}    # hacia dentro del local, con y hacia abajo

# ---- locales, puertas y ventanas de los tres niveles (cm; y hacia abajo; `N` núcleo, `H` húmedo) ------------------------------------------------------------
FILA1 = [0, 600, 1200, 1800, 2400, 3000, 3600]
BASE_PASILLOS = [("PASILLO PRINCIPAL", (0, 700, 3600, 900), ""), ("PASILLO DE ALA", (900, 1600, 2000, 1800), "")]
NUCLEO = [("ESCALERA", (2600, 900, 2900, 1600), "N"), ("ASCENSORES", (2900, 900, 3200, 1600), "N")]
PUERTAS_NUCLEO = [("ESCALERA", "n", 2750, 90, "in"), ("ASCENSORES", "n", 3050, 90, "out")]


def pb():
    locales = [("ADMISIÓN", (0, 0, 600, 700), ""), ("SALA DE ESPERA", (600, 0, 1400, 700), ""), ("CONSULTORIO 1", (1400, 0, 1900, 700), ""),
               ("CONSULTORIO 2", (1900, 0, 2400, 700), ""), ("SHOCK ROOM", (2400, 0, 3000, 700), ""), ("OBSERVACIÓN", (3000, 0, 3600, 700), ""),
               ("HALL DE ACCESO", (0, 900, 900, 2400), ""), ("RADIOLOGÍA", (900, 900, 1500, 1600), ""), ("TOMÓGRAFO", (1500, 900, 2100, 1600), ""),
               ("LABORATORIO", (2100, 900, 2600, 1600), ""), ("FARMACIA", (3200, 900, 3600, 1600), ""),
               ("SS.HH. HOMBRES", (900, 1800, 1300, 2400), "H"), ("SS.HH. MUJERES", (1300, 1800, 1700, 2400), "H"), ("SS.HH. ACCESIBLE", (1700, 1800, 2000, 2400), "H")]
    puertas = [("ADMISIÓN", "s", 300, 100, "in"), ("SALA DE ESPERA", "s", 1000, 120, "in"), ("CONSULTORIO 1", "s", 1650, 90, "in"), ("CONSULTORIO 2", "s", 2150, 90, "in"),
               ("SHOCK ROOM", "s", 2700, 120, "in"), ("OBSERVACIÓN", "s", 3300, 90, "in"), ("HALL DE ACCESO", "n", 450, 120, "in"), ("HALL DE ACCESO", "w", 1500, 140, "out"),
               ("RADIOLOGÍA", "n", 1200, 100, "in"), ("TOMÓGRAFO", "n", 1800, 100, "in"), ("LABORATORIO", "n", 2350, 90, "in"), ("FARMACIA", "n", 3400, 100, "in"),
               ("PASILLO DE ALA", "w", 1700, 120, "in"), ("SS.HH. HOMBRES", "n", 1100, 80, "in"), ("SS.HH. MUJERES", "n", 1500, 80, "in"), ("SS.HH. ACCESIBLE", "n", 1850, 95, "in")]
    ventanas = [("ADMISIÓN", "n", 300, 150), ("SALA DE ESPERA", "n", 1000, 250), ("CONSULTORIO 1", "n", 1650, 150), ("CONSULTORIO 2", "n", 2150, 150), ("SHOCK ROOM", "n", 2700, 150),
                ("OBSERVACIÓN", "n", 3300, 150), ("OBSERVACIÓN", "e", 350, 150), ("FARMACIA", "e", 1250, 150), ("FARMACIA", "s", 3400, 100), ("LABORATORIO", "s", 2350, 200),
                ("HALL DE ACCESO", "w", 2100, 250), ("HALL DE ACCESO", "s", 450, 250), ("SS.HH. HOMBRES", "s", 1100, 60), ("SS.HH. MUJERES", "s", 1500, 60), ("SS.HH. ACCESIBLE", "s", 1850, 60)]
    return {"id": "pb", "nombre": "PLANTA BAJA", "codigo": "PB", "locales": locales + BASE_PASILLOS + NUCLEO, "puertas": puertas + PUERTAS_NUCLEO, "ventanas": ventanas}


def n1():
    habs = [(f"HABITACIÓN {101 + i}", (FILA1[i], 0, FILA1[i + 1], 700), "") for i in range(6)]
    locales = habs + [("ESTAR DE FAMILIARES", (0, 900, 900, 2400), ""), ("ENFERMERÍA", (900, 900, 1700, 1600), ""), ("SALA DE MÉDICOS", (1700, 900, 2100, 1600), ""),
                      ("ESTAR DE PACIENTES", (2100, 900, 2600, 1600), ""), ("BAÑO ASISTIDO", (3200, 900, 3600, 1600), "H"),
                      ("HABITACIÓN 107", (900, 1800, 1450, 2400), ""), ("HABITACIÓN 108", (1450, 1800, 2000, 2400), "")]
    puertas = [(f"HABITACIÓN {101 + i}", "s", FILA1[i] + 300, 90, "in") for i in range(6)]
    puertas += [("ESTAR DE FAMILIARES", "n", 450, 120, "in"), ("ENFERMERÍA", "n", 1300, 120, "in"), ("SALA DE MÉDICOS", "n", 1900, 90, "in"), ("ESTAR DE PACIENTES", "n", 2350, 100, "in"),
                ("BAÑO ASISTIDO", "n", 3400, 95, "in"), ("PASILLO DE ALA", "w", 1700, 120, "in"), ("HABITACIÓN 107", "n", 1175, 90, "in"), ("HABITACIÓN 108", "n", 1725, 90, "in")]
    ventanas = [(f"HABITACIÓN {101 + i}", "n", FILA1[i] + 300, 150) for i in range(6)]
    ventanas += [("HABITACIÓN 106", "e", 350, 150), ("ESTAR DE FAMILIARES", "w", 1500, 250), ("ESTAR DE FAMILIARES", "s", 450, 250), ("ESTAR DE PACIENTES", "s", 2350, 200),
                 ("BAÑO ASISTIDO", "e", 1250, 100), ("HABITACIÓN 107", "s", 1175, 150), ("HABITACIÓN 108", "s", 1725, 150)]
    return {"id": "n1", "nombre": "PRIMER NIVEL (INTERNACIÓN)", "codigo": "N1", "locales": locales + BASE_PASILLOS + NUCLEO, "puertas": puertas + PUERTAS_NUCLEO, "ventanas": ventanas}


def n2():
    locales = [("QUIRÓFANO 1", (0, 0, 800, 700), ""), ("QUIRÓFANO 2", (800, 0, 1600, 700), ""), ("QUIRÓFANO 3", (1600, 0, 2400, 700), ""), ("TERAPIA INTENSIVA", (2400, 0, 3600, 700), ""),
               ("SALA DE RECUPERACIÓN", (0, 900, 900, 2400), ""), ("ESTERILIZACIÓN", (900, 900, 1500, 1600), "H"), ("LAVADO QUIRÚRGICO", (1500, 900, 2100, 1600), "H"),
               ("ESTAR MÉDICO", (2100, 900, 2600, 1600), ""), ("CUARTO LIMPIO", (3200, 900, 3600, 1600), "H"),
               ("VESTUARIO HOMBRES", (900, 1800, 1450, 2400), "H"), ("VESTUARIO MUJERES", (1450, 1800, 2000, 2400), "H")]
    puertas = [("QUIRÓFANO 1", "s", 400, 140, "in"), ("QUIRÓFANO 2", "s", 1200, 140, "in"), ("QUIRÓFANO 3", "s", 2000, 140, "in"), ("TERAPIA INTENSIVA", "s", 3000, 140, "in"),
               ("SALA DE RECUPERACIÓN", "n", 450, 120, "in"), ("ESTERILIZACIÓN", "n", 1200, 100, "in"), ("LAVADO QUIRÚRGICO", "n", 1800, 100, "in"), ("ESTAR MÉDICO", "n", 2350, 90, "in"),
               ("CUARTO LIMPIO", "n", 3400, 90, "in"), ("PASILLO DE ALA", "w", 1700, 120, "in"), ("VESTUARIO HOMBRES", "n", 1175, 90, "in"), ("VESTUARIO MUJERES", "n", 1725, 90, "in")]
    ventanas = [("TERAPIA INTENSIVA", "n", 3000, 300), ("TERAPIA INTENSIVA", "e", 350, 150), ("SALA DE RECUPERACIÓN", "w", 1500, 250), ("SALA DE RECUPERACIÓN", "s", 450, 250),
                ("ESTAR MÉDICO", "s", 2350, 200), ("VESTUARIO HOMBRES", "s", 1175, 100), ("VESTUARIO MUJERES", "s", 1725, 100)]
    return {"id": "n2", "nombre": "SEGUNDO NIVEL (QUIRÓFANOS Y TERAPIA INTENSIVA)", "codigo": "N2", "locales": locales + BASE_PASILLOS + NUCLEO, "puertas": puertas + PUERTAS_NUCLEO, "ventanas": ventanas}


NIVELES = [pb, n1, n2]
EJES_X = [("A", 0), ("B", 900), ("C", 1500), ("D", 2100), ("E", 2600), ("F", 3200), ("G", 3600)]
EJES_Y = [("1", 0), ("2", 700), ("3", 900), ("4", 1600), ("5", 2400)]


# ---- muros a partir de los locales (el espesor sale de quién comparte cada tramo) --------------------------------------------------------------------------
def muros(locales) -> List[dict]:
    lineas: Dict[tuple, list] = {}
    for _, (x0, y0, x1, y1), fl in locales:
        for o, c, a, b in (("h", y0, x0, x1), ("h", y1, x0, x1), ("v", x0, y0, y1), ("v", x1, y0, y1)):
            lineas.setdefault((o, c), []).append((a, b, fl))
    out: List[dict] = []
    for (o, c), segs in sorted(lineas.items()):
        cortes = sorted({v for a, b, _ in segs for v in (a, b)})
        for p, q in zip(cortes, cortes[1:]):
            cub = [fl for a, b, fl in segs if a <= p and q <= b]
            if not cub:
                continue
            t = 30 if len(cub) == 1 or any("N" in fl for fl in cub) else (12 if all("H" in fl for fl in cub) else 15)
            if out and out[-1]["o"] == o and out[-1]["c"] == c and out[-1]["q"] == p and out[-1]["t"] == t:
                out[-1]["q"] = q
            else:
                out.append({"o": o, "c": c, "p": p, "q": q, "t": t})
    return out


def _espesor_en(ms, o, c, x) -> float:
    """El espesor del muro de la orientación `o` sobre la línea `c` que cubre la posición `x` (0 si no hay)."""
    return max([m["t"] for m in ms if m["o"] == o and m["c"] == c and m["p"] <= x <= m["q"]], default=0)


def rectangulo(m, ms) -> Polygon:
    """El muro como rectángulo, prolongado en cada extremo hasta la cara del muro que cruza (para que las esquinas y los encuentros cierren)."""
    t = m["t"]
    perp = "v" if m["o"] == "h" else "h"
    a = _espesor_en(ms, perp, m["p"], m["c"]) / 2
    b = _espesor_en(ms, perp, m["q"], m["c"]) / 2
    if m["o"] == "h":
        return box(m["p"] - a, m["c"] - t / 2, m["q"] + b, m["c"] + t / 2)
    return box(m["c"] - t / 2, m["p"] - a, m["c"] + t / 2, m["q"] + b)


def punto_de(rect, lado, off) -> Tuple[float, float]:
    x0, y0, x1, y1 = rect
    return {"n": (off, y0), "s": (off, y1), "w": (x0, off), "e": (x1, off)}[lado]


class Nivel:
    """Un nivel ya resuelto: muros, aberturas con su geometría y la verdad de cada local."""

    def __init__(self, d):
        self.id, self.nombre, self.codigo = d["id"], d["nombre"], d["codigo"]
        self.locales = d["locales"]
        self.muros = muros(self.locales)
        self.rect = {n: r for n, r, _ in self.locales}
        self.aberturas = []
        for kind, lista in (("puerta", d["puertas"]), ("ventana", d["ventanas"])):
            for item in lista:
                sala, lado, off, ancho = item[:4]
                giro = item[4] if kind == "puerta" else "in"
                c = punto_de(self.rect[sala], lado, off)
                horizontal = lado in "ns"
                m = next(m for m in self.muros if m["o"] == ("h" if horizontal else "v") and m["c"] == (c[1] if horizontal else c[0]) and m["p"] <= (c[0] if horizontal else c[1]) <= m["q"])
                if not (m["p"] + ancho / 2 <= (c[0] if horizontal else c[1]) <= m["q"] - ancho / 2):
                    raise ValueError(f"{self.id}: {kind} de {ancho} cm en {sala} {lado} {off} no cabe en el muro")
                n = N_[lado]
                self.aberturas.append({"tipo": kind, "sala": sala, "c": c, "ancho": ancho, "t": m["t"], "u": (1, 0) if horizontal else (0, 1), "n": n if giro == "in" else (-n[0], -n[1])})
        todos = unary_union([rectangulo(m, self.muros) for m in self.muros])
        cortes = [self._corte(a) for a in self.aberturas]
        self.macizo = todos                                                         # los muros enteros: con ellos se mide el área libre de cada local
        self.paredes = todos.difference(unary_union(cortes))

    @staticmethod
    def _corte(a) -> Polygon:
        (cx, cy), w, t, (ux, uy) = a["c"], a["ancho"], a["t"], a["u"]
        return box(cx - w / 2, cy - t / 2 - 2, cx + w / 2, cy + t / 2 + 2) if ux else box(cx - t / 2 - 2, cy - w / 2, cx + t / 2 + 2, cy + w / 2)

    def area_libre(self, nombre) -> float:
        """El área en m² de lo que queda dentro del local una vez descontados los muros (lo que mide el motor)."""
        x0, y0, x1, y1 = self.rect[nombre]
        return box(x0, y0, x1, y1).difference(self.macizo).area / 10000.0

    def rotulos(self):
        """Código, nombre, centro y área de cada local (los pasillos y el núcleo también: lo que está dentro de muros se rotula)."""
        out = []
        for k, (n, (x0, y0, x1, y1), fl) in enumerate(self.locales, 1):
            out.append({"codigo": f"{self.codigo}-{k:02d}", "nombre": n, "centro": ((x0 + x1) / 2, (y0 + y1) / 2), "area": self.area_libre(n), "rect": (x0, y0, x1, y1), "nucleo": "N" in fl})
        return out


# ---- primitivas del dibujo (todas en cm, y hacia abajo): líneas, arcos, círculos y textos ------------------------------------------------------------------
def geometria_puerta(a):
    """Hoja abierta 90° hacia `n` con bisagra en el extremo bajo de la abertura: (bisagra, punta de la hoja, punta cerrada, radio)."""
    (cx, cy), w, (ux, uy), (nx, ny) = a["c"], a["ancho"], a["u"], a["n"]
    h = (cx - ux * w / 2, cy - uy * w / 2)
    return h, (h[0] + nx * w, h[1] + ny * w), (h[0] + ux * w, h[1] + uy * w), w


def lineas_ventana(a):
    (cx, cy), w, t, (ux, uy), (nx, ny) = a["c"], a["ancho"], a["t"], a["u"], (0, 1) if a["u"][0] else (1, 0)
    out = []
    for d in (-t / 4, 0, t / 4):
        out.append(((cx - ux * w / 2 + nx * d, cy - uy * w / 2 + ny * d), (cx + ux * w / 2 + nx * d, cy + uy * w / 2 + ny * d)))
    return out


def escalera(n: Nivel):
    """Las huellas de la escalera (una cada 28 cm), su línea de recorrido y el hueco del ascensor con su cruz."""
    x0, y0, x1, y1 = n.rect["ESCALERA"]
    lineas = [((x0 + 25, y), (x1 - 25, y)) for y in range(int(y0 + 60), int(y1 - 60), 28)]
    lineas.append((((x0 + x1) / 2, y1 - 60), ((x0 + x1) / 2, y0 + 60)))
    ax0, ay0, ax1, ay1 = n.rect["ASCENSORES"]
    r = (ax0 + 40, ay0 + 120, ax1 - 40, ay0 + 420)
    lineas += [((r[0], r[1]), (r[2], r[1])), ((r[2], r[1]), (r[2], r[3])), ((r[2], r[3]), (r[0], r[3])), ((r[0], r[3]), (r[0], r[1])), ((r[0], r[1]), (r[2], r[3])), ((r[2], r[1]), (r[0], r[3]))]
    return lineas


def anotaciones(n: Nivel):
    """Ejes con burbujas, cotas encadenadas (vanos de ejes y total) y el título: (líneas, círculos, textos) con su capa."""
    lineas, circulos, textos = [], [], []
    for letra, x in EJES_X:
        lineas.append(("A-EJES", (x, -260), (x, H + 120)))
        circulos.append(("A-EJES", (x, -330), 70))
        textos.append(("A-EJES", letra, (x, -330), 60))
    for num, y in EJES_Y:
        lineas.append(("A-EJES", (-260, y), (W + 120, y)))
        circulos.append(("A-EJES", (-330, y), 70))
        textos.append(("A-EJES", num, (-330, y), 60))
    xs = [x for _, x in EJES_X]
    for yy in (-130, -200):
        lineas.append(("A-COTAS", (xs[0], yy), (xs[-1], yy)))
    for x in xs:
        lineas += [("A-COTAS", (x, -230), (x, -100))]
    for a, b in zip(xs, xs[1:]):
        textos.append(("A-COTAS", f"{(b - a) / 100:.2f}".replace(".", ","), ((a + b) / 2, -150), 22))
    textos.append(("A-COTAS", f"{(xs[-1] - xs[0]) / 100:.2f}".replace(".", ","), ((xs[0] + xs[-1]) / 2, -220), 22))
    ys = [y for _, y in EJES_Y]
    for xx in (-130,):
        lineas.append(("A-COTAS", (xx, ys[0]), (xx, ys[-1])))
    for y in ys:
        lineas.append(("A-COTAS", (-230, y), (-100, y)))
    for a, b in zip(ys, ys[1:]):
        textos.append(("A-COTAS", f"{(b - a) / 100:.2f}".replace(".", ","), (-160, (a + b) / 2), 22))
    textos.append(("A-TEXTO", n.nombre, (0, H + 330), 45))
    textos.append(("A-TEXTO", "ESC. 1:100", (0, H + 420), 22))
    for r in n.rotulos():
        textos.append(("A-TEXTO", r["nombre"], (r["centro"][0], r["centro"][1] - 14), 18))
        textos.append(("A-TEXTO", f"{r['codigo']} · {r['area']:.2f} m²".replace(".", ","), (r["centro"][0], r["centro"][1] + 14), 12))
    return lineas, circulos, textos


# ---- escritura: DXF en metros y PNG --------------------------------------------------------------------------------------------------------------------
def anillos(poligono):
    geoms = [poligono] if isinstance(poligono, Polygon) else list(poligono.geoms)
    for g in geoms:
        yield list(g.exterior.coords)[:-1]
        for hueco in g.interiors:
            yield list(hueco.coords)[:-1]


def escribir_dxf(n: Nivel, ruta: Path) -> None:
    doc = ezdxf.new("R2018", setup=False)
    doc.units = 6
    for capa, color in (("A-MUROS", 7), ("A-PUERTAS", 3), ("A-VENTANAS", 5), ("A-EJES", 1), ("A-COTAS", 1), ("A-TEXTO", 7), ("A-ESCALERA", 8)):
        doc.layers.add(capa, color=color)
    doc.styles.add("ARIAL", font="arial.ttf")
    msp = doc.modelspace()
    m = lambda p: (p[0] / 100.0, (H - p[1]) / 100.0)                           # noqa: E731 - a metros, con y hacia arriba
    for anillo in anillos(n.paredes):
        msp.add_lwpolyline([m(p) for p in anillo], close=True, dxfattribs={"layer": "A-MUROS"})
    for a in n.aberturas:
        if a["tipo"] == "puerta":
            h, punta, cerrada, r = geometria_puerta(a)
            msp.add_line(m(h), m(punta), dxfattribs={"layer": "A-PUERTAS"})
            a0 = math.degrees(math.atan2(m(cerrada)[1] - m(h)[1], m(cerrada)[0] - m(h)[0]))
            a1 = math.degrees(math.atan2(m(punta)[1] - m(h)[1], m(punta)[0] - m(h)[0]))
            if (a1 - a0) % 360 > 180:
                a0, a1 = a1, a0
            msp.add_arc(m(h), r / 100.0, a0, a1, dxfattribs={"layer": "A-PUERTAS"})
        else:
            for p, q in lineas_ventana(a):
                msp.add_line(m(p), m(q), dxfattribs={"layer": "A-VENTANAS"})
    for p, q in escalera(n):
        msp.add_line(m(p), m(q), dxfattribs={"layer": "A-ESCALERA"})
    lineas, circulos, textos = anotaciones(n)
    for capa, p, q in lineas:
        msp.add_line(m(p), m(q), dxfattribs={"layer": capa})
    for capa, c, r in circulos:
        msp.add_circle(m(c), r / 100.0, dxfattribs={"layer": capa})
    for capa, valor, p, alto in textos:
        t = msp.add_text(valor, height=alto / 100.0, dxfattribs={"layer": capa, "style": "ARIAL"})
        t.set_placement(m(p), align=TextEntityAlignment.MIDDLE_CENTER)
    doc.saveas(str(ruta))


def fuente(px: int):
    for nombre in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nombre, px)
        except OSError:
            continue
    return ImageFont.load_default()


def escribir_png(n: Nivel, ruta: Path) -> None:
    s = PX_POR_CM
    img = Image.new("RGB", (int((W + 2 * MARGEN) * s), int((H + 2 * MARGEN) * s)), "white")
    d = ImageDraw.Draw(img)
    p = lambda q: ((q[0] + MARGEN) * s, (q[1] + MARGEN) * s)                    # noqa: E731
    geoms = [n.paredes] if isinstance(n.paredes, Polygon) else list(n.paredes.geoms)
    for g in geoms:
        d.polygon([p(q) for q in list(g.exterior.coords)[:-1]], fill="black")
        for hueco in g.interiors:
            d.polygon([p(q) for q in list(hueco.coords)[:-1]], fill="white")
    for a in n.aberturas:
        if a["tipo"] == "puerta":
            h, punta, cerrada, r = geometria_puerta(a)
            d.line([p(h), p(punta)], fill="black", width=2)
            a0 = math.degrees(math.atan2(cerrada[1] - h[1], cerrada[0] - h[0]))
            a1 = math.degrees(math.atan2(punta[1] - h[1], punta[0] - h[0]))
            if (a1 - a0) % 360 > 180:
                a0, a1 = a1, a0
            (x0, y0), (x1, y1) = p((h[0] - r, h[1] - r)), p((h[0] + r, h[1] + r))
            d.arc([x0, y0, x1, y1], a0, a1, fill="black", width=1)
        else:
            for q, r_ in lineas_ventana(a):
                d.line([p(q), p(r_)], fill="black", width=1)
    for q, r_ in escalera(n):
        d.line([p(q), p(r_)], fill="#555555", width=1)
    lineas, circulos, textos = anotaciones(n)
    for _, q, r_ in lineas:
        d.line([p(q), p(r_)], fill="#aa3333", width=1)
    for _, c, r in circulos:
        (x0, y0), (x1, y1) = p((c[0] - r, c[1] - r)), p((c[0] + r, c[1] + r))
        d.ellipse([x0, y0, x1, y1], outline="#aa3333", width=1)
    for _, valor, q, alto in textos:
        d.text(p(q), valor, fill="black", font=fuente(max(int(alto * s * 1.2), 8)), anchor="mm")
    img.save(ruta)


# ---- el motor y la comparación -------------------------------------------------------------------------------------------------------------------------
def limpio(nombre: str) -> str:
    return " ".join(nombre.upper().replace("·", " ").split())


CODIGO_PEGADO = re.compile(r"\s+[A-Z][A-Z0-9]{0,2}-\d+$")                       # `HABITACIÓN 101 N1-01`: el motor dejó el código del rótulo en el nombre


def pasar_por_el_motor(n: Nivel, ruta: Path, extension: str) -> dict:
    from epc_arch import Options, recognize
    t = time.time()
    res = recognize(ruta.read_bytes(), ruta.name, Options())
    arq = res.architecture
    c = arq.counts()
    verdad = {"puertas": sum(1 for a in n.aberturas if a["tipo"] == "puerta"), "ventanas": sum(1 for a in n.aberturas if a["tipo"] == "ventana")}
    out = {"formato": extension, "segundos": round(time.time() - t, 1), "puertas": [c["doors"], verdad["puertas"]], "ventanas": [c["windows"], verdad["ventanas"]],
           "huecos": c.get("openings", 0), "muros": [c["walls"], len(n.muros)], "ambientes": [len(arq.rooms), len(n.locales)],
           "unidades_por_metro": arq.units_per_metre, "espesor": arq.wall_thickness, "avisos": arq.warnings[:4]}
    out["areas"] = comparar_areas(n, arq) if extension == "dxf" else None
    return out


def comparar_areas(n: Nivel, arq) -> dict:
    """Los ambientes del motor emparejados por nombre con los locales: error del área medida (la escrita en el rótulo no cuenta: sale de la verdad)."""
    por_nombre = {limpio(n_): n_ for n_ in n.rect}
    filas, faltan = [], []
    vistos = set()
    pegados = 0
    for r in arq.rooms:
        nombre = limpio(r.name)
        if CODIGO_PEGADO.search(nombre):
            pegados += 1
            nombre = CODIGO_PEGADO.sub("", nombre)
        clave = por_nombre.get(nombre)
        if clave and r.area_m2 and clave not in vistos:
            vistos.add(clave)
            real = n.area_libre(clave)
            filas.append({"local": clave, "motor_m2": round(r.area_m2, 2), "verdad_m2": round(real, 2), "error_pct": round(100 * (r.area_m2 - real) / real, 1), "rotulo_m2": r.written_m2})
    faltan = sorted(set(n.rect) - vistos)
    errs = [abs(f["error_pct"]) for f in filas]
    return {"emparejados": len(filas), "nombres_con_codigo_pegado": pegados, "sin_emparejar": faltan, "error_medio_pct": round(sum(errs) / len(errs), 1) if errs else None, "error_max_pct": max(errs, default=None), "filas": filas}


def exportar(ruta: Path, carpeta: Path) -> dict:
    t = time.time()
    r = subprocess.run([sys.executable, "-m", "epc_arch.cli_v2", str(ruta), "--out", str(carpeta), "--formats", "svg,dxf,png,pdf", "--sheet", "A1"],
                       capture_output=True, text=True, env={**__import__("os").environ, "PYTHONPATH": str(RAIZ / "src")}, timeout=900)
    return {"codigo": r.returncode, "segundos": round(time.time() - t, 1), "salida": (r.stdout or r.stderr).strip().splitlines()[-1:] or [""]}


def fila(tag, cifras) -> str:
    a, b = cifras
    return f"{tag} {a}/{b}"


def main() -> None:
    exportar_todo = "--sin-exportar" not in sys.argv
    SALIDA.mkdir(parents=True, exist_ok=True)
    informe, verdad = {"niveles": []}, {}
    for fn in NIVELES:
        n = Nivel(fn())
        dxf, png = SALIDA / f"{n.id}.dxf", SALIDA / f"{n.id}.png"
        escribir_dxf(n, dxf)
        escribir_png(n, png)
        verdad[n.id] = {"nombre": n.nombre, "muros": len(n.muros), "puertas": sum(a["tipo"] == "puerta" for a in n.aberturas), "ventanas": sum(a["tipo"] == "ventana" for a in n.aberturas),
                        "locales": {r["nombre"]: {"codigo": r["codigo"], "area_m2": round(r["area"], 2)} for r in n.rotulos()}}
        print(f"{n.id}: {len(n.locales)} locales · {len(n.muros)} tramos de muro · {verdad[n.id]['puertas']} puertas · {verdad[n.id]['ventanas']} ventanas", flush=True)
        corridas = {}
        for ext, ruta in (("dxf", dxf), ("png", png)):
            c = pasar_por_el_motor(n, ruta, ext)
            corridas[ext] = c
            print(f"   motor {ext}: {fila('puertas', c['puertas'])}  {fila('ventanas', c['ventanas'])}  {fila('muros', c['muros'])}  {fila('ambientes', c['ambientes'])}  ({c['segundos']} s)"
                  + (f"  área media {c['areas']['error_medio_pct']} % (máx. {c['areas']['error_max_pct']} %), {c['areas']['nombres_con_codigo_pegado']} nombres con el código pegado" if c["areas"] else ""), flush=True)
        informe["niveles"].append({"id": n.id, "nombre": n.nombre, "corridas": corridas, "exportacion": exportar(dxf, SALIDA / "v2" / n.id) if exportar_todo else None})
        if exportar_todo:
            print(f"   exportación v2: {informe['niveles'][-1]['exportacion']}", flush=True)
    (SALIDA / "verdad.json").write_text(json.dumps(verdad, indent=1, ensure_ascii=False), encoding="utf-8")
    (SALIDA / "informe.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False), encoding="utf-8")
    (SALIDA / "informe.md").write_text(redactar(informe, verdad), encoding="utf-8")
    print(f"listo: {SALIDA}")


def redactar(informe, verdad) -> str:
    out = ["# Proyecto 13 — hospital de tres niveles: lo que reconoce el motor frente a lo dibujado", "",
           "| Nivel | Formato | Puertas | Ventanas | Muros (tramos) | Ambientes | Área media | Segundos |", "|---|---|---|---|---|---|---|---|"]
    for niv in informe["niveles"]:
        for ext, c in niv["corridas"].items():
            area = f"{c['areas']['error_medio_pct']} %" if c["areas"] and c["areas"]["error_medio_pct"] is not None else "—"
            out.append(f"| {niv['id']} | {ext} | {c['puertas'][0]}/{c['puertas'][1]} | {c['ventanas'][0]}/{c['ventanas'][1]} | {c['muros'][0]}/{c['muros'][1]} | {c['ambientes'][0]}/{c['ambientes'][1]} | {area} | {c['segundos']} |")
    out += ["", "Cada cifra es *reconocido/dibujado*. Los muros se cuentan por tramo continuo de un mismo espesor: el motor puede unir o partir tramos, la cifra orienta, no es exacta.", ""]
    for niv in informe["niveles"]:
        a = niv["corridas"]["dxf"]["areas"]
        if a and a["filas"]:
            out += [f"## {niv['nombre']}: áreas medidas (DXF)", "", "| Local | Motor m² | Dibujado m² | Error |", "|---|---|---|---|"]
            out += [f"| {f['local']} | {f['motor_m2']} | {f['verdad_m2']} | {f['error_pct']} % |" for f in a["filas"]]
            if a["sin_emparejar"]:
                out.append(f"\nSin emparejar por nombre: {', '.join(a['sin_emparejar'])}.")
            out.append("")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    main()
