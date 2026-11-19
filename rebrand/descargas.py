"""Jacnex Studio y las apps descargan y se actualizan desde descargas.jacnex.store, no desde GitHub.

descargas.jacnex.store (Cloudflare R2) guarda una copia de cada versión con las mismas rutas que
GitHub (ver espejo/espejo_r2.py), así que basta con cambiar la dirección:

    https://api.github.com/repos/jacnexstudio/<repo>/releases/...  ->  https://descargas.jacnex.store/api/repos/...
    https://github.com/jacnexstudio/<repo>/releases/...            ->  https://descargas.jacnex.store/jacnexstudio/...

Los demás enlaces a los repositorios de Jacnex en GitHub (que pueden ser privados) dejan de
apuntar ahí: "reportar un problema" (issues) lleva al soporte y el resto (página del repositorio,
documentación) a descargas.jacnex.store/jacnexstudio/<repo>, que redirige a la página de la app en
app.jacnex.store. Los enlaces a proyectos de terceros (créditos, modelos, licencias) no se tocan.

Se aplica después de los parches de diseño, así también cubre el código que agregan ellos y no
cambia las líneas de contexto que los parches esperan encontrar.
"""

import re

DESCARGAS = "https://descargas.jacnex.store"

# Archivos que no se tocan: dependencias de cargo y flujos de GitHub Actions del original.
NO_TOCAR = {"Cargo.toml", "Cargo.lock"}
CARPETAS_NO = {".github"}

# Lo que puede seguir a la dirección dentro de un texto o una cadena de format!().
_RESTO = r"[^\s\"'<>()\[\]`|\\]*"


def reglas(marca, proyecto):
    """Lista de (patrón compilado, reemplazo) para el código del launcher o de una app."""
    gh = re.escape(marca["github"])
    soporte = marca["soporte"]

    def repo_jacnex(m):
        resto = m.group(1) or ""
        if "/releases" in resto:
            return f"{DESCARGAS}/{marca['github']}{resto}"
        if "{" in resto.split("/", 2)[-1] and resto.count("/") > 1:
            # Un format!() con más datos después del repositorio: se deja la ruta entera (así no
            # sobran argumentos al compilar).
            return f"{DESCARGAS}/{marca['github']}{resto}"
        if "/issues" in resto:
            return soporte
        # Solo el repositorio (que puede ser {APP} en un format!): la página redirige a la app.
        primero = resto.split("/")[1] if resto.startswith("/") and len(resto) > 1 else ""
        primero = primero.split("#")[0]
        return f"{DESCARGAS}/{marca['github']}" + (f"/{primero}" if primero else "")

    lista = [
        (re.compile(rf"https://api\.github\.com/repos/(?={gh}/|\{{)"), f"{DESCARGAS}/api/repos/"),
        (re.compile(rf"https://github\.com/{gh}(?![A-Za-z0-9_-])({_RESTO})"), repo_jacnex),
    ]
    if proyecto == "launcher":
        # En el launcher, https://github.com/{repo} siempre es el repositorio de una app de Jacnex.
        lista.append((re.compile(r"https://github\.com/(?=\{)"), f"{DESCARGAS}/"))
    return lista


def aplicar(carpeta, marca, proyecto, archivos, leer_texto, protegidos):
    patrones = reglas(marca, proyecto)
    cambiados = 0
    for ruta in archivos(carpeta):
        if ruta.name in NO_TOCAR or ruta.name in protegidos:
            continue
        if any(p in CARPETAS_NO for p in ruta.relative_to(carpeta).parts):
            continue
        texto = leer_texto(ruta)
        if texto is None or "github.com" not in texto:
            continue
        nuevo = texto
        for patron, reemplazo in patrones:
            nuevo = patron.sub(reemplazo, nuevo)
        if nuevo != texto:
            ruta.write_bytes(nuevo.encode("utf-8"))
            cambiados += 1
    return cambiados


# craft-update (dependencia de cargo, ver bibliotecas.py): todos sus repositorios son apps de Jacnex.
CRAFT_UPDATE = [
    (re.compile(r"https://api\.github\.com/repos/(?=\{)"), f"{DESCARGAS}/api/repos/"),
    (re.compile(r"https://github\.com/(?=\{)"), f"{DESCARGAS}/"),
    (re.compile(r"https://github\.com/(?=jacnexstudio/)"), f"{DESCARGAS}/"),
]


def ajustar_craft_update(carpeta_src):
    """Cambia las direcciones en los .rs de craft-update. Devuelve cuántos archivos cambió."""
    cambiados = 0
    for ruta in sorted(carpeta_src.rglob("*.rs")):
        texto = ruta.read_text(encoding="utf-8")
        nuevo = texto
        for patron, reemplazo in CRAFT_UPDATE:
            nuevo = patron.sub(reemplazo, nuevo)
        if nuevo != texto:
            ruta.write_text(nuevo, encoding="utf-8", newline="")
            cambiados += 1
    return cambiados
