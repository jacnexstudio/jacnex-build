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

Ajuste: las apps ponen al día un Jacnex Studio atascado. Jacnex Studio 0.19.2 salió sin el ajuste
anterior (la caché trajo craft-update ya compilado) y no puede actualizarse solo: su propio código
exige la firma. Pero sí instala las apps nuevas, que solo se comprueban con su SHA-256. Por eso
cada app de Jacnex, al abrirse en Windows, revisa el Jacnex Studio instalado y, si es uno de esos,
lo actualiza a la última versión (obligatorio, con aviso y la ventana de Windows Installer).

Ajuste: escribir "@" en Windows (ver TECLADO).

Ajuste: Jacnex Studio reconoce su propio MSI (ver AJUSTES_MSI). craft-update solo trata como "el
launcher" a artcraft-launcher (con su carpeta anotada en HKCU, Learning Machines LLC) y solo cuenta
los instaladores publicados por "Learning Machines LLC". Jacnex Studio 0.19.3 y 0.19.4 no
encontraban su instalación (publicada por "Jacnex") y decían "Windows lists this app's
installation more than once or not at all". Ahora se actualiza como el launcher de ArtCraft. Las
apps ponen al día también esas dos versiones (ver MODULO).
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
    # Al abrirse, cada app revisa si el Jacnex Studio instalado está atascado (ver MODULO).
    (
        "pub fn finish(app: &App, args: &[OsString]) -> Option<Result<(), String>> {\n"
        "    if args.first().is_none_or(|a| a != FINISH_FLAG) {\n"
        "        return None;\n",
        "pub fn finish(app: &App, args: &[OsString]) -> Option<Result<(), String>> {\n"
        "    if args.first().is_none_or(|a| a != FINISH_FLAG) {\n"
        "        // Jacnex: pone al día un Jacnex Studio que no puede actualizarse solo.\n"
        "        jacnex_launcher::revisar(app);\n"
        "        return None;\n",
    ),
]

# Archivo de craft-update (junto a self_update.rs) -> ajustes, en las versiones que lo tienen.
AJUSTES_MSI = {
    "msi_copy.rs": [
        # Jacnex Studio es el launcher: con su MSI en su carpeta se actualiza sin contar productos.
        (
            "        let is_launcher = app.id == crate::suite::LAUNCHER.id;\n",
            "        // Jacnex: Jacnex Studio también es el launcher.\n"
            "        let is_launcher = app.id == crate::suite::LAUNCHER.id || app.id == \"jacnex-studio\";\n",
        ),
        # La carpeta que el MSI de Jacnex anota en HKCU\Software\Jacnex\<app>.
        (
            "        let key = RegKey::predef(HKEY_CURRENT_USER).open_subkey(format!(r\"Software\\Learning Machines LLC\\{}\", app.name)).ok()?;\n",
            "        // Jacnex: el MSI de Jacnex anota su carpeta en HKCU\\Software\\Jacnex\\<app>.\n"
            "        let key = RegKey::predef(HKEY_CURRENT_USER)\n"
            "            .open_subkey(format!(r\"Software\\Jacnex\\{}\", app.name))\n"
            "            .or_else(|_| RegKey::predef(HKEY_CURRENT_USER).open_subkey(format!(r\"Software\\Learning Machines LLC\\{}\", app.name)))\n"
            "            .ok()?;\n",
        ),
        # Otro texto: así las apps distinguen un Jacnex Studio sin este ajuste (ver MODULO).
        (
            "    \"Windows lists this app's installation more than once or not at all, so it can't tell which copy to update. Use the app's installer instead.\";\n",
            "    \"Windows registra esta app más de una vez o ninguna, así que no se sabe qué copia actualizar. Usa el instalador de la app.\";\n",
        ),
    ],
    "detect.rs": [
        # Los instaladores de Jacnex los publica "Jacnex".
        (
            "    publisher == PUBLISHER && app.names().any(|n| n == display_name)\n",
            "    // Jacnex: los instaladores de Jacnex los publica \"Jacnex\".\n"
            "    (publisher == PUBLISHER || publisher == \"Jacnex\") && app.names().any(|n| n == display_name)\n",
        ),
    ],
}

