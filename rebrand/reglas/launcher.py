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
    instalacion_como_adobe(carpeta, parche)


# --- Instalación como Creative Cloud --------------------------------------------------------------
# En Windows las apps se instalan desde su zip portable en %LOCALAPPDATA%\Jacnex Studio\apps:
# sin permiso de administrador, sin la ventana de Windows Installer y sin reiniciar al desinstalar.
# Cada app instalada recibe su acceso directo en el menú Inicio, que se borra al desinstalarla.
# Las que ya estaban instaladas con el MSI se siguen actualizando con el MSI.

MODULO_ACCESOS = r'''//! Accesos directos del menú Inicio para las apps que instala el launcher (agregado por Jacnex).

use std::path::{Path, PathBuf};

use jacnex_studio_core::CraftApp;

fn acceso(app: &CraftApp) -> Option<PathBuf> {
    dirs::data_dir().map(|d| d.join(r"Microsoft\Windows\Start Menu\Programs").join(format!("{}.lnk", app.name)))
}

fn literal(texto: &str) -> String {
    format!("'{}'", texto.replace('\'', "''"))
}

/// Crea (o renueva) el acceso directo de `app` hacia `exe`. Un fallo no detiene la instalación.
pub fn crear(app: &CraftApp, exe: &Path) {
    let (Some(lnk), Some(carpeta)) = (acceso(app), exe.parent()) else { return };
    let script = format!(
        "$a = (New-Object -ComObject WScript.Shell).CreateShortcut({}); $a.TargetPath = {}; $a.WorkingDirectory = {}; $a.IconLocation = {}; $a.Save()",
        literal(&lnk.to_string_lossy()),
        literal(&exe.to_string_lossy()),
        literal(&carpeta.to_string_lossy()),
        literal(&format!("{},0", exe.to_string_lossy())),
    );
    let estado = crate::process::command("powershell.exe")
        .args(["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", &script])
        .status();
    if !estado.is_ok_and(|e| e.success()) {
        log::warn!("couldn't create the Start menu shortcut for {}", app.name);
    }
}

/// Borra el acceso directo de `app`, si lo hay.
pub fn borrar(app: &CraftApp) {
    if let Some(lnk) = acceso(app) {
        let _ = std::fs::remove_file(lnk);
    }
}
'''


def instalacion_como_adobe(carpeta, parche):
    # Primero el zip portable, después el MSI.
    parche(carpeta / "crates/core/src/platform.rs",
           r"(pub fn default_kinds\(self\)[^{]*\{\s*match self\.os \{\s*Os::Windows => &\[)PackageKind::Msi, PackageKind::PortableZip\]",
           r"\g<1>PackageKind::PortableZip, PackageKind::Msi]", regex=True)
    parche(carpeta / "crates/native/src/install.rs",
           "return vec![PackageKind::Msi, PackageKind::PortableZip];",
           "return vec![PackageKind::PortableZip, PackageKind::Msi];")
    # Acceso directo al instalar y al desinstalar.
    instalar = carpeta / "crates/native/src/install.rs"
    parche(instalar,
           r"(crate::portable::install\(app, .*?\}\)\s*)\.map\(Some\)",
           r"\g<1>.map(|record| {" "\n"
           r"                crate::jacnex_accesos::crear(app, &record.path);" "\n"
           r"                Some(record)" "\n"
           r"            })",
           regex=True)
    parche(instalar,
           r"crate::portable::remove\(app, (record\.ok_or\([^;]*?\)\?)\)",
           r"crate::portable::remove(app, \g<1>).inspect(|()| crate::jacnex_accesos::borrar(app))",
           regex=True)
    # Siempre así en Windows, como Adobe: sin la opción "Instalar apps nuevas como" (al abrir
    # Configuración guardaba "MSI" aunque nadie lo eligiera) y sin hacer caso a esa preferencia.
    # Las apps ya instaladas con el MSI se siguen actualizando con el MSI.
    parche(instalar,
           r"(pub fn choose_kinds\(app: &CraftApp, existing: Option<&Installed>, record: Option<&Record>, "
           r"preferred: &\[PackageKind\]\) -> Vec<PackageKind> \{\n)",
           r"\g<1>    #[cfg(windows)]" "\n"
           r"    let preferred: &[PackageKind] = {" "\n"
           r"        let _ = preferred;" "\n"
           r"        &[]" "\n"
           r"    };" "\n",
           regex=True)
    parche(carpeta / "crates/ui-egui/src/settings_dialog.rs",
           r'if self\.platform\.is_some_and\(\|p\| p\.os == Os::Windows\) \{(\s*sheet::panel\(ui, tl!\("Installing on Windows"\))',
           r"if false {\g<1>",
           regex=True)
    (carpeta / "crates/native/src/jacnex_accesos.rs").write_text(MODULO_ACCESOS, encoding="utf-8", newline="\n")
    parche(carpeta / "crates/native/src/lib.rs", "pub mod install;\n", "pub mod install;\n#[cfg(windows)]\nmod jacnex_accesos;\n")
