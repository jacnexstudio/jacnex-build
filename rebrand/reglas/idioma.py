"""Español como idioma predeterminado de toda la suite, sin quitar los demás idiomas.

Cada app de ArtCraft trae sus traducciones y una opción «Auto / Igual que el sistema» que sigue el
idioma de Windows, con inglés si no lo reconoce. Aquí esa opción pasa a dar español siempre: quien
no toca nada ve la app en español (también las instalaciones que ya existen, que guardaron «auto»),
y quien elige English en Preferencias lo conserva, porque esa elección se guarda aparte.

Layoutnex y Lightnex no tienen «Auto»: guardan el idioma elegido y, sin elección, usan inglés. Ahí
cambia el valor predeterminado y el nombre con el que se guarda, para que las instalaciones que ya
guardaron el inglés por defecto pasen al español; quien elija English después lo conserva.

Photonex y Readnex leen sus catálogos de craft-i18n al compilar (CRAFT_I18N_DIR, lo prepara
compilar-windows.yml); sin ellos solo tendrían inglés.
"""

# Variable para volver al idioma real del sistema (pruebas, capturas en otro idioma).
SALIDA = "JACNEX_IDIOMA_SISTEMA"


def _sistema_es():
    return f'std::env::var_os("{SALIDA}").is_none()'


def aplicar(carpeta, proyecto, parche):
    cambios = REGLAS.get(proyecto)
    if cambios is None:
        raise KeyError(f"sin regla de idioma para {proyecto!r}")
    for ruta, buscar, reemplazo, regex in cambios:
        parche(carpeta / ruta, buscar, reemplazo, regex=regex)


REGLAS = {
    "launcher": [
        ("crates/ui-egui/src/i18n/detect.rs",
         "let locales: Vec<String> = sys_locale::get_locales().collect();",
         f'let locales: Vec<String> = if {_sistema_es()} {{ vec!["es".to_owned()] }} else {{ sys_locale::get_locales().collect() }};',
         False),
    ],
    "photocraft": [
        ("crates/ui-egui/src/i18n/system.rs",
         "std::panic::catch_unwind(|| bounded_tags(sys_locale::get_locales())).unwrap_or_default()",
         f'if {_sistema_es()} {{ return bounded_tags(["es".to_owned()]); }}\n'
         "    std::panic::catch_unwind(|| bounded_tags(sys_locale::get_locales())).unwrap_or_default()",
         False),
    ],
    "pdfcraft": [
        ("crates/ui-egui/src/i18n.rs",
         "let tags: Vec<String> = sys_locale::get_locales().collect();",
         f'let tags: Vec<String> = if {_sistema_es()} {{ vec!["es".to_owned()] }} else {{ sys_locale::get_locales().collect() }};',
         False),
    ],
    "filmcraft": [
        ("apps/filmcraft/src/main.rs",
         "app.hooks.system_languages = Some(Box::new(|| sys_locale::get_locales().collect()));",
         "app.hooks.system_languages = Some(Box::new(|| {\n"
         f'            if {_sistema_es()} {{ vec!["es".to_owned()] }} else {{ sys_locale::get_locales().collect() }}\n'
         "        }));",
         False),
    ],
    "vectorcraft": [
        ("crates/ui-egui/src/i18n.rs",
         r"(#\[cfg\(target_os = \"windows\"\)\]\nfn windows_locale\(\) -> Option<String> \{\n)",
         rf'\g<1>    if {_sistema_es()} {{\n        return Some("es-PE".to_owned());\n    }}\n',
         True),
    ],
    "effectcraft": [
        ("crates/ui-egui/src/i18n.rs",
         "supported(sys_locale::get_locale().as_deref())",
         f'supported(if {_sistema_es()} {{ Some("es".to_owned()) }} else {{ sys_locale::get_locale() }}.as_deref())',
         False),
    ],
    "lightcraft": [
        ("crates/ui-egui/src/i18n.rs",
         "        .or_else(|| DEFAULT_LANGUAGE.with(std::cell::Cell::get))\n        .unwrap_or(Locale::En)",
         "        .or_else(|| DEFAULT_LANGUAGE.with(std::cell::Cell::get))\n        .unwrap_or(Locale::Es)",
         False),
        ("crates/ui-egui/src/state.rs",
         '    #[serde(default = "crate::i18n::default_language")]\n    pub language: crate::i18n::Locale,',
         '    #[serde(default = "crate::i18n::default_language", rename = "idiomaJacnex")]\n    pub language: crate::i18n::Locale,',
         False),
    ],
    "designcraft": [
        ("crates/ui-egui/src/state.rs",
         "    /// Preferences › General › Interface Language: supported codes are listed in `i18n::LANGUAGES`.\n"
         "    pub language: String,",
         "    /// Preferences › General › Interface Language: supported codes are listed in `i18n::LANGUAGES`.\n"
         '    #[serde(rename = "idiomaJacnex")]\n'
         "    pub language: String,",
         False),
        ("crates/ui-egui/src/state.rs",
         "            language: String::new(),\n            flattener: String::new(),",
         '            language: "es".into(),\n            flattener: String::new(),',
         False),
    ],
}