INICIO_MODULO = "// --- Jacnex: las apps ponen al día un Jacnex Studio atascado"

# Se agrega al final de self_update.rs. Solo Windows: ahí se repartió Jacnex Studio 0.19.2.
MODULO = INICIO_MODULO + r''' (agregado por Jacnex) ---------------

/// Jacnex Studio 0.19.2 y anteriores salieron con la comprobación de firma de ArtCraft: sin firma
/// digital no se actualizan solos ("isn't signed ... so it doesn't install updates"). 0.19.3 y
/// 0.19.4 no reconocen su propio MSI ("Windows lists this app's installation more than once or not
/// at all"). Cada app de
/// Jacnex, al abrirse, revisa el Jacnex Studio instalado y, si es uno de esos, descarga el MSI de
/// la última versión de jacnexstudio/jacnex-studio, lo comprueba con el SHA-256 publicado, avisa,
/// cierra Jacnex Studio, lo instala con la ventana de progreso de Windows Installer (por usuario,
/// sin permiso de administrador) y lo vuelve a abrir. Es obligatorio: si algo falla, se intenta
/// otra vez al abrir una app.
#[cfg(windows)]
mod jacnex_launcher {
    use std::path::{Path, PathBuf};
    use std::time::{Duration, SystemTime};

    use crate::app::App;
    use crate::http::{Http, Stop};
    use crate::process;

    const LANZADOR: &str = "jacnex-studio";
    const EXE: &str = "jacnex-studio.exe";
    const CLAVE: &str = r"Software\Jacnex\Jacnex Studio";
    const DESCARGAS: &str = "https://github.com/jacnexstudio/jacnex-studio/releases/latest/download/";
    /// Textos que solo tiene un Jacnex Studio que no puede actualizarse solo: el que exige firma
    /// digital y el que no reconoce su propio MSI. Escritos al revés: este código también va dentro
    /// de Jacnex Studio, que si no los tendría siempre.
    const ATASCADO: [&str; 2] = ["setadpu llatsni t'nseod ti os", "lla ta ton ro ecno naht erom noitallatsni s'ppa siht stsil swodniW"];
    /// Entre un intento y el siguiente: varias apps abiertas a la vez no lo hacen dos veces.
    const ENTRE_INTENTOS: Duration = Duration::from_secs(10 * 60);
    const AVISO: &str = "Hay una versión nueva de Jacnex Studio y es obligatoria. Jacnex Studio se cerrará unos segundos mientras se instala y luego se abrirá solo.";

    /// Revisa Jacnex Studio en segundo plano: la app abre sin esperar.
    pub(super) fn revisar(app: &App) {
        if app.id == LANZADOR {
            return;
        }
        let _ = std::thread::Builder::new().name("jacnex-studio-al-dia".into()).spawn(|| {
            let Some(exe) = instalado() else { return };
            if let Err(e) = poner_al_dia(&exe, &std::env::temp_dir().join("jacnex-studio-actualizacion"), true) {
                log::warn!("Jacnex Studio no se pudo poner al día: {e}");
            }
        });
    }

    /// El jacnex-studio.exe que instaló el MSI (por usuario).
    fn instalado() -> Option<PathBuf> {
        let clave = winreg::RegKey::predef(winreg::enums::HKEY_CURRENT_USER).open_subkey(CLAVE).ok()?;
        let carpeta: String = clave.get_value("InstallDir").ok()?;
        let exe = PathBuf::from(carpeta).join(EXE);
        exe.is_file().then_some(exe)
    }

    fn atascado(exe: &Path) -> bool {
        let Ok(datos) = std::fs::read(exe) else { return false };
        ATASCADO.iter().any(|al_reves| {
            let texto: Vec<u8> = al_reves.bytes().rev().collect();
            datos.windows(texto.len()).any(|w| w == texto.as_slice())
        })
    }

    fn reciente(marca: &Path) -> bool {
        std::fs::metadata(marca)
            .and_then(|m| m.modified())
            .ok()
            .and_then(|t| SystemTime::now().duration_since(t).ok())
            .is_some_and(|d| d < ENTRE_INTENTOS)
    }

    /// Si `exe` está atascado, descarga el MSI de la última versión a `temporal` y lo comprueba;
    /// con `instalar`, además lo instala. Devuelve el MSI descargado.
    pub(super) fn poner_al_dia(exe: &Path, temporal: &Path, instalar: bool) -> Result<Option<PathBuf>, String> {
        if !atascado(exe) {
            return Ok(None);
        }
        std::fs::create_dir_all(temporal).map_err(|e| format!("no se pudo crear {} ({e})", temporal.display()))?;
        let marca = temporal.join("ultimo-intento");
        if reciente(&marca) {
            return Ok(None);
        }
        std::fs::write(&marca, b"").map_err(|e| format!("no se pudo escribir {} ({e})", marca.display()))?;
        let http = Http::new("JacnexSuite/LauncherUpdate")?;
        let sumas = http.get_text(&format!("{DESCARGAS}SHA256SUMS.txt"))?.ok_or("la última versión no publica SHA256SUMS.txt")?;
        let (sha, nombre) = crate::release::parse_sha256sums(&sumas)
            .into_iter()
            .find(|(_, n)| n.starts_with("jacnex-studio-") && n.ends_with("-windows-x64.msi"))
            .ok_or("la última versión no tiene el MSI de Windows")?;
        let msi = temporal.join(&nombre);
        http.download(&format!("{DESCARGAS}{nombre}"), &msi, 0, &sha, &Stop::default(), &mut |_| {})?;
        if instalar {
            instalar_msi(exe, &msi)?;
        }
        Ok(Some(msi))
    }

    /// Avisa, cierra Jacnex Studio, instala el MSI y lo vuelve a abrir.
    fn instalar_msi(exe: &Path, msi: &Path) -> Result<(), String> {
        avisar();
        let abierto = process::capture("tasklist", &["/FI", "IMAGENAME eq jacnex-studio.exe", "/NH"], Duration::from_secs(15))
            .is_some_and(|s| s.to_ascii_lowercase().contains(EXE));
        if abierto {
            // Sin /T: la app que hace esto pudo abrirla Jacnex Studio y no se cierra con él.
            let _ = process::run("taskkill", &["/F", "/IM", EXE], Duration::from_secs(15));
            std::thread::sleep(Duration::from_secs(2));
        }
        let hecho = crate::install::windows::run_msi(msi, None, &Stop::default(), &mut |_| {});
        if abierto || hecho.is_ok() {
            let _ = process::spawn_detached(std::process::Command::new(exe));
        }
        hecho?;
        if atascado(exe) {
            return Err("después de instalar sigue la versión anterior".into());
        }
        let _ = std::fs::remove_file(msi);
        Ok(())
    }

    /// Un aviso de Windows encima de todo, que se cierra solo a los 15 segundos.
    fn avisar() {
        let script = format!("(New-Object -ComObject WScript.Shell).Popup('{AVISO}', 15, 'Jacnex Studio', 4160) | Out-Null");
        let _ = process::run("powershell", &["-NoProfile", "-NonInteractive", "-Command", &script], Duration::from_secs(60));
    }
}
'''


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
    """Aplica cada ajuste que falte: una copia ajustada antes, con menos ajustes, recibe los nuevos."""
    texto = archivo.read_text(encoding="utf-8")
    antes = texto
    for viejo, nuevo in AJUSTES:
        if nuevo in texto:
            continue
        n = texto.count(viejo)
        if n != 1:
            raise ErrorDeAjuste(f"{archivo}: se esperaba 1 coincidencia de {viejo[:80]!r} y hay {n}")
        texto = texto.replace(viejo, nuevo)
    if MODULO not in texto:
        # Una copia con un módulo anterior recibe el nuevo.
        if INICIO_MODULO in texto:
            texto = texto[: texto.index(INICIO_MODULO)]
        texto = texto.rstrip("\n") + "\n\n" + MODULO
    cambio = texto != antes
    if cambio:
        archivo.write_text(texto, encoding="utf-8", newline="")
    for nombre, ajustes in AJUSTES_MSI.items():
        otro = archivo.with_name(nombre)
        if otro.exists() and aplicar(otro, ajustes):
            cambio = True
    return cambio


