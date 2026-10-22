#!/usr/bin/env python3
"""Diseña los SVG de la marca Jacnex: logo de Jacnex Studio (basado en el logo oficial de
Jacnex Solutions) y el ícono hexagonal de cada app.

Uso: pip install fonttools==4.55.3 && python disenar.py   (escribe en svg/)
Las letras se convierten en trazos con la fuente Archivo (SIL OFL 1.1, fuentes/OFL-Archivo.txt).
"""

from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

AQUI = Path(__file__).parent
SALIDA = AQUI / "svg"
FUENTE = AQUI / "fuentes" / "Archivo-Variable.ttf"

AZUL = "#1268F8"         # hexágono del logo oficial
AZUL_OSCURO_TEMA = "#4D8EFF"  # el mismo azul, legible sobre fondo oscuro
MARINO = "#091E3D"        # "JACNEX" del logo oficial

# Hexágono del logo oficial, medido sobre la imagen original y llevado a 0..100 de alto.
HEXAGONO = [(50, 0), (95.9, 23.1), (95.9, 76.7), (50, 100), (4.1, 76.7), (4.1, 23.1)]
# La "A" sin travesaño del logo oficial.
CHEVRON = "M50 23.3L78.4 72H64.9L50 44.4L35.1 72H21.6Z"


def hexagono_redondeado(radio=6.0):
    """Trazo del hexágono con esquinas redondeadas (como el original)."""
    pts = HEXAGONO
    n = len(pts)
    partes = []
    for i in range(n):
        anterior, actual, siguiente = pts[i - 1], pts[i], pts[(i + 1) % n]

        def hacia(a, b, d):
            dx, dy = b[0] - a[0], b[1] - a[1]
            largo = (dx * dx + dy * dy) ** 0.5
            return (a[0] + dx / largo * d, a[1] + dy / largo * d)

        entrada = hacia(actual, anterior, radio)
        salida = hacia(actual, siguiente, radio)
        partes.append(f"{'M' if i == 0 else 'L'}{entrada[0]:.2f} {entrada[1]:.2f}")
        partes.append(f"Q{actual[0]:.2f} {actual[1]:.2f} {salida[0]:.2f} {salida[1]:.2f}")
    return "".join(partes) + "Z"


HEX = hexagono_redondeado()


class Texto:
    """Convierte texto en trazos SVG con Archivo en el grosor y ancho pedidos."""

    def __init__(self, peso, ancho):
        fuente = instantiateVariableFont(TTFont(FUENTE), {"wght": peso, "wdth": ancho})
        self.glifos = fuente.getGlyphSet()
        self.cmap = fuente.getBestCmap()
        self.alto_mayuscula = fuente["OS/2"].sCapHeight
        self.hmtx = fuente["hmtx"]

    def trazo(self, texto, alto, x=0.0, y_base=0.0, espaciado=0.0):
        """Devuelve (d, ancho_total) con las mayúsculas de `alto` unidades de alto."""
        escala = alto / self.alto_mayuscula
        partes, cursor = [], x
        for i, letra in enumerate(texto):
            nombre = self.cmap[ord(letra)]
            pen = SVGPathPen(self.glifos)
            self.glifos[nombre].draw(TransformPen(pen, (escala, 0, 0, -escala, cursor, y_base)))
            partes.append(pen.getCommands())
            cursor += self.hmtx[nombre][0] * escala
            if i < len(texto) - 1:
                cursor += espaciado
        return " ".join(partes), cursor - x


def svg(vista, contenido):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vista}">{contenido}</svg>\n'


def marca_jacnex(x=0, y=0, escala=1.0, color=AZUL):
    return (f'<g transform="translate({x} {y}) scale({escala})"><path d="{HEX}" fill="{color}"/>'
            f'<path d="{CHEVRON}" fill="#fff"/></g>')


# --- Íconos de las apps: el hexágono en el color de cada app con un símbolo blanco -----------

TRAZO = 'fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"'
RELLENO = 'fill="#fff"'

