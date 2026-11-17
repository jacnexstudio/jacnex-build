"""Ajusta las bibliotecas de ArtCraft que la app descarga al compilar (dependencias git de cargo).

    python bibliotecas.py <carpeta del código>

El cambio de marca solo toca el código del repositorio; craft-update llega aparte, desde
storytold/craft-libs, en la versión fijada en Cargo.lock. Este paso descarga las dependencias
(cargo fetch --locked) y cambia la copia descargada, así no hay que tocar Cargo.lock (la
compilación usa --locked). Se ejecuta después de restaurar la caché de Rust y antes de compilar.

Ajuste: actualizarse sin firma digital. En Windows craft-update solo instala una actualización si
el programa tiene firma Authenticode del mismo editor. Las versiones de Jacnex todavía no están
firmadas, así que el launcher decía "this copy of Jacnex Studio isn't signed" y no se
actualizaba. Sin firma propia se acepta la descarga: igual se comprueba con el SHA-256 publicado
en la versión de GitHub (jacnexstudio) antes de instalar nada. Cuando el programa esté firmado,
vuelve a exigirse la firma del mismo editor.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


class ErrorDeAjuste(Exception):
    pass


MARCA = "Jacnex: sin firma propia"

AJUSTES = [
    # Una copia sin firma también recibe la actualización (ArtCraft solo la ofrece si está firmada).
    (
        "fn can_self_update_at(app: &App, exe: &Path, opted_in: bool) -> bool {\n"
        "    current_at(app, exe, opted_in).is_some() && (opted_in || is_signed(exe))\n",
        "fn can_self_update_at(app: &App, exe: &Path, opted_in: bool) -> bool {\n"
        f"    // {MARCA}: también se actualiza (la descarga se comprueba con su SHA-256).\n"
        "    let _ = is_signed;\n"
        "    current_at(app, exe, opted_in).is_some()\n",
    ),
    # Sin firma propia no hay editor con el que comparar: vale la comprobación del SHA-256.
    (
        "    let ours = publisher(reference).map_err(|e| format!(\"this copy of {} isn't signed ({e}), "
        "so it doesn't install updates\", app.name))?;\n",
        f"    // {MARCA}: la descarga ya se comprobó con el SHA-256 publicado en la versión.\n"
        "    let Ok(ours) = publisher(reference) else { return Ok(()) };\n"
        "    let _ = app;\n",
    ),
]


def cargo_home():
    return Path(os.environ.get("CARGO_HOME") or Path.home() / ".cargo")


def revisiones_craft_update(carpeta):
    lock = (carpeta / "Cargo.lock").read_text(encoding="utf-8")
    revs = set()
    for bloque in lock.split("[[package]]"):
        if re.search(r'(?m)^name = "craft-update"$', bloque):
            m = re.search(r'(?m)^source = "git\+[^"#]*#([0-9a-f]{40})"$', bloque)
            if not m:
                raise ErrorDeAjuste("Cargo.lock: craft-update no viene de git")
            revs.add(m.group(1))
    return revs


def ajustar(archivo):
    texto = archivo.read_text(encoding="utf-8")
    if MARCA in texto:
        if any(viejo in texto for viejo, _ in AJUSTES):
            raise ErrorDeAjuste(f"{archivo}: ajustado a medias")
        return False
    for viejo, nuevo in AJUSTES:
        n = texto.count(viejo)
        if n != 1:
            raise ErrorDeAjuste(f"{archivo}: se esperaba 1 coincidencia de {viejo[:80]!r} y hay {n}")
        texto = texto.replace(viejo, nuevo)
    archivo.write_text(texto, encoding="utf-8", newline="")
    return True


def recompilar(carpeta):
    """Cargo no revisa si cambió una dependencia git (la reconoce por su revisión) y la caché de Rust
    puede traerla ya compilada: se borran sus huellas para que se compile con el ajuste."""
    destino = Path(os.environ.get("CARGO_TARGET_DIR") or carpeta / "target")
    if not destino.is_dir():
        return 0
    borradas = 0
    for huella in destino.glob("**/.fingerprint/craft-update-*"):
        shutil.rmtree(huella, ignore_errors=True)
        borradas += 1
    return borradas


def main():
    carpeta = Path(sys.argv[1]).resolve()
    revs = revisiones_craft_update(carpeta)
    if not revs:
        print("Bibliotecas: el proyecto no usa craft-update")
        return
    subprocess.run(["cargo", "fetch", "--locked"], cwd=carpeta, check=True)
    for rev in sorted(revs):
        archivos = list((cargo_home() / "git" / "checkouts").glob(f"craft-libs-*/{rev[:7]}/crates/update/src/self_update.rs"))
        if not archivos:
            raise ErrorDeAjuste(f"no se encontró craft-update {rev[:7]} en {cargo_home()}")
        for archivo in archivos:
            print(f"Bibliotecas: craft-update {rev[:7]} {'ajustado' if ajustar(archivo) else 'ya estaba ajustado'}")
    print(f"Bibliotecas: {recompilar(carpeta)} huellas de compilación de craft-update borradas")


if __name__ == "__main__":
    try:
        main()
    except ErrorDeAjuste as e:
        print(f"ERROR: {e}\nArtCraft cambió craft-update; hay que actualizar rebrand/bibliotecas.py.", file=sys.stderr)
        sys.exit(1)
