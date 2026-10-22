"""Reglas para cualquier app de la suite (PhotoCraft -> Next Photo, LightCraft -> Next Light, ...).

Se reemplazan los logos de ArtCraft (docs/brand), que no son libres, y el ícono de la app por el
hexagonal de Jacnex. Una app con necesidades propias puede tener su propio archivo de reglas.
"""

from types import SimpleNamespace

from reglas import comunes


def crear(app):
    def nombre_producto(marca):
        return marca["apps"][app]["nombre"]

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
            *comunes.copias_logos(),
            *comunes.copias_icono(app, f"{marca['prefijo_id']}.{app}", f"svg/apps/{app}.svg", f"apps/{app}"),
            (f"assets/app-icon/{app}-small.svg", f"svg/apps/{app}.svg"),
            (f"assets/app-icon/{app}-macos-512.png", f"generado/apps/{app}/icon-512.png"),
        ]

    def parches(carpeta, marca, parche):
        comunes.ajustar_instalador_windows(carpeta, app)

    return SimpleNamespace(nombre_producto=nombre_producto, textos=textos, nombres_de_archivo=nombres_de_archivo,
                           copias_de_marca=copias_de_marca, parches=parches)
