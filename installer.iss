; installer.iss — Brixta Tally Sync Agent (SYSTEM tasks)
#define MyAppName "Brixta Tally Sync Agent"
#define MyAppVersion "1.0.3"
#define InstallRoot "C:\BrixtaTallyAgent"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Brixta
DefaultDirName={code:GetInstallDir}
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir=dist-installer
OutputBaseFilename=BrixtaSetup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
WizardStyle=modern
CloseApplications=yes
RestartIfNeededByRun=no
UninstallDisplayIcon={app}\app.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; --------- ensure writable folders exist ----------
[Dirs]
Name: "{app}"; Permissions: users-full
Name: "{app}\logs"; Permissions: users-full
Name: "{app}\exports"; Permissions: users-full
Name: "{app}\parsed_exports"; Permissions: users-full

; --------- files from PyInstaller dist -------------
[Files]
Source: "dist\app.exe"; DestDir: "{app}"; Flags: ignoreversion replacesameversion
Source: "dist\xmlRead2.exe"; DestDir: "{app}"; Flags: ignoreversion replacesameversion
Source: "config.json.example"; DestDir: "{app}"; DestName: "config.json"; Flags: onlyifdoesntexist

; --------- stop old tasks / processes before overwrite ----------
[Run]
Filename: "schtasks.exe"; Parameters: "/End /TN ""Brixta Receiver"""; Flags: runhidden; StatusMsg: "Stopping old task Brixta Receiver..."; Check: TaskExists('Brixta Receiver')
Filename: "schtasks.exe"; Parameters: "/End /TN ""Brixta Data Pump"""; Flags: runhidden; StatusMsg: "Stopping old task Brixta Data Pump..."; Check: TaskExists('Brixta Data Pump')
Filename: "schtasks.exe"; Parameters: "/Delete /F /TN ""Brixta Receiver"""; Flags: runhidden; Check: TaskExists('Brixta Receiver')
Filename: "schtasks.exe"; Parameters: "/Delete /F /TN ""Brixta Data Pump"""; Flags: runhidden; Check: TaskExists('Brixta Data Pump')
Filename: "taskkill.exe"; Parameters: "/IM app.exe /F"; Flags: runhidden skipifsilent
Filename: "taskkill.exe"; Parameters: "/IM xmlRead2.exe /F"; Flags: runhidden skipifsilent

; --------- create new scheduled tasks (run as SYSTEM) ----------
; Receiver = Flask listener: start on system boot, highest privileges
[Run]
Filename: "schtasks.exe"; \
  Parameters: "/Create /F /RL HIGHEST /SC ONSTART /TN ""Brixta Receiver"" /TR ""\""{app}\app.exe\"""" /RU SYSTEM"; \
  Flags: runhidden; StatusMsg: "Registering task: Brixta Receiver"

; Data Pump = xmlRead2: every 2 minutes, SYSTEM
[Run]
Filename: "schtasks.exe"; \
  Parameters: "/Create /F /RL HIGHEST /SC MINUTE /MO 2 /TN ""Brixta Data Pump"" /TR ""\""{app}\xmlRead2.exe\"""" /RU SYSTEM"; \
  Flags: runhidden; StatusMsg: "Registering task: Brixta Data Pump"

; --------- kick them once now ----------
[Run]
Filename: "schtasks.exe"; Parameters: "/Run /TN ""Brixta Receiver"""; Flags: runhidden
Filename: "schtasks.exe"; Parameters: "/Run /TN ""Brixta Data Pump"""; Flags: runhidden

; --------- uninstall cleanup ----------
[UninstallRun]
Filename: "schtasks.exe"; Parameters: "/End /TN ""Brixta Receiver"""; Flags: runhidden
Filename: "schtasks.exe"; Parameters: "/Delete /F /TN ""Brixta Receiver"""; Flags: runhidden
Filename: "schtasks.exe"; Parameters: "/End /TN ""Brixta Data Pump"""; Flags: runhidden
Filename: "schtasks.exe"; Parameters: "/Delete /F /TN ""Brixta Data Pump"""; Flags: runhidden

[Code]
function TaskExists(const TaskName: string): Boolean;
var
  ResultCode: Integer;
begin
  Result := (ShellExec('', 'schtasks.exe',
    '/Query /TN "' + TaskName + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)) and
    (ResultCode = 0);
end;

function GetInstallDir(Param: string): string;
begin
  { Allow override with /DIR="..." if ever needed, else use C:\BrixtaTallyAgent }
  Result := ExpandConstant('{param:InstallDir|' + '{#InstallRoot}' + '}');
end;