def aplicar(archivo, ajustes):
    """Como ajustar, para los archivos de AJUSTES_MSI."""
    texto = archivo.read_text(encoding="utf-8")
    antes = texto
    for viejo, nuevo in ajustes:
        if nuevo in texto:
            continue
        n = texto.count(viejo)
        if n != 1:
            raise ErrorDeAjuste(f"{archivo}: se esperaba 1 coincidencia de {viejo[:80]!r} y hay {n}")
        texto = texto.replace(viejo, nuevo)
    if texto == antes:
        return False
    archivo.write_text(texto, encoding="utf-8", newline="")
    return True


COMPILADOS = (
    "**/.fingerprint/craft-update-*",
    "**/build/craft-update-*",
    "**/deps/libcraft_update-*",
    "**/deps/craft_update-*",
)


def recompilar(carpeta, compilados=COMPILADOS):
    """Cargo no revisa si cambió una dependencia git (la reconoce por su revisión) y la caché de Rust
    puede traerla ya compilada: se borra lo compilado de craft-update (huellas y bibliotecas) para
    que se compile con el ajuste. Borrar solo las huellas no bastó: Jacnex Studio 0.19.2 salió con
    la comprobación de firma de antes porque la caché trajo craft-update compilado y no se borró
    nada. Por eso, además, compilar-windows.yml revisa el programa después de compilar."""
    destino = Path(os.environ.get("CARGO_TARGET_DIR") or carpeta / "target")
    if not destino.is_dir():
        return 0
    borradas = 0
    for patron in compilados:
        for ruta in destino.glob(patron):
            if ruta.is_dir():
                shutil.rmtree(ruta, ignore_errors=True)
            else:
                ruta.unlink(missing_ok=True)
            borradas += 1
    return borradas



