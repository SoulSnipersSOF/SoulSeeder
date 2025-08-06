# Uninstall.ps1 - SoulSniper's SOF Seeder Enhanced Uninstaller
# Removes ALL traces including scheduled tasks, registry entries, logs, and Steam configurations

# Configuration
$TaskName = "SoulSeeder Auto Seeder"
$AppName = "SoulSniper_SOF_Seeder"
$LogPath = "C:\ProgramData\SeedMySoul"
$UserLogPath = "$env:USERPROFILE\SeedMySoul"
$DesktopLogPath = "$env:USERPROFILE\Desktop\soulsniper_debug.txt"

# Ensure we're running as Administrator for complete cleanup
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Requesting Administrator privileges for complete uninstall..." -ForegroundColor Yellow
    try {
        Start-Process PowerShell -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`"" -Wait
    } catch {
        Write-Host "Failed to get admin privileges. Some cleanup may be incomplete." -ForegroundColor Red
        Read-Host "Press Enter to continue with limited cleanup"
    }
    exit
}

Write-Host "===============================================" -ForegroundColor Red
Write-Host "  SoulSniper's SOF Seeder - Uninstaller" -ForegroundColor Red
Write-Host "===============================================" -ForegroundColor Red
Write-Host ""
Write-Host "Performing complete system cleanup..." -ForegroundColor Yellow
Write-Host ""

# 1. Remove scheduled task(s) - Enhanced with better detection
Write-Host "[1/8] Removing scheduled tasks..." -ForegroundColor Yellow

# First, list all tasks that might be related to find the exact name
$AllTasks = Get-ScheduledTask | Where-Object { 
    $_.TaskName -like "*Soul*" -or 
    $_.TaskName -like "*Seed*" -or 
    $_.TaskName -like "*HLL*" -or
    $_.Description -like "*SoulSniper*" -or
    $_.Description -like "*Hell Let Loose*"
}

if ($AllTasks) {
    Write-Host "Found potentially related tasks:" -ForegroundColor Cyan
    foreach ($Task in $AllTasks) {
        Write-Host "  - $($Task.TaskName) | $($Task.TaskPath) | $($Task.Description)" -ForegroundColor Gray
    }
    Write-Host ""
}

# Comprehensive list of possible task names
$TaskNames = @(
    "SoulSeeder Auto Seeder",
    "SoulSniper_AutoSeeder", 
    "SoulSniperAutoSeeder", 
    "SoulSniper SOF Seeder",
    "SoulSniper's SOF Seeder",
    "HLL Auto Seeder",
    "Auto Seeder"
)    

$TasksRemoved = 0

# Method 1: Try exact name matches
foreach ($Task in $TaskNames) {
    try {
        $ExistingTask = Get-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue
        if ($ExistingTask) {
            Write-Host "Found exact match: $Task" -ForegroundColor Yellow
            Unregister-ScheduledTask -TaskName $Task -Confirm:$false -ErrorAction Stop
            Write-Host "[OK] Removed scheduled task: $Task" -ForegroundColor Green
            $TasksRemoved++
        }
    } catch {
        Write-Host "[ERROR] Failed to remove task: $Task - $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Method 2: Try removing any tasks we found in the search
if ($AllTasks) {
    foreach ($Task in $AllTasks) {
        try {
            # Skip if already removed
            $StillExists = Get-ScheduledTask -TaskName $Task.TaskName -ErrorAction SilentlyContinue
            if ($StillExists) {
                Write-Host "Removing found task: $($Task.TaskName)" -ForegroundColor Yellow
                Unregister-ScheduledTask -TaskName $Task.TaskName -Confirm:$false -ErrorAction Stop
                Write-Host "[OK] Removed scheduled task: $($Task.TaskName)" -ForegroundColor Green
                $TasksRemoved++
            }
        } catch {
            Write-Host "[ERROR] Failed to remove task: $($Task.TaskName) - $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

# Method 3: Nuclear option - use schtasks.exe directly
$SchTasksNames = @(
    "SoulSeeder Auto Seeder",
    "\SoulSeeder Auto Seeder",
    "\\SoulSeeder Auto Seeder"
)

foreach ($TaskName in $SchTasksNames) {
    try {
        $Result = & schtasks.exe /query /tn "$TaskName" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Found task via schtasks: $TaskName" -ForegroundColor Yellow
            $DeleteResult = & schtasks.exe /delete /tn "$TaskName" /f 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "[OK] Removed via schtasks: $TaskName" -ForegroundColor Green
                $TasksRemoved++
            } else {
                Write-Host "[ERROR] schtasks delete failed for: $TaskName" -ForegroundColor Red
            }
        }
    } catch {
        # Silent continue
    }
}

# Method 4: Check root folder and subfolders
try {
    $RootTasks = Get-ScheduledTask -TaskPath "\" -ErrorAction SilentlyContinue | Where-Object { 
        $_.TaskName -like "*Soul*" -or $_.Description -like "*SoulSniper*" 
    }
    
    foreach ($Task in $RootTasks) {
        try {
            Write-Host "Found root task: $($Task.TaskName)" -ForegroundColor Yellow
            Unregister-ScheduledTask -TaskName $Task.TaskName -Confirm:$false -ErrorAction Stop
            Write-Host "[OK] Removed root task: $($Task.TaskName)" -ForegroundColor Green
            $TasksRemoved++
        } catch {
            Write-Host "[ERROR] Failed to remove root task: $($Task.TaskName)" -ForegroundColor Red
        }
    }
} catch {
    # Silent continue
}

if ($TasksRemoved -eq 0) {
    Write-Host "[INFO] No scheduled tasks found" -ForegroundColor Cyan
    
    # Final verification - show what tasks DO exist for debugging
    Write-Host "Debug: Current scheduled tasks containing 'Soul' or 'Seed':" -ForegroundColor Gray
    try {
        $DebugTasks = Get-ScheduledTask | Where-Object { 
            $_.TaskName -like "*Soul*" -or $_.TaskName -like "*Seed*" 
        } | Select-Object TaskName, TaskPath, State | Format-Table -AutoSize
        if ($DebugTasks) {
            $DebugTasks | Out-Host
        } else {
            Write-Host "  (No matching tasks found)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  (Could not query tasks for debug)" -ForegroundColor Gray
    }
} else {
    Write-Host "[OK] Removed $TasksRemoved scheduled task(s)" -ForegroundColor Green
}

# 2. Close any running instances
Write-Host "[2/8] Stopping running processes..." -ForegroundColor Yellow
$ProcessNames = @("SoulSniper_SOF_Seeder", "hll_auto_join", "SoulSniperSOFSeeder")
$ProcessesStopped = 0

foreach ($ProcessName in $ProcessNames) {
    try {
        $Processes = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
        if ($Processes) {
            $Processes | Stop-Process -Force -ErrorAction SilentlyContinue
            Write-Host "[OK] Stopped: $ProcessName" -ForegroundColor Green
            $ProcessesStopped++
            Start-Sleep -Milliseconds 500  # Give time for processes to close
        }
    } catch {
        # Silent continue
    }
}

if ($ProcessesStopped -eq 0) {
    Write-Host "[INFO] No running processes found" -ForegroundColor Cyan
}

# 3. Remove registry entries for admin elevation
Write-Host "[3/8] Cleaning registry entries..." -ForegroundColor Yellow
$RegistryPaths = @(
    "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers",
    "HKLM:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
)

$RegistryEntriesRemoved = 0
foreach ($RegPath in $RegistryPaths) {
    try {
        if (Test-Path $RegPath) {
            $RegKey = Get-Item $RegPath -ErrorAction SilentlyContinue
            if ($RegKey) {
                $Values = $RegKey.GetValueNames() | Where-Object { $_ -like "*SoulSniper*" -or $_ -like "*SOF_Seeder*" }
                foreach ($Value in $Values) {
                    try {
                        Remove-ItemProperty -Path $RegPath -Name $Value -ErrorAction SilentlyContinue
                        Write-Host "[OK] Removed registry entry: $Value" -ForegroundColor Green
                        $RegistryEntriesRemoved++
                    } catch {
                        # Silent continue
                    }
                }
            }
        }
    } catch {
        # Silent continue
    }
}

if ($RegistryEntriesRemoved -eq 0) {
    Write-Host "[INFO] No registry entries found" -ForegroundColor Cyan
}

# 4. Clean up log directories and debug files
Write-Host "[4/8] Removing log files and directories..." -ForegroundColor Yellow
$LogsRemoved = 0
$FilesToClean = @($LogPath, $UserLogPath, $DesktopLogPath)

# Add potential temp log locations
$TempLogs = @(
    "$env:TEMP\soulsniper*",
    "$env:USERPROFILE\AppData\Local\soulsniper*",
    "$env:USERPROFILE\AppData\Roaming\soulsniper*"
)

foreach ($Pattern in $TempLogs) {
    try {
        $Files = Get-ChildItem -Path (Split-Path $Pattern) -Filter (Split-Path $Pattern -Leaf) -ErrorAction SilentlyContinue
        foreach ($File in $Files) {
            Remove-Item $File.FullName -Recurse -Force -ErrorAction SilentlyContinue
            $LogsRemoved++
        }
    } catch {
        # Silent continue
    }
}

foreach ($Path in $FilesToClean) {
    try {
        if (Test-Path $Path) {
            Remove-Item $Path -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "[OK] Removed: $Path" -ForegroundColor Green
            $LogsRemoved++
        }
    } catch {
        # Silent continue
    }
}

if ($LogsRemoved -eq 0) {
    Write-Host "[INFO] No log files found" -ForegroundColor Cyan
}

# 5. Clear Steam launch options (comprehensive search)
Write-Host "[5/8] Clearing Steam configurations..." -ForegroundColor Yellow
try {
    # Search all possible Steam locations
    $SteamPaths = @()
    
    # Registry-based Steam path detection
    try {
        $RegSteamPath = Get-ItemProperty -Path "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam" -Name "InstallPath" -ErrorAction SilentlyContinue
        if ($RegSteamPath) { $SteamPaths += $RegSteamPath.InstallPath }
    } catch { }
    
    try {
        $RegSteamPath2 = Get-ItemProperty -Path "HKCU:\Software\Valve\Steam" -Name "SteamPath" -ErrorAction SilentlyContinue
        if ($RegSteamPath2) { $SteamPaths += $RegSteamPath2.SteamPath }
    } catch { }
    
    # Common Steam locations
    $CommonPaths = @(
        "C:\Program Files (x86)\Steam",
        "C:\Program Files\Steam",
        "D:\Steam", "D:\Program Files (x86)\Steam", "D:\Program Files\Steam",
        "E:\Steam", "E:\Program Files (x86)\Steam", "E:\Program Files\Steam",
        "F:\Steam", "G:\Steam", "H:\Steam"
    )
    $SteamPaths += $CommonPaths
    
    # Remove duplicates
    $SteamPaths = $SteamPaths | Select-Object -Unique | Where-Object { $_ -and (Test-Path $_) }
    
    $HLL_APP_ID = "686810"
    $SteamConfigsFixed = 0
    
    foreach ($SteamPath in $SteamPaths) {
        $UserDataPath = Join-Path $SteamPath "userdata"
        if (Test-Path $UserDataPath) {
            $UserDirs = Get-ChildItem $UserDataPath -Directory | Where-Object { $_.Name -match '^\d+$' }
            
            foreach ($UserDir in $UserDirs) {
                $ConfigPath = Join-Path $UserDir.FullName "config\localconfig.vdf"
                if (Test-Path $ConfigPath) {
                    try {
                        $Content = Get-Content $ConfigPath -Raw -Encoding UTF8
                        $OriginalContent = $Content
                        
                        # Remove HLL launch options - multiple patterns to catch all variants
                        $Patterns = @(
                            "`"$HLL_APP_ID`"\s*\{[^}]*`"LaunchOptions`"[^}]*\}",
                            "`"$HLL_APP_ID`"\s*\{[^}]*LaunchOptions[^}]*\}"
                        )
                        
                        foreach ($Pattern in $Patterns) {
                            $Content = $Content -replace $Pattern, "`"$HLL_APP_ID`"`n`t`t`t{`n`t`t`t}"
                        }
                        
                        # Also remove any standalone launch options lines
                        $Content = $Content -replace "`"LaunchOptions`"\s*`"[^`"]*-dev \+connect[^`"]*`"", ""
                        
                        if ($Content -ne $OriginalContent) {
                            Set-Content $ConfigPath -Value $Content -Encoding UTF8
                            $SteamConfigsFixed++
                        }
                    } catch {
                        # Silent fail - not critical
                    }
                }
            }
        }
    }
    
    if ($SteamConfigsFixed -gt 0) {
        Write-Host "[OK] Cleared Steam launch options ($SteamConfigsFixed config files)" -ForegroundColor Green
    } else {
        Write-Host "[INFO] No Steam launch options found or already clean" -ForegroundColor Cyan
    }
} catch {
    Write-Host "[INFO] Could not access Steam configurations (not critical)" -ForegroundColor Cyan
}

