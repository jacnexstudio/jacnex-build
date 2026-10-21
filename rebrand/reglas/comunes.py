"""Reglas compartidas por el launcher y todas las apps."""

import re
import uuid

IDENT = r"[A-Za-z0-9_]"


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
        (rf"storytold/({ids_apps(marca)})\b", rf"{gh}/\1"),
        (r'(GITHUB_OWNER: &str = )"storytold"', rf'\1"{gh}"'),
        (r'"https://github\.com/storytold"', f'"https://github.com/{gh}"'),
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


def cambiar_upgrade_codes(carpeta, proyecto):
    """Un instalador de Jacnex no debe reemplazar ni chocar con el original de ArtCraft instalado."""
    cambiados = 0
    for wxs in carpeta.rglob("*.wxs"):
        texto = wxs.read_text(encoding="utf-8")
        nuevo = re.sub(r'(UpgradeCode=")([0-9A-Fa-f-]{36})(")', lambda m: m.group(1) + nuevo_guid(proyecto, m.group(2)) + m.group(3), texto)
        if nuevo != texto:
            wxs.write_text(nuevo, encoding="utf-8", newline="")
            cambiados += 1
    return cambiados