SIMBOLOS = {
    # Fotos: montañas y sol
    "photocraft": f'<path {RELLENO} d="M24 70L41 45L52 59L60 49L76 70Z"/><circle {RELLENO} cx="64" cy="36" r="6"/>',
    # Revelado: sol
    "lightcraft": f'<circle {RELLENO} cx="50" cy="50" r="11"/><path {TRAZO} d="M50 23V29M50 71V77M23 50H29M71 50H77M31 31L35 35M65 65L69 69M31 69L35 65M65 35L69 31"/>',
    # Vectores: curva con nodos
    "vectorcraft": f'<path {TRAZO} d="M28 68C34 36 66 64 72 32"/><rect {RELLENO} x="22" y="62" width="12" height="12" rx="2"/><rect {RELLENO} x="66" y="26" width="12" height="12" rx="2"/>',
    # Video: botón de reproducir
    "filmcraft": f'<path {RELLENO} d="M40 31Q38 30 38 33V67Q38 70 40 69L70 52Q72 50 70 48Z"/>',
    # Animación: esfera con estela
    "effectcraft": f'<circle {RELLENO} cx="60" cy="50" r="13"/><path {TRAZO} d="M24 40H38M20 50H36M24 60H38"/>',
    # Maquetación: página de revista (titular, imagen y texto)
    "designcraft": f'<rect {TRAZO} x="28" y="25" width="44" height="50" rx="3"/><path {TRAZO} d="M36 35H64M56 47H64M56 56H64M56 65H64"/><rect {RELLENO} x="34" y="43" width="15" height="25" rx="1.5"/>',
    # PDF: documento con esquina doblada
    "pdfcraft": f'<path {TRAZO} d="M33 24H55L69 38V74H33Z"/><path {TRAZO} d="M55 24V38H69M41 50H61M41 61H55"/>',
    # Prototipos: puntero sobre un marco
    "figcraft": f'<path {TRAZO} d="M30 40V30H40M60 30H70V40M70 60V70H60M40 70H30V60"/><path {RELLENO} d="M44 42L62 52L54 54L50 62Z"/>',
    # Escritura: líneas de texto
    "wordcraft": f'<path {TRAZO} d="M30 34H70M30 46H70M30 58H70M30 70H54"/>',
    # Hojas de cálculo: tabla
    "gridcraft": f'<rect {TRAZO} x="27" y="29" width="46" height="42" rx="3"/><path {TRAZO} d="M27 43H73M27 57H73M43 29V71M58 29V71"/>',
    # Presentaciones: pantalla con gráfico
    "deckcraft": f'<rect {TRAZO} x="25" y="28" width="50" height="34" rx="3"/><path {TRAZO} d="M50 62V72M40 74H60M37 54V47M48 54V41M59 54V44"/>',
    # Audio: onda
    "soundcraft": f'<path {TRAZO} d="M28 44V56M38 36V64M48 28V72M58 38V62M68 45V55"/>',
    # CAD: escuadra
    "cadcraft": f'<path {TRAZO} d="M28 72V28L72 72Z"/><path {TRAZO} d="M38 62V52L48 62Z"/>',
    # IA (Next Forge): destello
    "forge": f'<path {RELLENO} d="M50 22Q53 44 76 50Q53 56 50 78Q47 56 24 50Q47 44 50 22Z"/><path {RELLENO} d="M71 24Q72 30 78 31Q72 32 71 38Q70 32 64 31Q70 30 71 24Z"/>',
}

# Colores de cada app (los de la suite original, algunos oscurecidos para que el blanco se lea).
COLORES = {
    "photocraft": "#2F7BF5", "lightcraft": "#E08A00", "vectorcraft": "#E8573F", "filmcraft": "#8B5CF6",
    "effectcraft": "#E0368F", "designcraft": "#5E9A12", "pdfcraft": "#0E9E84", "figcraft": "#00A874",
    "wordcraft": "#3F5FE0", "gridcraft": "#1F9D55", "deckcraft": "#F07A1E", "soundcraft": "#1A9CC0",
    "cadcraft": "#2F8FD6", "forge": "#6D4AFF",
}


def icono_app(app_id):
    return svg("0 0 100 100", f'<path d="{HEX}" fill="{COLORES[app_id]}"/>{SIMBOLOS[app_id]}')