# Ajustes de teclado en Windows, en egui-winit y winit (dependencias git de ArtCraft). En el teclado
# latinoamericano "@" es AltGr+Q, que Windows también da con Ctrl+Alt+Q, o Alt+64.
#  - egui-winit tiraba el texto escrito con Ctrl apretado (para no escribir con Ctrl+C), y Ctrl+Alt
#    es AltGr: con Ctrl+Alt+Q no salía la "@".
#  - winit pasaba a Windows las teclas con Alt, que en una ventana sin bordes (Jacnex Studio) dejan
#    la ventana en el modo del menú del sistema, que no se ve: la tecla siguiente elegía una opción
#    ("Minimizar"). Sin menú propio, Alt ya no abre ese menú, como hace GLFW.
#  - Aun así la ventana se minimizaba al escribir "@" en el inicio de sesión: mientras la ventana no
#    tiene botón de minimizar (Jacnex Studio lo quita en esa pantalla), winit no deja que Windows
#    la minimice con ningún atajo (SC_MINIMIZE).
# Si ArtCraft cambia de versión y el texto no está, se avisa y se compila sin el ajuste.
TECLADO = [
    (
        "egui-winit",
        "egui-*/*/crates/egui-winit/src/lib.rs",
        "                let is_cmd =\n"
        "                    self.modifiers.ctrl || self.modifiers.command || self.modifiers.mac_cmd;\n",
        "                // Jacnex: en Windows Ctrl+Alt es AltGr (\"@\" es Ctrl+Alt+Q en el teclado latinoamericano).\n"
        "                let is_cmd = (self.modifiers.ctrl || self.modifiers.command || self.modifiers.mac_cmd)\n"
        "                    && !(cfg!(windows) && self.modifiers.ctrl && self.modifiers.alt);\n",
        ("**/.fingerprint/egui-winit-*", "**/build/egui-winit-*", "**/deps/libegui_winit-*", "**/deps/egui_winit-*"),
    ),
    (
        "winit",
        "winit-*/*/src/platform_impl/windows/event_loop.rs",
        "            result = ProcResult::DefWindowProc(wparam);\n"
        "        },\n"
        "\n"
        "        WM_MOUSEMOVE => {\n",
        "            // Jacnex: sin menú propio, Alt no abre el menú del sistema (SC_KEYMENU): en una ventana\n"
        "            // sin bordes no se ve y la tecla siguiente elegía una opción, como \"Minimizar\".\n"
        "            if wparam & 0xfff0 == 0xf100 && unsafe { GetMenu(window) } == 0 {\n"
        "                result = ProcResult::Value(0);\n"
        "                return;\n"
        "            }\n"
        "            result = ProcResult::DefWindowProc(wparam);\n"
        "        },\n"
        "\n"
        "        WM_MOUSEMOVE => {\n",
        ("**/.fingerprint/winit-*", "**/build/winit-*", "**/deps/libwinit-*", "**/deps/winit-*"),
    ),
    (
        "winit",
        "winit-*/*/src/platform_impl/windows/event_loop.rs",
        "        WM_SYSCOMMAND => {\n"
        "            if wparam == SC_RESTORE as usize {\n",
        "        WM_SYSCOMMAND => {\n"
        "            // Jacnex: sin el botón de minimizar (Jacnex Studio lo quita en el inicio de sesión),\n"
        "            // Windows no minimiza la ventana por su cuenta: ni atajos de teclado, ni el menú del\n"
        "            // sistema, ni la barra de tareas. El botón propio de la ventana sí (no pasa por aquí).\n"
        "            if wparam & 0xfff0 == SC_MINIMIZE as usize\n"
        "                && !userdata.window_state_lock().window_flags.contains(WindowFlags::MINIMIZABLE)\n"
        "            {\n"
        "                result = ProcResult::Value(0);\n"
        "                return;\n"
        "            }\n"
        "            if wparam == SC_RESTORE as usize {\n",
        ("**/.fingerprint/winit-*", "**/build/winit-*", "**/deps/libwinit-*", "**/deps/winit-*"),
    ),
]


