#define MyAppName "JARVIS"
#define MyAppVersion "2.4.0"
#define MyAppPublisher "nezerrucyk-alt"
#define MyAppURL "https://nezerrucyk-alt.github.io/jarvis-ai-assistant/"
#define MyAppExeName "JARVIS.exe"

[Setup]
AppId={{B7E4A2B0-6C1D-4F2E-9A77-3F5C1D8E4A21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}issues
AppUpdatesURL=https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases
VersionInfoVersion=2.4.0.0
VersionInfoProductName=JARVIS
VersionInfoProductVersion=2.4.0
VersionInfoCompany={#MyAppPublisher}
DefaultDirName={autopf}\JARVIS
DefaultGroupName=JARVIS
AllowNoIcons=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=JARVIS-Setup
SetupIconFile=..\assets\jarvis.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes
RestartApplications=no
DisableWelcomePage=no

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "payload\JARVIS-Windows.exe"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\JARVIS"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\JARVIS"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,JARVIS}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
