# jacnex-build

Convierte las apps de código abierto de [ArtCraft](https://github.com/storytold) (MIT o Apache-2.0)
en la suite **Jacnex Studio** y las compila.

- `marca.json`: nombres de Jacnex para el launcher y cada app.
- `marca/`: logos e íconos (`npm run generar` los regenera desde `marca/svg/`).
- `rebrand/`: el cambio de marca. `python rebrand/rebrand.py <proyecto> <carpeta>` reemplaza
  nombres, enlaces e identificadores, cambia logos e íconos y agrega el aviso de modificación al
  `NOTICE`. Las reglas de cada proyecto están en `rebrand/reglas/`.
- `.github/workflows/compilar-windows.yml`: flujo reutilizable que toma la última versión original,
  le aplica el cambio de marca, la compila para Windows y la publica en el repositorio de la app.

## Licencias

El código original pertenece al ArtCraft Team y sus colaboradores y se distribuye bajo sus licencias
(MIT o Apache-2.0); cada versión compilada conserva sus `LICENSE-*`, `NOTICE` y `ATTRIBUTION.md`.
Jacnex no está afiliado ni respaldado por el ArtCraft Team.

Los scripts de este repositorio se publican bajo MIT o Apache-2.0. El nombre, los logos y los íconos
de Jacnex (`marca/`) no tienen licencia libre: ver `marca/LICENSE-brand.txt`.
