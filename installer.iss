; installer.iss
[Setup]
AppName=Brixta Tally Sync Agent
AppVersion=1.0.0
DefaultDirName={pf}\BrixtaTallyAgent
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir=dist-installer
OutputBaseFilename=BrixtaSetup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\app.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\xmlRead2.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json.example"; DestDir: "{app}"; DestName: "config.json"; Flags: onlyifdoesntexist

[Run]
; Start receiver after install (non-blocking)
Filename: "{app}\app.exe"; Flags: nowait postinstall skipifsilent

[Tasks]
Name: "CreateTasks"; Description: "Register background tasks"; Flags: checkedonce

[Run]
; Receiver: run on system startup
Filename: "schtasks.exe"; \
  Parameters: "/Create /TN ""BrixtaReceiver"" /SC ONSTART /TR ""\""{app}\app.exe\"" "" /RL HIGHEST /F"; \
  StatusMsg: "Creating Receiver task..."; Flags: runascurrentuser runhidden

; DataPump: run every 5 minutes
Filename: "schtasks.exe"; \
  Parameters: "/Create /TN ""BrixtaDataPump"" /SC MINUTE /MO 5 /TR ""\""{app}\xmlRead2.exe\"" "" /RL HIGHEST /F"; \
  StatusMsg: "Creating DataPump task..."; Flags: runascurrentuser runhidden

; Kick DataPump once immediately
Filename: "{app}\xmlRead2.exe"; Flags: nowait runhidden
