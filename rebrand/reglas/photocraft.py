"""Reglas para PhotoCraft -> Jacnex Photo (storytold/photocraft).

Los íconos de la app (assets/app-icon) tienen la misma licencia que el código, así que se conservan;
solo se reemplazan los logos de ArtCraft (docs/brand), que no son libres.
"""

from reglas import comunes

APP = "photocraft"


def nombre_producto(marca):
    return marca["apps"][APP]["nombre"]


def textos(marca):
    return [
        *comunes.urls_y_repos(marca),
        *comunes.comunidad(),
        *comunes.nombres_de_apps(marca),
        *comunes.marca_generica(marca),
    ]


def nombres_de_archivo(marca):
    return [
        (r"ai\.storyteller\.", f"{marca['prefijo_id']}."),
        (r"artcraft", marca["empresa"].lower()),
    ]


def copias_de_marca(marca):
    return [
        ("docs/brand/jacnex-logo.svg", "svg/logo.svg"),
        ("docs/brand/jacnex-logo-white.svg", "svg/logo-white.svg"),
        ("docs/brand/jacnex-mark.svg", "svg/mark.svg"),
        ("docs/brand/jacnex-mark-black.svg", "svg/mark-black.svg"),
        ("docs/brand/jacnex-logo.png", "generado/logo.png"),
        ("docs/brand/jacnex-logo-white.png", "generado/logo-white.png"),
        ("docs/brand/jacnex-mark.png", "generado/mark.png"),
        ("docs/brand/jacnex-mark-black.png", "generado/mark-black.png"),
        ("docs/brand/LICENSE-brand.txt", "LICENSE-brand.txt"),
    ]


def parches(carpeta, marca, parche):
    if comunes.cambiar_upgrade_codes(carpeta, APP) != 1:
        raise comunes.ErrorDeParche("se esperaba un instalador .wxs con UpgradeCode")
