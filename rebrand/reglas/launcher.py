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
    lid = marca["launcher"]["id"]
    return [
        *comunes.copias_logos(),
        *comunes.copias_icono(lid, f"{marca['prefijo_id']}.{lid}", "svg/mark.svg", "launcher"),
        # El ícono de la comunidad (antes Discord) es el de WhatsApp.
        ("assets/social/discord.svg", "svg/whatsapp.svg"),
        # Íconos de cada app en el catálogo del launcher.
        *[(f"assets/app-icons/{app}.png", f"generado/apps/{app}/icon-128.png") for app in marca["apps"]],
    ]


def parches(carpeta, marca, parche):
    # Jacnex todavía no tiene redes sociales propias: se quitan los íconos de las de ArtCraft.
    parche(carpeta / "crates/core/src/catalog.rs",
           r"pub const SOCIAL: \[\(&str, &str\); \d+\] = \[.*?\];",
           "pub const SOCIAL: [(&str, &str); 0] = [];", regex=True)

    # Apps que Jacnex no ofrece (marca.json: "excluida"): se quitan del catálogo del launcher.
    catalogo = carpeta / "crates/core/src/catalog.rs"
    excluidas = [app for app, datos in marca["apps"].items() if datos.get("excluida")]
    for app in excluidas:
        parche(catalogo, rf'\n    app\(\s*"{app}",.*?"[^"]*/{app}",\s*\),', "", regex=True)
    if excluidas:
        parche(catalogo, r"pub const SUITE: \[CraftApp; \d+\]",
               f"pub const SUITE: [CraftApp; {len(marca['apps']) - len(excluidas)}]", regex=True)
    comunes.ajustar_instalador_windows(carpeta, "launcher")
