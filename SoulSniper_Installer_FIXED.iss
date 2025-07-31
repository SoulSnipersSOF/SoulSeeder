[Setup]
; Basic Information
AppName=SoulSniper's SOF Seeder
AppVersion=1.0.0
AppPublisher=SoulSniper Gaming Community
AppPublisherURL=https://soulsniper.com
AppSupportURL=https://soulsniper.com/support
AppUpdatesURL=https://soulsniper.com/updates
DefaultDirName={autopf}\SoulSniperSOFSeeder
DefaultGroupName=SoulSniper SOF Seeder
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=SoulSniper_SOF_Seeder_Setup
SetupIconFile=SoulSniper_Logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Uninstall
UninstallDisplayIcon={app}\SoulSniper_SOF_Seeder.exe
UninstallDisplayName=SoulSniper's SOF Seeder
CreateUninstallRegKey=yes

; Version Info
VersionInfoVersion=1.0.0.0
VersionInfoCompany=SoulSniper Gaming Community
VersionInfoDescription=Automatic Hell Let Loose Server Seeder
VersionInfoCopyright=Copyright (C) 2025 SoulSniper Gaming Community
VersionInfoProductName=SoulSniper's SOF Seeder
VersionInfoProductVersion=1.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; OnlyBelowVersion: 6.1

[Files]
; Main application
Source: "dist\SoulSniper_SOF_Seeder.exe"; DestDir: "{app}"; Flags: ignoreversion
; Support files
Source: "CreateTasks.xml"; DestDir: "{app}"; Flags: ignoreversion
Source: "Uninstall.ps1"; DestDir: "{app}"; Flags: ignoreversion
; Optional files (only if they exist)
Source: "SoulSniper_Logo.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "soulsniper_icon.png"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "README.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist isreadme

[Icons]
Name: "{group}\SoulSniper's SOF Seeder"; Filename: "{app}\SoulSniper_SOF_Seeder.exe"
Name: "{group}\Uninstall SoulSniper's SOF Seeder"; Filename: "{uninstallexe}"
Name: "{autodesktop}\SoulSniper's SOF Seeder"; Filename: "{app}\SoulSniper_SOF_Seeder.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\SoulSniper's SOF Seeder"; Filename: "{app}\SoulSniper_SOF_Seeder.exe"; Tasks: quicklaunchicon

[Run]
; Run the application after installation and let it do first-run setup
Filename: "{app}\SoulSniper_SOF_Seeder.exe"; Description: "{cm:LaunchProgram,SoulSniper's SOF Seeder}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Run uninstall script to clean up scheduled tasks
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\Uninstall.ps1"""; Flags: runhidden waituntilterminated

[Code]
// Custom installation messages and logic
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure InitializeWizard();
begin
  // Custom welcome message
  WizardForm.WelcomeLabel2.Caption := 
    'This will install SoulSniper''s SOF Seeder on your computer.' + #13#10 + #13#10 +
    'This application automatically seeds Hell Let Loose servers daily at 7 AM EST.' + #13#10 + #13#10 +
    'Features:' + #13#10 +
    '• Automatic daily server seeding with wake-from-sleep' + #13#10 +
    '• Manual server joining options' + #13#10 +
    '• Smart player count monitoring via Battlemetrics' + #13#10 +
    '• Automatic HLL splash screen handling' + #13#10 +
    '• Works when logged out or computer is sleeping' + #13#10 +
    '• Zero configuration required' + #13#10 + #13#10 +
    'Administrator privileges are required for full automation features.' + #13#10 + #13#10 +
    'Click Next to continue, or Cancel to exit Setup.';
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  // Skip components page since we don't have optional components
  if PageID = wpSelectComponents then
    Result := True;
end;

// Check if Steam is installed
function IsSteamInstalled(): Boolean;
var
  SteamPath: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath', SteamPath) or
            RegQueryStringValue(HKLM, 'SOFTWARE\Valve\Steam', 'InstallPath', SteamPath) or
            RegQueryStringValue(HKCU, 'SOFTWARE\Valve\Steam', 'SteamPath', SteamPath);
end;

// Check if Hell Let Loose is installed
function IsHLLInstalled(): Boolean;
var
  SteamPath: String;
  HLLPath: String;
begin
  Result := False;
  if IsSteamInstalled() then
  begin
    if RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath', SteamPath) or
       RegQueryStringValue(HKLM, 'SOFTWARE\Valve\Steam', 'InstallPath', SteamPath) then
    begin
      HLLPath := SteamPath + '\steamapps\common\Hell Let Loose';
      Result := DirExists(HLLPath);
    end;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  
  // Check requirements on ready page
  if CurPageID = wpReady then
  begin
    if not IsSteamInstalled() then
    begin
      MsgBox('Warning: Steam is not detected on this system.' + #13#10 + #13#10 +
             'SoulSniper''s SOF Seeder requires Steam and Hell Let Loose to function properly.' + #13#10 + #13#10 +
             'Please install Steam and Hell Let Loose before using this application.', 
             mbInformation, MB_OK);
    end
    else if not IsHLLInstalled() then
    begin
      MsgBox('Warning: Hell Let Loose is not detected in your Steam library.' + #13#10 + #13#10 +
             'Please install Hell Let Loose from Steam before using this application.' + #13#10 + #13#10 +
             'The seeder can still be installed and will work once HLL is installed.', 
             mbInformation, MB_OK);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Skip task creation during install - let the app handle it on first run
    // This avoids PowerShell compatibility issues during installation
  end;
end;

// Custom finish page
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
  begin
    WizardForm.FinishedLabel.Caption :=
      'SoulSniper''s SOF Seeder has been successfully installed!' + #13#10 + #13#10 +
      'Important Notes:' + #13#10 +
      '• The app will automatically set up daily seeding at 7 AM EST' + #13#10 +
      '• Your computer will wake from sleep for seeding' + #13#10 +
      '• Manual server joining works anytime' + #13#10 +
      '• App will request admin privileges when needed' + #13#10 + #13#10 +
      'The application will now run and complete the setup process.' + #13#10 + #13#10 +
      'Thank you for helping seed the SoulSniper servers!';
  end;
end;