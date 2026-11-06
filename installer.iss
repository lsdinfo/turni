#define AppName "Moreno - Turni"
#define AppVersion "3.0"

[Setup]
AppId={{6F1B3C52-4D1E-4B7A-9C3A-5A0E2B7D1A10}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Moreno
DefaultDirName={autopf}\Moreno
DefaultGroupName=Moreno
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer
OutputBaseFilename=Setup_Moreno_{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no
UninstallDisplayIcon={app}\Turni.exe

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea un collegamento sul desktop"; GroupDescription: "Collegamenti:"

[Files]
Source: "dist\Turni\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "installed.flag"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Moreno - Turni"; Filename: "{app}\Turni.exe"
Name: "{autodesktop}\Moreno - Turni"; Filename: "{app}\Turni.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Turni.exe"; Description: "Avvia Moreno"; Flags: nowait postinstall skipifsilent
