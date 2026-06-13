; Inno Setup script — 幼儿园教学管理系统 Windows Installer
;
; Build (from repo root on Windows):
;   ISCC.exe packaging\windows\installer.iss /DMyAppVersion=3.0.0-beta.1
;
; Prerequisite: PyInstaller onedir build must be done first (dist\KindergartenManager\)

#ifndef MyAppVersion
#define MyAppVersion "3.0.0-beta.1"
#endif

#define MyAppName     "幼儿园教学管理系统"
#define MyAppExeName  "KindergartenManager.exe"
#define SourceDir     "..\..\dist\KindergartenManager"

[Setup]
; AppId GUID: {{...} 语法中 {{ 转义为 {, 最终 AppId = {D4E8F2A1-B3C7-4096-9E5A-2F1D6B8C3A47}
AppId={{D4E8F2A1-B3C7-4096-9E5A-2F1D6B8C3A47}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=ywyz
AppPublisherURL=https://github.com/ywyz/kindergartenManager
AppSupportURL=https://github.com/ywyz/kindergartenManager/issues
DefaultDirName={autopf}\KindergartenManager
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=KindergartenManager-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0
UninstallDisplayIcon={app}\{#MyAppExeName}

; Use bundled English messages (ChineseSimplified.isl is not included in Inno Setup by default)
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden
