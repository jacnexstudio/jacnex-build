#!/usr/bin/env python3
"""Convierte el código de una app de ArtCraft en su versión Jacnex.

Uso:  python rebrand/rebrand.py <proyecto> <carpeta-del-codigo>
      (proyecto = launcher, o el id de una app de marca.json: photocraft, lightcraft, ...)

Pasos: reemplaza textos, renombra archivos, copia la marca de Jacnex, aplica parches puntuales, la
identidad visual de Jacnex en las apps (identidad.py) y agrega el aviso de modificación al NOTICE.
Al final lista lo que quedó con nombres de ArtCraft
para revisarlo. Si un parche no encuentra lo que espera (porque ArtCraft cambió su código), se
detiene con un error en lugar de producir una versión a medias.
"""

import importlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reglas.comunes import ErrorDeParche  # noqa: E402
import identidad  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
MARCA = json.loads((RAIZ / "marca.json").read_text(encoding="utf-8"))

# Archivos que conservan el texto original: la atribución de la licencia debe mantenerse.
PROTEGIDOS = {"LICENSE-MIT", "LICENSE-APACHE", "LICENSE", "NOTICE", "ATTRIBUTION.md"}
CARPETAS_IGNORADAS = {".git", "target", "node_modules", "dist"}
RESTOS = re.compile(r"ArtCraft|Artcraft|artcraft|storytold|storyteller|Learning Machines")


def archivos(carpeta):
    for ruta in carpeta.rglob("*"):
        if any(p in CARPETAS_IGNORADAS for p in ruta.relative_to(carpeta).parts):
            continue
        if ruta.is_file():
            yield ruta


def leer_texto(ruta):
    try:
        return ruta.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None


def reemplazar_textos(carpeta, reglas):
    cambiados = 0
    for ruta in archivos(carpeta):
        if ruta.name in PROTEGIDOS:
            continue
        texto = leer_texto(ruta)
        if texto is None:
            continue
        nuevo = texto
        for patron, reemplazo in reglas:
            nuevo = patron.sub(reemplazo, nuevo)
        if nuevo != texto:
            ruta.write_bytes(nuevo.encode("utf-8"))
            cambiados += 1
    return cambiados


def renombrar(carpeta, reglas):
    rutas = sorted((r for r in carpeta.rglob("*") if not any(p in CARPETAS_IGNORADAS for p in r.relative_to(carpeta).parts)),
                   key=lambda r: len(r.parts), reverse=True)
    renombrados = 0
    for ruta in rutas:
        nombre = ruta.name
        for patron, reemplazo in reglas:
            nombre = patron.sub(reemplazo, nombre)
        if nombre != ruta.name:
            ruta.rename(ruta.with_name(nombre))
            renombrados += 1
    return renombrados


def copiar_marca(carpeta, copias):
    for destino, origen in copias:
        fuente = RAIZ / "marca" / origen
        objetivo = carpeta / destino
        if not fuente.exists():
            raise ErrorDeParche(f"falta el archivo de marca {fuente}")
        objetivo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fuente, objetivo)
    return len(copias)


def parche(ruta, buscar, reemplazo, regex=False, conteo=1):
    """Reemplazo puntual que falla si el texto esperado no está (o está más veces de lo esperado)."""
    texto = ruta.read_text(encoding="utf-8")
    if regex:
        nuevo, n = re.subn(buscar, reemplazo, texto, flags=re.S)
    else:
        n = texto.count(buscar)
        nuevo = texto.replace(buscar, reemplazo)
    if conteo is not None and n != conteo:
        raise ErrorDeParche(f"{ruta}: se esperaban {conteo} coincidencias de {buscar!r} y hay {n}")
    ruta.write_text(nuevo, encoding="utf-8", newline="")


