; Inno Setup 脚本 — 幼儿园教学管理系统 Windows 安装包
;
; 构建方式（在 Windows 上）：
;   ISCC.exe packaging\windows\installer.iss /DMyAppVersion=3.0.0-beta.1
;
; 前置条件：已完成 PyInstaller onedir 构建（dist\KindergartenManager\）

#ifndef MyAppVersion
#define MyAppVersion "3.0.0-beta.1"
#endif

#define MyAppName     "幼儿园教学管理系统"
#define MyAppExeName  "KindergartenManager.exe"
#define MyAppID       "D4E8F2A1-B3C7-4096-9E5A-2F1D6B8C3A47"
#define SourceDir     "..\..\dist\KindergartenManager"

[Setup]
AppId={{#MyAppID}
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
SetupIconFile=
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
; 要求 Windows 10 及以上（NiceGUI 运行时依赖）
MinVersion=10.0
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "在桌面创建快捷方式"; GroupDescription: "附加快捷方式:"; Flags: unchecked

[Files]
; 拷贝整个 onedir 目录（含所有依赖）
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";              Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}";         Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}";      Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; 安装完成后可选择立即启动
Filename: "{app}\{#MyAppExeName}"; \
  Description: "立即启动 {#MyAppName}"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; 卸载前强制停止进程（防止文件占用）
Filename: "taskkill"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden

[Code]
{ 安装向导欢迎页附加说明 }
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel2.Caption :=
    '即将安装「幼儿园教学管理系统 v{#MyAppVersion}」。' + #13#10 +
    #13#10 +
    '首次启动后，程序将自动：' + #13#10 +
    '  • 在浏览器中打开 http://localhost:8080' + #13#10 +
    '  • 初始化本地 SQLite 数据库' + #13#10 +
    #13#10 +
    '请访问 http://localhost:8080/setup 创建管理员账号。' + #13#10 +
    #13#10 +
    '如需使用云端 MySQL，请在安装目录中创建 .env 文件并配置' + #13#10 +
    'DATABASE_URL 后重启程序。';
end;
