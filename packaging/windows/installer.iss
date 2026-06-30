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

[Code]
var
  AdminPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  AdminPage := CreateInputQueryPage(
    wpSelectTasks,
    'Initialize administrator',
    'Create the first system administrator',
    'This step is optional. If skipped, open http://localhost:8080/setup-admin after launch.'
  );
  AdminPage.Add('Admin username:', False);
  AdminPage.Add('Admin password:', True);
  AdminPage.Add('Confirm password:', True);
  AdminPage.Values[0] := 'sysadmin';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = AdminPage.ID then begin
    if (AdminPage.Values[1] <> '') or (AdminPage.Values[2] <> '') then begin
      if Length(AdminPage.Values[0]) < 4 then begin
        MsgBox('Admin username must be at least 4 characters.', mbError, MB_OK);
        Result := False;
      end else if Length(AdminPage.Values[1]) < 8 then begin
        MsgBox('Admin password must be at least 8 characters.', mbError, MB_OK);
        Result := False;
      end else if AdminPage.Values[1] <> AdminPage.Values[2] then begin
        MsgBox('The two passwords do not match.', mbError, MB_OK);
        Result := False;
      end;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  PasswordFile: string;
  ResultCode: Integer;
begin
  if (CurStep = ssPostInstall) and (not WizardSilent) and (AdminPage.Values[1] <> '') then begin
    PasswordFile := ExpandConstant('{tmp}\km_admin_password.txt');
    SaveStringToFile(PasswordFile, AdminPage.Values[1], False);
    Exec(
      ExpandConstant('{app}\{#MyAppExeName}'),
      'bootstrap-admin --init --username "' + AdminPage.Values[0] + '" --password-file "' + PasswordFile + '" --allow-remote',
      '',
      SW_HIDE,
      ewWaitUntilTerminated,
      ResultCode
    );
    DeleteFile(PasswordFile);
  end;
end;
