"""Reglas para ArtCraft Launcher -> Jacnex Studio (storytold/craft-launcher)."""

from reglas import comunes


def nombre_producto(marca):
    return marca["launcher"]["nombre"]


def textos(marca):
    lanzador = marca["launcher"]
    return [
        *comunes.urls_y_repos(marca),
        *comunes.comunidad(),
        (r"ArtCraft Launcher", lanzador["nombre"]),
        (r"Craft App Suite", marca["suite"]),
        *comunes.nombres_de_apps(marca),
        (r"artcraft-launcher", lanzador["id"]),
        (r"artcraft_launcher", lanzador["id"].replace("-", "_")),
        (r"ARTCRAFT_LAUNCHER", lanzador["id"].replace("-", "_").upper()),
        *comunes.marca_generica(marca),
    ]


def nombres_de_archivo(marca):
    lanzador = marca["launcher"]
    return [
        (r"ai\.storyteller\.", f"{marca['prefijo_id']}."),
        (r"artcraft-launcher", lanzador["id"]),
        (r"artcraft_launcher", lanzador["id"].replace("-", "_")),
        (r"artcraft", marca["empresa"].lower()),
    ]


def copias_de_marca(marca):
    """(destino dentro del código, archivo en marca/) — después de renombrar."""
    lid, prefijo = marca["launcher"]["id"], marca["prefijo_id"]
    copias = [
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
        (f"assets/app-icon/{lid}.svg", "svg/mark.svg"),
        (f"assets/app-icon/{lid}-1024.png", "generado/icon-1024.png"),
        (f"assets/app-icon/{lid}.ico", "generado/icon.ico"),
        (f"assets/app-icon/{lid}.icns", "generado/icon.icns"),
        (f"assets/app-icon/hicolor/scalable/apps/{prefijo}.{lid}.svg", "svg/mark.svg"),
    ]
    for t in (16, 24, 32, 48, 64, 128, 256, 512):
        copias.append((f"assets/app-icon/hicolor/{t}x{t}/apps/{prefijo}.{lid}.png", f"generado/icon-{t}.png"))
    return copias


def parches(carpeta, marca, parche):
    # Jacnex todavía no tiene redes sociales propias: se quitan los íconos de las de ArtCraft.
    parche(carpeta / "crates/core/src/catalog.rs",
           r"pub const SOCIAL: \[\(&str, &str\); \d+\] = \[.*?\];",
           "pub const SOCIAL: [(&str, &str); 0] = [];", regex=True)
    comunes.cambiar_upgrade_codes(carpeta, "launcher")