def main():
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "apps").mkdir(exist_ok=True)
    negrita = Texto(peso=900, ancho=112)
    fina = Texto(peso=600, ancho=112)

    # Logo horizontal (cabecera del launcher): hexágono + JACNEX + STUDIO en una línea.
    d_jacnex, ancho_jacnex = negrita.trazo("JACNEX", 60, x=118, y_base=80, espaciado=2)
    d_studio, ancho_studio = fina.trazo("STUDIO", 60, x=118 + ancho_jacnex + 26, y_base=80, espaciado=14)
    total = 118 + ancho_jacnex + 26 + ancho_studio
    vista = f"-2 -2 {total + 4:.1f} 104"
    for nombre, color_texto, color_studio in (("logo.svg", MARINO, AZUL), ("logo-white.svg", "#FFFFFF", AZUL_OSCURO_TEMA)):
        (SALIDA / nombre).write_text(svg(vista, marca_jacnex() + f'<path d="{d_jacnex}" fill="{color_texto}"/><path d="{d_studio}" fill="{color_studio}"/>'), encoding="utf-8")

    # Logo vertical (como el oficial): hexágono arriba, JACNEX y STUDIO debajo.
    d_j, a_j = negrita.trazo("JACNEX", 70, y_base=0, espaciado=3)
    d_s, a_s = fina.trazo("STUDIO", 24, y_base=0, espaciado=20)
    ancho = max(a_j, a_s)
    hex_lado = 150
    contenido = (
        marca_jacnex(x=(ancho - hex_lado * 0.918) / 2 - 4.1 * 1.5, y=0, escala=1.5)
        + f'<g transform="translate({(ancho - a_j) / 2:.1f} 250)"><path d="{d_j}" fill="{MARINO}"/></g>'
        + f'<g transform="translate({(ancho - a_s) / 2:.1f} 300)"><path d="{d_s}" fill="{AZUL}"/></g>'
    )
    (SALIDA / "logo-vertical.svg").write_text(svg(f"-10 -10 {ancho + 20:.1f} 330", contenido), encoding="utf-8")

    # Ícono del launcher (Jacnex Studio) y versión negra para la bandeja de macOS.
    (SALIDA / "mark.svg").write_text(svg("0 0 100 100", marca_jacnex()), encoding="utf-8")
    (SALIDA / "mark-black.svg").write_text(
        svg("0 0 100 100", f'<path fill-rule="evenodd" fill="#000" d="{HEX}{CHEVRON}"/>'), encoding="utf-8")

    # Imágenes del instalador (Inno Setup): franja lateral en marino con el logo, y el ícono.
    d_jw, a_jw = negrita.trazo("JACNEX", 21, y_base=0, espaciado=1)
    d_sw, a_sw = fina.trazo("STUDIO", 7.5, y_base=0, espaciado=6.5)
    lateral = (
        f'<rect width="164" height="314" fill="{MARINO}"/>'
        + marca_jacnex(x=(164 - 0.62 * 91.8) / 2 - 0.62 * 4.1, y=96, escala=0.62)
        + f'<g transform="translate({(164 - a_jw) / 2:.2f} 192)"><path d="{d_jw}" fill="#FFFFFF"/></g>'
        + f'<g transform="translate({(164 - a_sw) / 2:.2f} 210)"><path d="{d_sw}" fill="{AZUL_OSCURO_TEMA}"/></g>'
    )
    (SALIDA / "instalador-lateral.svg").write_text(svg("0 0 164 314", lateral), encoding="utf-8")
    (SALIDA / "instalador-icono.svg").write_text(svg("-6 -6 112 112", '<rect x="-6" y="-6" width="112" height="112" fill="#FFFFFF"/>' + marca_jacnex()), encoding="utf-8")

    for app_id in SIMBOLOS:
        (SALIDA / "apps" / f"{app_id}.svg").write_text(icono_app(app_id), encoding="utf-8")
    print(f"SVG escritos en {SALIDA} ({len(SIMBOLOS)} íconos de apps)")


if __name__ == "__main__":
    main()