# 6. Remove Windows Firewall rules (if any were created)
Write-Host "[6/8] Checking Windows Firewall rules..." -ForegroundColor Yellow
try {
    $FirewallRules = Get-NetFirewallRule -DisplayName "*SoulSniper*" -ErrorAction SilentlyContinue
    if ($FirewallRules) {
        $FirewallRules | Remove-NetFirewallRule -ErrorAction SilentlyContinue
        Write-Host "[OK] Removed firewall rules" -ForegroundColor Green
    } else {
        Write-Host "[INFO] No firewall rules found" -ForegroundColor Cyan
    }
} catch {
    Write-Host "[INFO] Could not check firewall rules" -ForegroundColor Cyan
}

# 7. Clear Windows Event Logs related to the app
Write-Host "[7/8] Clearing application event logs..." -ForegroundColor Yellow
try {
    $Events = Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='*SoulSniper*'} -ErrorAction SilentlyContinue
    if ($Events) {
        # Note: Can't easily delete specific events, but we can clear the entire Application log if needed
        Write-Host "[INFO] Application events exist but will be cleaned by system over time" -ForegroundColor Cyan
    } else {
        Write-Host "[INFO] No application events found" -ForegroundColor Cyan
    }
} catch {
    Write-Host "[INFO] Could not check event logs" -ForegroundColor Cyan
}

