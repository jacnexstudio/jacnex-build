"""Identidad visual de Jacnex sobre una app de la suite.

Las herramientas, los menús y la organización de cada app se quedan como en el original (son los
de Adobe, a los que la gente ya está acostumbrada). Lo que cambia es el acabado:

- Iconos: los mismos dibujos con un trazo más fino (el "trazo Jacnex").
- Tipografía: Plus Jakarta Sans, la fuente de la marca, en lugar de Inter en la interfaz.
- Color: los grises de la interfaz toman un leve tono azul marino y los azules de acento pasan al
  azul Jacnex. El lienzo se queda neutro para no alterar cómo se ven las fotos.

Todo se aplica con reglas, no con parches fijos, para que siga funcionando cuando el original
publica una versión nueva. Si una regla deja de encontrar lo que busca, la compilación se detiene.
"""

import colorsys
import re
import shutil
from pathlib import Path

from reglas.comunes import ErrorDeParche

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "marca" / "fuentes" / "plus-jakarta-sans"

# --- Iconos ---------------------------------------------------------------------------------------

# Trazo de los iconos SVG (24×24, trazo 2 en el original): más fino y con puntas y esquinas
# rectas, en línea con los cortes del logo de Jacnex.
TRAZO_SVG = 0.75
# Trazo de los iconos dibujados en código, relativo al original.
TRAZO_CODIGO = 0.85


def _escalar(m, factor):
    valor = float(m.group(2)) * factor
    return f'{m.group(1)}{valor:.2f}'.rstrip("0").rstrip(".") + m.group(3)


def iconos_svg(carpeta):
    """Afina el trazo de los iconos SVG de la interfaz."""
    cambiados = 0
    for svg in carpeta.glob("**/assets/icons/**/*.svg"):
        if "target" in svg.parts:
            continue
        texto = svg.read_text(encoding="utf-8")
        nuevo = re.sub(r'(stroke-width\s*=\s*")([\d.]+)(")', lambda m: _escalar(m, TRAZO_SVG), texto)
        nuevo = re.sub(r'(stroke-width\s*:\s*)([\d.]+)(\s*[;"])', lambda m: _escalar(m, TRAZO_SVG), nuevo)
        nuevo = re.sub(r'stroke-linecap\s*=\s*"round"', 'stroke-linecap="square"', nuevo)
        nuevo = re.sub(r'stroke-linejoin\s*=\s*"round"', 'stroke-linejoin="miter"', nuevo)
        if nuevo != texto:
            svg.write_text(nuevo, encoding="utf-8", newline="")
            cambiados += 1
    return cambiados


# Cómo fija cada app el grosor de sus iconos dibujados en código (archivo, patrón, grupo numérico).
TRAZOS_EN_CODIGO = {
    "lightcraft": [(r"(Stroke::new\(\()(1\.5)( \* k\)\.max\(1\.0\), color\))", 1)],
    "designcraft": [(r"(let mut pen = Pen \{ p, r, c, w: )(1\.3)( \})", 1)],
    "filmcraft": [(r"(Pen16 \{ painter, rect, color, width: )(1\.25)( \})", 1)],
    "effectcraft": [(r"(Pen16 \{ painter, rect, color, width: )(1\.25)( \})", 1)],
}


def iconos_codigo(carpeta, proyecto):
    reglas = TRAZOS_EN_CODIGO.get(proyecto)
    if not reglas:
        return 0
    archivo = carpeta / "crates" / "ui-egui" / "src" / "icons.rs"
    texto = archivo.read_text(encoding="utf-8")
    for patron, _ in reglas:
        texto, n = re.subn(patron, lambda m: f"{m.group(1)}{float(m.group(2)) * TRAZO_CODIGO:.2f}{m.group(3)}", texto)
        if n == 0:
            raise ErrorDeParche(f"{archivo}: no se encontró el grosor de los iconos ({patron})")
    archivo.write_text(texto, encoding="utf-8", newline="")
    return 1


# --- Color ----------------------------------------------------------------------------------------

TONO_JACNEX = 218 / 360  # el tono del azul Jacnex (#1268F8)


def _tono_gris(r, g, b):
    """Un gris neutro pasa a un gris con un leve tono azul marino, con la misma luminosidad."""
    v = (r + g + b) / 3
    if v <= 10 or v >= 246:
        return r, g, b
    l = v / 255
    s = 0.09 if l < 0.5 else 0.08
    rr, gg, bb = colorsys.hls_to_rgb(TONO_JACNEX, l, s)
    return round(rr * 255), round(gg * 255), round(bb * 255)