def ajustar_teclado(carpeta):
    """Aplica TECLADO a las copias descargadas y borra lo compilado de las que cambiaron."""
    checkouts = cargo_home() / "git" / "checkouts"
    for nombre, patron, viejo, nuevo, compilados in TECLADO:
        cambiados = 0
        vistos = 0
        for archivo in checkouts.glob(patron):
            texto = archivo.read_text(encoding="utf-8")
            if nuevo in texto:
                vistos += 1
                continue
            if texto.count(viejo) != 1:
                continue
            archivo.write_text(texto.replace(viejo, nuevo), encoding="utf-8", newline="")
            cambiados += 1
            vistos += 1
        if not vistos:
            print(f"AVISO: {nombre}: no se encontró el texto a ajustar; se compila sin el ajuste de teclado")
            continue
        borrados = recompilar(carpeta, compilados)
        print(f"Bibliotecas: {nombre} ajustado ({cambiados} copias cambiadas, {borrados} archivos compilados borrados)")


def main():
    carpeta = Path(sys.argv[1]).resolve()
    revs = revisiones_craft_update(carpeta)
    subprocess.run(["cargo", "fetch", "--locked"], cwd=carpeta, check=True)
    ajustar_teclado(carpeta)
    if not revs:
        print("Bibliotecas: el proyecto no usa craft-update")
        return
    for rev in sorted(revs):
        archivos = list((cargo_home() / "git" / "checkouts").glob(f"craft-libs-*/{rev[:7]}/crates/update/src/self_update.rs"))
        if not archivos:
            raise ErrorDeAjuste(f"no se encontró craft-update {rev[:7]} en {cargo_home()}")
        for archivo in archivos:
            print(f"Bibliotecas: craft-update {rev[:7]} {'ajustado' if ajustar(archivo) else 'ya estaba ajustado'}")
    print(f"Bibliotecas: {recompilar(carpeta)} archivos compilados de craft-update borrados")


if __name__ == "__main__":
    try:
        main()
    except ErrorDeAjuste as e:
        print(f"ERROR: {e}\nArtCraft cambió craft-update; hay que actualizar rebrand/bibliotecas.py.", file=sys.stderr)
        sys.exit(1)