def aplicar_diseno(carpeta, proyecto):
    """Aplica los parches de diseño de parches/<proyecto>/*.patch (git diff), en orden de nombre.

    Se generan desde una copia de trabajo ya con el cambio de marca, así que se aplican después de
    él. Si ArtCraft cambió el código que un parche toca, git lo rechaza y la compilación se detiene.
    """
    carpeta_parches = RAIZ / "parches" / proyecto
    if not carpeta_parches.is_dir():
        return 0
    lista = sorted(carpeta_parches.glob("*.patch"))
    for archivo in lista:
        resultado = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "--ignore-whitespace", str(archivo)],
            cwd=carpeta, capture_output=True, text=True,
        )
        if resultado.returncode != 0:
            raise ErrorDeParche(f"el parche {archivo.name} no se pudo aplicar:\n{resultado.stderr.strip()}")
    return len(lista)


def avisar_modificacion(carpeta, nombre):
    notice = carpeta / "NOTICE"
    if notice.exists():
        texto = notice.read_text(encoding="utf-8")
        texto += (
            f"\n\nModified version: {nombre}\n"
            f"This is a modified version distributed by {MARCA['empresa']} ({MARCA['web']}). It was renamed and\n"
            "rebranded, and the ArtCraft names, wordmarks and logos were removed as their brand terms require.\n"
            f"{MARCA['empresa']} is not affiliated with or endorsed by the ArtCraft Team. The list of changes is in\n"
            f"https://github.com/{MARCA['github']}/jacnex-build (rebrand/).\n"
        )
        if (carpeta / "assets" / "fonts" / "OFL-PlusJakartaSans.txt").exists():
            texto += (
                "\nPlus Jakarta Sans font (assets/fonts/PlusJakartaSans-Variable.ttf), added by Jacnex — SIL Open\n"
                "Font License 1.1. See assets/fonts/OFL-PlusJakartaSans.txt.\n"
            )
        notice.write_text(texto, encoding="utf-8", newline="")


def restos(carpeta):
    encontrados = {}
    for ruta in archivos(carpeta):
        if ruta.name in PROTEGIDOS:
            continue
        texto = leer_texto(ruta)
        if texto:
            n = len(RESTOS.findall(texto))
            if n:
                encontrados[str(ruta.relative_to(carpeta))] = n
    return encontrados


def compilar(reglas):
    return [(re.compile(p), r) for p, r in reglas]


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    proyecto, carpeta = sys.argv[1], Path(sys.argv[2]).resolve()
    try:
        reglas = importlib.import_module(f"reglas.{proyecto}")
    except ModuleNotFoundError:
        if proyecto not in MARCA["apps"]:
            sys.exit(f"No hay reglas para {proyecto!r} y no es una app de marca.json")
        reglas = importlib.import_module("reglas.app_generica").crear(proyecto)

    print(f"Cambio de marca: {proyecto} en {carpeta}")
    print(f"  textos cambiados en {reemplazar_textos(carpeta, compilar(reglas.textos(MARCA)))} archivos")
    print(f"  {renombrar(carpeta, compilar(reglas.nombres_de_archivo(MARCA)))} archivos o carpetas renombrados")
    print(f"  {copiar_marca(carpeta, reglas.copias_de_marca(MARCA))} archivos de marca copiados")
    reglas.parches(carpeta, MARCA, parche)
    print("  parches aplicados")
    if proyecto != "launcher":
        resumen = identidad.aplicar(carpeta, proyecto)
        print("  identidad Jacnex: " + ", ".join(f"{k} {v}" for k, v in resumen.items()))
    aplicados = aplicar_diseno(carpeta, proyecto)
    if aplicados:
        print(f"  diseño de Jacnex aplicado ({aplicados} parches)")
    avisar_modificacion(carpeta, reglas.nombre_producto(MARCA))

    quedan = restos(carpeta)
    if quedan:
        print(f"  quedan {sum(quedan.values())} menciones de ArtCraft en {len(quedan)} archivos (revisar):")
        for ruta, n in sorted(quedan.items(), key=lambda x: -x[1])[:40]:
            print(f"    {n:4}  {ruta}")


if __name__ == "__main__":
    try:
        main()
    except ErrorDeParche as e:
        sys.exit(f"ERROR: {e}\nArtCraft cambió algo que el cambio de marca necesita; hay que actualizar las reglas.")
