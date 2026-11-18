"""Pone la versión de Jacnex en el código de ArtCraft antes de compilar.

    python version.py <carpeta del código> <X.Y.Z>

Jacnex publica su propia versión cuando vuelve a compilar una app con cambios suyos sin que
ArtCraft haya sacado una nueva (0.19.2 de ArtCraft -> 0.19.3 de Jacnex). Las actualizaciones
automáticas y el instalador MSI solo reemplazan un programa por uno con un número X.Y.Z mayor,
así que volver a publicar el mismo número no le llegaría a nadie.

La versión vive en un solo lugar: `version` dentro de `[workspace.package]` del Cargo.toml de la
raíz (todas las crates usan `version.workspace = true`). Después hay que refrescar Cargo.lock con
`cargo update --workspace`, que solo cambia las entradas de las crates del propio código.
"""

import re
import sys
from pathlib import Path

VERSION = re.compile(r"^\d+\.\d+\.\d+$")
LINEA = re.compile(r'^(\s*version\s*=\s*")([^"]+)(".*)$')


class ErrorDeVersion(Exception):
    pass


def poner_version(texto: str, nueva: str) -> tuple[str, str]:
    """Devuelve el Cargo.toml con la versión nueva y la versión que tenía."""
    if not VERSION.match(nueva):
        raise ErrorDeVersion(f"versión no válida: {nueva!r} (se espera X.Y.Z)")
    lineas = texto.splitlines(keepends=True)
    en_seccion = False
    for i, linea in enumerate(lineas):
        limpia = linea.strip()
        if limpia.startswith("["):
            en_seccion = limpia == "[workspace.package]"
            continue
        if en_seccion:
            m = LINEA.match(linea.rstrip("\r\n"))
            if m:
                final = linea[len(linea.rstrip("\r\n")):]
                lineas[i] = f"{m.group(1)}{nueva}{m.group(3)}{final}"
                return "".join(lineas), m.group(2)
    raise ErrorDeVersion('no hay `version = "…"` en [workspace.package] del Cargo.toml')


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    manifiesto = Path(argv[1]) / "Cargo.toml"
    try:
        # newline="": deja los saltos de línea como están (CRLF en Windows).
        with manifiesto.open(encoding="utf-8", newline="") as f:
            texto = f.read()
        nuevo, antes = poner_version(texto, argv[2])
    except (OSError, ErrorDeVersion) as e:
        print(f"Versión: {e}", file=sys.stderr)
        return 1
    with manifiesto.open("w", encoding="utf-8", newline="") as f:
        f.write(nuevo)
    print(f"Versión: {antes} -> {argv[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