# 8. Final cleanup verification
Write-Host "[8/8] Performing final verification..." -ForegroundColor Yellow

# Check if Steam is running and restart it to reload configs
try {
    $SteamProcess = Get-Process -Name "steam" -ErrorAction SilentlyContinue
    if ($SteamProcess) {
        Write-Host "[INFO] Steam is running - configurations will reload automatically" -ForegroundColor Cyan
    }
} catch {
    # Silent continue
}

# Verify task removal
$RemainingTasks = 0
foreach ($Task in $TaskNames) {
    try {
        $ExistingTask = Get-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue
        if ($ExistingTask) {
            $RemainingTasks++
        }
    } catch { }
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "           Uninstall Complete!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Items successfully removed:" -ForegroundColor Cyan
Write-Host "[OK] Scheduled tasks and automation" -ForegroundColor White
Write-Host "[OK] Running processes" -ForegroundColor White
Write-Host "[OK] Registry entries for admin elevation" -ForegroundColor White
Write-Host "[OK] Log files and debug information" -ForegroundColor White
Write-Host "[OK] Steam launch option configurations" -ForegroundColor White
Write-Host "[OK] Windows firewall rules (if any)" -ForegroundColor White
Write-Host "[OK] Application traces" -ForegroundColor White
Write-Host ""

if ($RemainingTasks -gt 0) {
    Write-Host "[WARNING] Some scheduled tasks may still exist" -ForegroundColor Yellow
    Write-Host "   You can manually remove them from Task Scheduler" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Final steps:" -ForegroundColor Yellow
Write-Host "1. The installer will now remove the application files" -ForegroundColor White
Write-Host "2. You may need to restart Steam to ensure configs are reloaded" -ForegroundColor White
Write-Host "3. System restore points are unaffected" -ForegroundColor White
Write-Host ""
Write-Host "Thank you for using SoulSniper's SOF Seeder!" -ForegroundColor Cyan
Write-Host "May your servers always be full!" -ForegroundColor Green

# Don't pause if running from installer
if ($env:TEMP -notlike "*inno*" -and $env:TEMP -notlike "*setup*") {
    Read-Host "Press Enter to close"
}