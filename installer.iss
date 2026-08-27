; installer.iss — Script Inno Setup pour l'application desktop "Veille Immobiliere"
; Genere un setup.exe : installe l'app, cree un raccourci Bureau + menu Demarrer,
; et permet une desinstallation propre (y compris les donnees utilisateur en option).
;
; Compilation : "C:\Users\DELL\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer.iss
; Sortie : installer_output\VeilleImmobiliere-Setup.exe

#define MyAppName "Veille Immobiliere"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Al Omrane Analyzer"
#define MyAppExeName "VeilleImmobiliere.exe"
; Resolu a la COMPILATION (sur cette machine) -- different de {%LOCALAPPDATA}
; qui, lui, ne se resout qu'a l'INSTALLATION sur la machine cible et n'est
; donc pas utilisable comme chemin Source (lu ici, au build).
#define LocalAppData GetEnv("LOCALAPPDATA")

[Setup]
AppId={{B4B6E1C1-7F0D-4C3A-9E1E-3A6B6E7C2F41}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=VeilleImmobiliere-Setup
SetupIconFile=static\favicon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Creer une icone sur le Bureau"; GroupDescription: "Icones additionnelles :"

[Files]
Source: "dist\VeilleImmobiliere\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Navigateur Playwright (headless shell, ~270 Mo) requis par le scraping Mubawab --
; PyInstaller n'embarque pas les binaires de navigateur, seulement le code Python.
; desktop.py pointe PLAYWRIGHT_BROWSERS_PATH ici (voir _configure_frozen_playwright_browsers).
Source: "{#LocalAppData}\ms-playwright\chromium_headless_shell-1234\*"; DestDir: "{app}\ms-playwright\chromium_headless_shell-1234"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent

; La base de donnees (%LOCALAPPDATA%\VeilleImmobiliere) n'est PAS supprimee a la
; desinstallation : elle contient les donnees scrapees de l'utilisateur, a
; conserver par defaut en cas de reinstallation/mise a jour.
