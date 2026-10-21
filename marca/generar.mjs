// Genera los PNG, ICO e ICNS de la marca a partir de svg/ (que escribe disenar.py).
// Uso: npm install && npm run generar
import { Resvg } from '@resvg/resvg-js';
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';

const SALIDA = 'generado';
const TAMANOS = [16, 24, 32, 48, 64, 128, 256, 512, 1024];

const png = (svg, ancho) => new Resvg(readFileSync(`svg/${svg}`, 'utf8'), { fitTo: { mode: 'width', value: ancho } }).render().asPng();
const guardar = (ruta, datos) => { writeFileSync(`${SALIDA}/${ruta}`, datos); };

// ICO con imágenes PNG dentro (válido desde Windows Vista).
function ico(lista) {
  const cabecera = Buffer.alloc(6);
  cabecera.writeUInt16LE(0, 0); cabecera.writeUInt16LE(1, 2); cabecera.writeUInt16LE(lista.length, 4);
  let desplazamiento = 6 + 16 * lista.length;
  const entradas = lista.map(([t, datos]) => {
    const e = Buffer.alloc(16);
    e.writeUInt8(t >= 256 ? 0 : t, 0); e.writeUInt8(t >= 256 ? 0 : t, 1);
    e.writeUInt16LE(1, 4); e.writeUInt16LE(32, 6);
    e.writeUInt32LE(datos.length, 8); e.writeUInt32LE(desplazamiento, 12);
    desplazamiento += datos.length;
    return e;
  });
  return Buffer.concat([cabecera, ...entradas, ...lista.map(([, d]) => d)]);
}

// ICNS con PNG: ic07=128, ic08=256, ic09=512, ic10=1024.
function icns(lista) {
  const bloques = lista.map(([tipo, datos]) => {
    const c = Buffer.alloc(8);
    c.write(tipo, 0, 'ascii'); c.writeUInt32BE(datos.length + 8, 4);
    return Buffer.concat([c, datos]);
  });
  const c = Buffer.alloc(8);
  c.write('icns', 0, 'ascii'); c.writeUInt32BE(8 + bloques.reduce((s, b) => s + b.length, 0), 4);
  return Buffer.concat([c, ...bloques]);
}

/** Juego completo de íconos de una app: icon-<t>.png, icon.ico e icon.icns en `carpeta`. */
function juegoDeIconos(svg, carpeta) {
  mkdirSync(`${SALIDA}/${carpeta}`, { recursive: true });
  const iconos = Object.fromEntries(TAMANOS.map((t) => [t, png(svg, t)]));
  for (const t of TAMANOS) guardar(`${carpeta}/icon-${t}.png`, iconos[t]);
  guardar(`${carpeta}/icon.ico`, ico([16, 24, 32, 48, 64, 128, 256].map((t) => [t, iconos[t]])));
  guardar(`${carpeta}/icon.icns`, icns([['ic07', iconos[128]], ['ic08', iconos[256]], ['ic09', iconos[512]], ['ic10', iconos[1024]]]));
}

mkdirSync(SALIDA, { recursive: true });
guardar('logo.png', png('logo.svg', 3200));
guardar('logo-white.png', png('logo-white.svg', 3200));
guardar('logo-vertical.png', png('logo-vertical.svg', 1600));
guardar('mark.png', png('mark.svg', 1024));
guardar('mark-64.png', png('mark.svg', 64));
guardar('mark-black.png', png('mark-black.svg', 1024));
guardar('mark-black-44.png', png('mark-black.svg', 44));

juegoDeIconos('mark.svg', 'launcher');
const apps = readdirSync('svg/apps').filter((f) => f.endsWith('.svg')).map((f) => f.slice(0, -4));
for (const app of apps) juegoDeIconos(`apps/${app}.svg`, `apps/${app}`);
console.log(`Listo: logos, launcher y ${apps.length} apps en ${SALIDA}/`);
