; Instalador .exe de Jacnex Studio: un asistente en español con la marca Jacnex que instala el MSI
; del launcher sin mostrar el asistente de Windows Installer. Lo compila compilar-windows.yml:
;   ISCC /DVersion=0.6.1 /DMsi=<ruta del .msi> /DIcono=<icon.ico> /O<carpeta> jacnex-studio.iss
; El MSI es por usuario (se instala en %LOCALAPPDATA%\Programs\Jacnex Studio), así que no pide
; permisos de administrador. Desinstalar y actualizar siguen a cargo del MSI.

#ifndef Version
  #error Falta /DVersion=<versión>
#endif
#ifndef Msi
  #error Falta /DMsi=<ruta del .msi>
#endif
#ifndef Icono
  #define Icono "..\marca\generado\launcher\icon.ico"
#endif
#define MsiNombre ExtractFileName(Msi)

[Setup]
AppId={{342D912F-E677-5F10-83EC-5BB58B0E85F2}
AppName=Jacnex Studio
AppVersion={#Version}
AppVerName=Jacnex Studio {#Version}
AppPublisher=Jacnex Solutions
AppPublisherURL=https://jacnex.com
AppSupportURL=https://jacnex.com/soporte
VersionInfoCompany=Jacnex Solutions
VersionInfoDescription=Instalador de Jacnex Studio
VersionInfoProductName=Jacnex Studio
VersionInfoVersion={#Version}
OutputBaseFilename=JacnexStudio-Setup
SetupIconFile={#Icono}
WizardStyle=modern
WizardSizePercent=100
WizardImageFile=lateral-100.bmp,lateral-200.bmp
WizardSmallImageFile=icono-100.bmp,icono-200.bmp
WizardImageStretch=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
MinVersion=10.0
CreateAppDir=no
Uninstallable=no
DisableWelcomePage=no
DisableReadyPage=yes
DisableFinishedPage=no
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Messages]
es.WelcomeLabel1=Te damos la bienvenida a Jacnex Studio
es.WelcomeLabel2=Jacnex Studio es la app desde donde instalas, abres y actualizas todas las apps de la Jacnex Suite: Photonex, Lightnex, Vectornex, Filmnex y más.%n%nLa instalación tarda menos de un minuto.
es.FinishedHeadingLabel=Jacnex Studio está listo
es.FinishedLabelNoIcons=Jacnex Studio se instaló correctamente. Desde ahí puedes instalar las apps de la suite.
es.ClickFinish=Haz clic en Finalizar para cerrar el asistente.

[CustomMessages]
es.Escritorio=Crear un acceso directo en el escritorio
es.Instalando=Instalando Jacnex Studio...
es.Abrir=Abrir Jacnex Studio
es.Fallo=No se pudo instalar Jacnex Studio (código %1).%n%nCierra Jacnex Studio si está abierto y vuelve a intentarlo. Si el problema sigue, escríbenos a soporte@jacnex.com.

[Tasks]
Name: "escritorio"; Description: "{cm:Escritorio}"

[Files]
Source: "{#Msi}"; DestDir: "{tmp}"; Flags: deleteafterinstall; AfterInstall: InstalarMsi

[Run]
Filename: "{code:Ejecutable}"; Description: "{cm:Abrir}"; Flags: postinstall nowait skipifsilent skipifdoesntexist

[Code]
function Ejecutable(Param: String): String;
begin
  { Una actualización respeta la carpeta que el usuario eligió antes (la guarda el MSI). }
  if not RegQueryStringValue(HKCU, 'Software\Jacnex\Jacnex Studio', 'InstallDir', Result) then
    Result := ExpandConstant('{localappdata}\Programs\Jacnex Studio');
  Result := AddBackslash(Result) + 'jacnex-studio.exe';
end;

{ Corre el MSI apenas se extrae. Si falla, el asistente lo informa y termina sin instalar. }
procedure InstalarMsi;
var
  Parametros: String;
  Codigo: Integer;
begin
  WizardForm.StatusLabel.Caption := CustomMessage('Instalando');
  WizardForm.ProgressGauge.Style := npbstMarquee;
  Parametros := '/i "' + ExpandConstant('{tmp}\{#MsiNombre}') + '" /qn /norestart INSTALLDESKTOPSHORTCUT=';
  if WizardIsTaskSelected('escritorio') then
    Parametros := Parametros + '1'
  else
    Parametros := Parametros + '0';
  if not Exec(ExpandConstant('{sys}\msiexec.exe'), Parametros, '', SW_HIDE, ewWaitUntilTerminated, Codigo) then
    Codigo := -1;
  WizardForm.ProgressGauge.Style := npbstNormal;
  { 3010 y 1641: instalado, pero Windows pide reiniciar (no debería pasar con este MSI). }
  if (Codigo <> 0) and (Codigo <> 3010) and (Codigo <> 1641) then
    RaiseException(FmtMessage(CustomMessage('Fallo'), [IntToStr(Codigo)]));
end;