def _tono_enfasis(r, g, b):
    """Un gris de selección (herramienta activa, fila elegida) pasa a un azul Jacnex apagado."""
    l = (r + g + b) / 3 / 255
    rr, gg, bb = colorsys.hls_to_rgb(TONO_JACNEX, l, 0.42 if l < 0.5 else 0.6)
    return round(rr * 255), round(gg * 255), round(bb * 255)


def transformar_color(r, g, b, enfasis=False):
    if max(r, g, b) - min(r, g, b) <= 6:
        return _tono_enfasis(r, g, b) if enfasis and 25 < r < 235 else _tono_gris(r, g, b)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if 195 / 360 <= h <= 235 / 360 and s >= 0.35 and 0.2 <= l <= 0.85:
        rr, gg, bb = colorsys.hls_to_rgb(TONO_JACNEX, l, max(s, 0.9))
        return round(rr * 255), round(gg * 255), round(bb * 255)
    return r, g, b


NUM = r"(0x[0-9a-fA-F]{1,2}|\d{1,3})"


def _n(t):
    return int(t, 16) if t.lower().startswith("0x") else int(t)


def _recolorear_linea(linea):
    # El lienzo y lo que lo rodea se quedan neutros: ahí se juzga el color de la imagen.
    if re.search(r"canvas|pasteboard|checker|lienzo", linea, re.I):
        return linea
    # Lo que marca "esto está activo" lleva el azul Jacnex en lugar de un gris.
    enfasis = bool(re.search(r"\b(accent_soft|row_selected|selected\w*|selection\w*|SELECTED\w*)\s*[:=]", linea))

    def rgb(m):
        r, g, b = (_n(m.group(i)) for i in (2, 3, 4))
        if max(r, g, b) > 255:
            return m.group(0)
        nr, ng, nb = transformar_color(r, g, b, enfasis)
        return f"{m.group(1)}({nr}, {ng}, {nb}{m.group(5)}"

    linea = re.sub(rf"(from_rgb|from_rgba_unmultiplied)\(\s*{NUM},\s*{NUM},\s*{NUM}(\s*[,)])", rgb, linea)

    def gris(m):
        v = _n(m.group(2))
        nr, ng, nb = transformar_color(v, v, v, enfasis)
        if (nr, ng, nb) == (v, v, v):
            return m.group(0)
        return f"{m.group(1)}from_rgb({nr}, {ng}, {nb})"

    linea = re.sub(rf"(\bColor32::)from_gray\(\s*{NUM}\s*\)", gris, linea)

    def hexa(m):
        h = m.group(2)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        nr, ng, nb = transformar_color(r, g, b, enfasis)
        return f"{m.group(1)}{nr:02x}{ng:02x}{nb:02x}{m.group(3)}"

    linea = re.sub(r"(\b0x)([0-9a-fA-F]{6})(\b(?!_?[0-9a-fA-F]))", hexa, linea)
    linea = re.sub(r'(")#?([0-9a-fA-F]{6})(")', hexa, linea)
    return linea


def colores(carpeta):
    """Recolorea las paletas de la interfaz (theme.rs y theme/*.rs del crate ui-egui)."""
    src = carpeta / "crates" / "ui-egui" / "src"
    archivos = [p for p in [src / "theme.rs", *sorted((src / "theme").glob("*.rs"))] if p.exists()]
    if not archivos:
        raise ErrorDeParche(f"{src}: no hay theme.rs")
    for archivo in archivos:
        texto = archivo.read_text(encoding="utf-8")
        # Las pruebas comparan con los colores originales: se dejan como están.
        corte = texto.find("#[cfg(test)]")
        cuerpo, pruebas = (texto, "") if corte < 0 else (texto[:corte], texto[corte:])
        nuevo = "".join(_recolorear_linea(l) for l in cuerpo.splitlines(keepends=True)) + pruebas
        if nuevo != texto:
            archivo.write_text(nuevo, encoding="utf-8", newline="")
    return len(archivos)


# --- Tipografía -----------------------------------------------------------------------------------

