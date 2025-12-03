; Inno Setup Script for Healthcare AI Assistant
; Compile with: iscc installer.iss

#define AppName "Healthcare AI Assistant"
#define AppVersion "1.0.0"
#define AppPublisher "Healthcare AI Project"
#define AppURL "https://github.com/JesseBrown1980/AI-healthCare-project"
#define AppExeName "HealthcareAIAssistant.exe"
#define OutputDir "dist"
#define SourceDir ".."

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile={#SourceDir}\LICENSE
OutputDir={#OutputDir}
OutputBaseFilename=HealthcareAIAssistant-Setup-{#AppVersion}
SetupIconFile={#SourceDir}\windows_build\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode
Name: "startup"; Description: "Start {#AppName} on Windows startup"; GroupDescription: "Startup Options"; Flags: unchecked

[Files]
Source: "{#SourceDir}\dist\HealthcareAIAssistant.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\windows_build\*"; DestDir: "{app}\windows_build"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\alembic\*"; DestDir: "{app}\alembic"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\alembic.ini"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\.env.example"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Windows\Start Menu\Programs\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"""; Tasks: startup; Flags: uninsdeletevalue

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create .env file if it doesn't exist
    if not FileExists(ExpandConstant('{app}\.env')) then
    begin
      SaveStringToFile(ExpandConstant('{app}\.env'), '# Healthcare AI Assistant Configuration' + #13#10, False);
    end;
  end;
end;

