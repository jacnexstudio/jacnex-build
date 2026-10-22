"""Reglas compartidas por el launcher y todas las apps."""

import re
import uuid

IDENT = r"[A-Za-z0-9_]"


class ErrorDeParche(Exception):
    """El código original cambió y una regla ya no encuentra lo que esperaba."""


def ids_apps(marca):
    ids = list(marca["apps"])
    for app in marca["apps"].values():
        ids += [a.lower() for a in app["anteriores"]]
    return "|".join(ids)


def urls_y_repos(marca):
    """Direcciones web, repositorios e identificadores de ArtCraft que pasan a ser de Jacnex."""
    gh, web, soporte = marca["github"], marca["web"], marca["soporte"]
    return [
        (r"https://(?:www\.)?getartcraft\.com", web),
        (r"(?:www\.)?getartcraft\.com", web.removeprefix("https://")),
        (r"raw\.githubusercontent\.com/storytold/craft-launcher-assets", f"raw.githubusercontent.com/{gh}/jacnex-assets"),
        (r"storytold/craft-launcher-assets", f"{gh}/jacnex-assets"),
        (r"storytold/craft-launcher\b", f"{gh}/{marca['launcher']['repo']}"),
        # Los enlaces a las apps pasan a Jacnex, pero no las dependencias de código (git = "..." en
        # Cargo.toml y git+https://... en Cargo.lock), que deben seguir bajando el código original.
        (rf'(?<!git = "https://github\.com/)(?<!git\+https://github\.com/)storytold/({ids_apps(marca)})\b', rf"{gh}/\1"),
        (r'(GITHUB_OWNER: &str = )"storytold"', rf'\1"{gh}"'),
        (r'"https://github\.com/storytold"', f'"https://github.com/{gh}"'),
        # Enlaces armados en el código: format!("https://github.com/storytold/{app}")
        (r"https://github\.com/storytold/\{", f"https://github.com/{gh}/{{"),
        # El launcher pregunta las versiones a un servidor de ArtCraft; el de Jacnex vive en su web
        # (si no responde, el launcher consulta GitHub directamente).
        (r"https://api\.storyteller\.ai/v1/craft_apps/release_info", f"{web}/api/suite/release_info"),
        (r"[\w.+-]+@storyteller\.ai", f"soporte@{web.removeprefix('https://')}"),
        (r"ai\.storyteller\.", f"{marca['prefijo_id']}."),
        (r'"ai\.storyteller"', f'"{marca["prefijo_id"]}"'),
        (r"https://discord\.gg/artcraft", soporte),
        (r"discord://-/invite/artcraft", soporte),
        (r"Learning Machines (?:LLC|Inc\.?)", marca["empresa"]),
    ]


def comunidad():
    """ArtCraft invita a su Discord; Jacnex ofrece su página de soporte."""
    return [
        (r"Join the ArtCraft community on Discord", "Get help from the Jacnex team"),
        (r"Únete a la comunidad de ArtCraft en Discord", "Recibe ayuda del equipo de Jacnex"),
        (r"Join the ArtCraft Discord(…|\.\.\.)?", r"Jacnex help and support\1"),
        (r"Únete al Discord de ArtCraft(…|\.\.\.)?", r"Ayuda y soporte de Jacnex\1"),
    ]


def nombres_de_apps(marca):
    """PhotoCraft -> Jacnex Photo, etc. Solo palabras completas: no toca identificadores como PhotoCraftData."""
    reglas = []
    for app_id, app in marca["apps"].items():
        originales = [marca["nombres_originales"][app_id], *app["anteriores"]]
        for original in originales:
            reglas.append((rf"(?<!{IDENT}){re.escape(original)}(?!{IDENT})", app["nombre"]))
    reglas += [
        (r"Every Craft app", "Every Jacnex app"),
        (r"(?<!{0})Craft apps(?!{0})".format(IDENT), "Jacnex apps"),
        (r"(?<!{0})Craft app(?!{0})".format(IDENT), "Jacnex app"),
        (r"aplicaciones Craft", "aplicaciones Jacnex"),
    ]
    return reglas


def marca_generica(marca):
    """Lo que quede con el nombre ArtCraft (incluye nombres internos, siempre de forma consistente)."""
    e = marca["empresa"]
    return [(r"ArtCraft", e), (r"Artcraft", e), (r"ARTCRAFT", e.upper()), (r"artcraft", e.lower())]


def nuevo_guid(proyecto, guid):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://jacnex.com/{proyecto}/{guid.upper()}")).upper()