MODULO_FUENTES = '''//! Identidad Jacnex: Plus Jakarta Sans en la interfaz en lugar de Inter (agregado por Jacnex).
//! Se aplica a cada `set_fonts` del crate; los textos de los documentos no cambian.

use std::sync::Arc;

const REGULAR: &[u8] = include_bytes!("../../../assets/fonts/jacnex/PlusJakartaSans-Regular.ttf");
const MEDIUM: &[u8] = include_bytes!("../../../assets/fonts/jacnex/PlusJakartaSans-Medium.ttf");
const SEMIBOLD: &[u8] = include_bytes!("../../../assets/fonts/jacnex/PlusJakartaSans-SemiBold.ttf");
const BOLD: &[u8] = include_bytes!("../../../assets/fonts/jacnex/PlusJakartaSans-Bold.ttf");

fn reemplazo(nombre: &str) -> Option<&'static [u8]> {
    let n = nombre.to_ascii_lowercase();
    // Layoutnex llama "ui" y "ui-semibold" a su fuente de interfaz (Source Sans 3).
    match n.as_str() {
        "ui" => return Some(REGULAR),
        "ui-semibold" => return Some(SEMIBOLD),
        _ => {}
    }
    if !n.starts_with("inter") || n.contains("italic") || n.starts_with("internal") {
        return None;
    }
    Some(if n.contains("semibold") || n.contains("semi-bold") || n.contains("semi_bold") {
        SEMIBOLD
    } else if n.contains("medium") {
        MEDIUM
    } else if n.contains("bold") {
        BOLD
    } else {
        REGULAR
    })
}

/// Cambia las fuentes Inter de la interfaz por Plus Jakarta Sans, conservando sus ajustes.
pub(crate) fn con_fuentes(mut fonts: egui::FontDefinitions) -> egui::FontDefinitions {
    for (nombre, datos) in fonts.font_data.iter_mut() {
        if let Some(bytes) = reemplazo(nombre) {
            let mut nueva = egui::FontData::from_static(bytes);
            nueva.tweak = datos.tweak.clone();
            *datos = Arc::new(nueva);
        }
    }
    fonts
}
'''


def _envolver_set_fonts(texto):
    """`x.set_fonts(ARG)` → `x.set_fonts(crate::jacnex_marca::con_fuentes(ARG))`."""
    salida, i, n = [], 0, 0
    marca = ".set_fonts("
    while True:
        j = texto.find(marca, i)
        if j < 0:
            salida.append(texto[i:])
            return "".join(salida), n
        k = j + len(marca)
        nivel, fin = 1, k
        while nivel and fin < len(texto):
            nivel += {"(": 1, ")": -1}.get(texto[fin], 0)
            fin += 1
        argumento = texto[k:fin - 1]
        salida.append(texto[i:k] + f"crate::jacnex_marca::con_fuentes({argumento}))")
        i, n = fin, n + 1


def fuentes(carpeta):
    src = carpeta / "crates" / "ui-egui" / "src"
    destino = carpeta / "assets" / "fonts" / "jacnex"
    destino.mkdir(parents=True, exist_ok=True)
    for ttf in FUENTES.glob("*.ttf"):
        shutil.copyfile(ttf, destino / ttf.name)
    shutil.copyfile(FUENTES / "OFL.txt", carpeta / "assets" / "fonts" / "OFL-PlusJakartaSans.txt")
    (src / "jacnex_marca.rs").write_text(MODULO_FUENTES, encoding="utf-8", newline="\n")

    lib = src / "lib.rs"
    texto = lib.read_text(encoding="utf-8")
    if "mod jacnex_marca;" not in texto:
        # Al final: delante podría cortar un atributo interno (#![...]) de varias líneas.
        lib.write_text(texto.rstrip("\n") + "\n\nmod jacnex_marca;\n", encoding="utf-8", newline="")

    total = 0
    for rs in src.rglob("*.rs"):
        if rs.name == "jacnex_marca.rs":
            continue
        texto = rs.read_text(encoding="utf-8")
        if ".set_fonts(" not in texto:
            continue
        nuevo, n = _envolver_set_fonts(texto)
        rs.write_text(nuevo, encoding="utf-8", newline="")
        total += n
    if total == 0:
        raise ErrorDeParche(f"{src}: no se encontró dónde instala las fuentes (set_fonts)")
    return total


def aplicar(carpeta, proyecto):
    """Aplica la identidad Jacnex. Devuelve un resumen para el registro."""
    return {
        "iconos SVG": iconos_svg(carpeta),
        "iconos en código": iconos_codigo(carpeta, proyecto),
        "archivos de color": colores(carpeta),
        "puntos de fuentes": fuentes(carpeta),
    }
