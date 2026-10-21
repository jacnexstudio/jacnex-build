"""Reglas para PhotoCraft -> Next Photo (storytold/photocraft).

Se reemplazan los logos de ArtCraft (docs/brand), que no son libres, y el ícono de la app por el
hexagonal de Jacnex.
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
        *comunes.copias_logos(),
        *comunes.copias_icono(APP, f"{marca['prefijo_id']}.{APP}", f"svg/apps/{APP}.svg", f"apps/{APP}"),
        (f"assets/app-icon/{APP}-small.svg", f"svg/apps/{APP}.svg"),
    ]


def parches(carpeta, marca, parche):
    comunes.ajustar_instalador_windows(carpeta, APP)