GUID = re.compile(r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b")


def renovar_guids(carpeta_windows, proyecto):
    """Cambia todos los GUID de los archivos del instalador por otros propios y estables.

    El mismo GUID original da siempre el mismo nuevo en todos los archivos, así los scripts que lo
    verifican (como test-msi.ps1) siguen coincidiendo con el .wxs.
    """
    def reemplazo(m):
        original, nuevo = m.group(0), nuevo_guid(proyecto, m.group(0))
        return nuevo.lower() if original == original.lower() else nuevo

    for archivo in carpeta_windows.iterdir():
        if archivo.suffix.lower() not in (".wxs", ".wxi", ".wxl", ".ps1"):
            continue
        datos = archivo.read_bytes()
        bom = datos.startswith(b"\xef\xbb\xbf")
        texto = datos.decode("utf-8-sig")
        nuevo = GUID.sub(reemplazo, texto)
        if nuevo != texto:
            archivo.write_bytes((b"\xef\xbb\xbf" if bom else b"") + nuevo.encode("utf-8"))


LICENCIAS = ("NOTICE", "LICENSE-MIT", "LICENSE-APACHE", "ATTRIBUTION.md", "ASSETS.md")
KEYPATH = ' KeyPath="yes"'


def ajustar_instalador_windows(carpeta, proyecto):
    """Prepara el instalador de Windows (WiX) y el paquete portable de una app.

    - Identificadores propios (UpgradeCode y Guid de componentes): un producto de Jacnex no debe
      reemplazar ni confundirse con el original de ArtCraft si ambos están instalados.
    - NOTICE, licencias y atribuciones dentro del MSI y del zip portable, como exige la licencia.
    """
    windows = carpeta / "packaging" / "windows"
    # El instalador principal se llama como la app; algunas tienen además installer-ui.wxs.
    wxs_lista = list(windows.glob("*.wxs"))
    wxs = windows / f"{proyecto}.wxs" if len(wxs_lista) > 1 else (wxs_lista[0] if wxs_lista else None)
    ps1 = windows / "package.ps1"
    if wxs is None or not wxs.exists() or not ps1.exists():
        raise ErrorDeParche(f"no se encontró el instalador .wxs o package.ps1 en {windows}")

    texto = wxs.read_text(encoding="utf-8")
    renovar_guids(windows, proyecto)
    texto = wxs.read_text(encoding="utf-8")
    # Solo las licencias que existen y que el instalador no incluye ya (algunas apps ya las traen).
    # Si el instalador ya empaca una carpeta entera (p. ej. docs/ con las licencias, como VectorCraft),
    # no se agrega nada: WiX rechaza archivos repetidos.
    if "<Files Include=" in texto:
        licencias = []
    else:
        licencias = [n for n in LICENCIAS if (carpeta / n).exists() and f'\\{n}"' not in texto]
    # Un componente por archivo: WiX solo genera el Guid solo para componentes de un archivo.
    componente = "".join(
        f'      <Component Id="JacnexLicencia{i}" Directory="INSTALLFOLDER">\n'
        f'        <File Id="JacnexLic{i}" Source="$(var.BinDir)\\{n}"{KEYPATH} />\n'
        f'      </Component>\n'
        for i, n in enumerate(licencias))
    if texto.count("</ComponentGroup>") < 1:
        raise ErrorDeParche(f"{wxs}: no se encontró </ComponentGroup>")
    texto = texto.replace("    </ComponentGroup>", componente + "    </ComponentGroup>", 1)
    wxs.write_text(texto, encoding="utf-8", newline="")

    script = ps1.read_text(encoding="utf-8")
    copia_bin = re.search(r"^Copy-Item \(Join-Path \$Bin .*\$Stage[ \t]*$", script, flags=re.M)
    if not copia_bin:
        raise ErrorDeParche(f"{ps1}: no se encontró la copia de binarios a $Stage")
    lista = ", ".join(f"'{n}'" for n in LICENCIAS if (carpeta / n).exists())
    linea = f"\nforeach ($f in {lista}) {{ Copy-Item (Join-Path $Root $f) $Stage }}"
    script = script[:copia_bin.end()] + linea + script[copia_bin.end():]
    # Paquete portable: agrega NOTICE y ATTRIBUTION.md a la lista de archivos si faltan.
    script, n = re.subn(r"foreach \(\$f in ('README\.md'[^)]*)\)",
                        lambda m: "foreach ($f in " + m.group(1) + "".join(
                            f", '{x}'" for x in ("NOTICE", "ATTRIBUTION.md") if f"'{x}'" not in m.group(1)) + ")",
                        script)
    if n < 1:
        raise ErrorDeParche(f"{ps1}: no se encontró la lista de archivos del paquete portable")
    ps1.write_text(script, encoding="utf-8", newline="")


TAMANOS_HICOLOR = (16, 24, 32, 48, 64, 128, 256, 512)


def copias_logos():
    """Logos de Jacnex en lugar de los de ArtCraft (docs/brand, ya renombrados a jacnex-*)."""
    return [
        ("docs/brand/jacnex-logo.svg", "svg/logo.svg"),
        ("docs/brand/jacnex-logo-white.svg", "svg/logo-white.svg"),
        ("docs/brand/jacnex-mark.svg", "svg/mark.svg"),
        ("docs/brand/jacnex-mark-black.svg", "svg/mark-black.svg"),
        ("docs/brand/jacnex-logo.png", "generado/logo.png"),
        ("docs/brand/jacnex-logo-white.png", "generado/logo-white.png"),
        ("docs/brand/jacnex-mark.png", "generado/mark.png"),
        ("docs/brand/jacnex-mark-64.png", "generado/mark-64.png"),
        ("docs/brand/jacnex-mark-black.png", "generado/mark-black.png"),
        ("docs/brand/jacnex-mark-black-44.png", "generado/mark-black-44.png"),
        ("docs/brand/LICENSE-brand.txt", "LICENSE-brand.txt"),
    ]


def copias_icono(stem, id_hicolor, svg, carpeta):
    """El juego de íconos de una app en assets/app-icon/ (como lo organizan las apps de ArtCraft)."""
    copias = [
        (f"assets/app-icon/{stem}.svg", svg),
        (f"assets/app-icon/{stem}-1024.png", f"generado/{carpeta}/icon-1024.png"),
        (f"assets/app-icon/{stem}.ico", f"generado/{carpeta}/icon.ico"),
        (f"assets/app-icon/{stem}.icns", f"generado/{carpeta}/icon.icns"),
        (f"assets/app-icon/hicolor/scalable/apps/{id_hicolor}.svg", svg),
    ]
    for t in TAMANOS_HICOLOR:
        copias.append((f"assets/app-icon/hicolor/{t}x{t}/apps/{id_hicolor}.png", f"generado/{carpeta}/icon-{t}.png"))
    return copias
