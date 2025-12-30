# Python Setup Script - Requires Administrator
# This script will request elevation automatically

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Cyan
    Write-Host "Please approve the UAC prompt." -ForegroundColor Yellow
    Write-Host ""
    
    # Re-run script as Administrator
    $scriptPath = $MyInvocation.MyCommand.Path
    Start-Process powershell -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$scriptPath`"" -Wait
    exit
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Python PATH Configuration (Administrator)" -ForegroundColor Cyan
Write-Host "Healthcare AI Project Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Python installation paths
$pythonPath = "C:\Users\acer\AppData\Local\Programs\Python\Python313"
$pythonScriptsPath = "$pythonPath\Scripts"
$pythonExe = "$pythonPath\python.exe"

# Verify Python exists
if (-not (Test-Path $pythonExe)) {
    Write-Host "[ERROR] Python not found at: $pythonExe" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Found Python installation at: $pythonPath" -ForegroundColor Green
Write-Host ""

# Get current System PATH
$systemPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")

# Check if Python is already in System PATH
$pathNeedsUpdate = $true
$scriptsNeedsUpdate = $true

if ($systemPath -like "*$pythonPath*") {
    Write-Host "[OK] Python directory already in System PATH" -ForegroundColor Green
    $pathNeedsUpdate = $false
} else {
    Write-Host "[MISSING] Python directory NOT in System PATH" -ForegroundColor Yellow
}

if ($systemPath -like "*$pythonScriptsPath*") {
    Write-Host "[OK] Python Scripts directory already in System PATH" -ForegroundColor Green
    $scriptsNeedsUpdate = $false
} else {
    Write-Host "[MISSING] Python Scripts directory NOT in System PATH" -ForegroundColor Yellow
}

Write-Host ""

# Add to System PATH if needed
if ($pathNeedsUpdate -or $scriptsNeedsUpdate) {
    Write-Host "Adding Python to System PATH..." -ForegroundColor Cyan
    
    $newSystemPath = $systemPath
    
    if ($pathNeedsUpdate) {
        if ($newSystemPath -and -not $newSystemPath.EndsWith(";")) {
            $newSystemPath += ";"
        }
        $newSystemPath += $pythonPath
        Write-Host "  [Added] $pythonPath" -ForegroundColor Green
    }
    
    if ($scriptsNeedsUpdate) {
        if ($newSystemPath -and -not $newSystemPath.EndsWith(";")) {
            $newSystemPath += ";"
        }
        $newSystemPath += $pythonScriptsPath
        Write-Host "  [Added] $pythonScriptsPath" -ForegroundColor Green
    }
    
    # Update System PATH
    [Environment]::SetEnvironmentVariable("Path", $newSystemPath, "Machine")
    
    Write-Host ""
    Write-Host "[SUCCESS] System PATH updated successfully!" -ForegroundColor Green
} else {
    Write-Host "[OK] System PATH already configured correctly" -ForegroundColor Green
}

Write-Host ""

# Disable Windows Store Python aliases
Write-Host "Disabling Windows Store Python aliases..." -ForegroundColor Cyan
$windowsAppsPath = "$env:LOCALAPPDATA\Microsoft\WindowsApps"
$pythonAlias = "$windowsAppsPath\python.exe"
$python3Alias = "$windowsAppsPath\python3.exe"

if (Test-Path $pythonAlias) {
    try {
        $backupName = "python.exe.backup"
        $backupPath = "$windowsAppsPath\$backupName"
        
        if (Test-Path $backupPath) {
            Remove-Item $backupPath -Force
        }
        
        Rename-Item $pythonAlias $backupName -Force
        Write-Host "[OK] Disabled python.exe alias (backed up)" -ForegroundColor Green
    } catch {
        Write-Host "[WARNING] Could not disable python.exe alias: $_" -ForegroundColor Yellow
        Write-Host "  You may need to disable it manually in Windows Settings" -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] python.exe alias not found (already disabled)" -ForegroundColor Green
}

if (Test-Path $python3Alias) {
    try {
        $backupName = "python3.exe.backup"
        $backupPath = "$windowsAppsPath\$backupName"
        
        if (Test-Path $backupPath) {
            Remove-Item $backupPath -Force
        }
        
        Rename-Item $python3Alias $backupName -Force
        Write-Host "[OK] Disabled python3.exe alias (backed up)" -ForegroundColor Green
    } catch {
        Write-Host "[WARNING] Could not disable python3.exe alias: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] python3.exe alias not found (already disabled)" -ForegroundColor Green
}

Write-Host ""

# Verify Python installation
Write-Host "Verifying Python installation..." -ForegroundColor Cyan
try {
    $pythonVersion = & "$pythonExe" --version 2>&1
    Write-Host "[OK] Python version: $pythonVersion" -ForegroundColor Green
    
    $pipVersion = & "$pythonExe" -m pip --version 2>&1
    Write-Host "[OK] pip version: $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Error verifying Python: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[COMPLETE] Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT: Please close and reopen your terminal for changes to take effect." -ForegroundColor Yellow
Write-Host ""
Write-Host "After restarting terminal, verify with:" -ForegroundColor Cyan
Write-Host "  python --version" -ForegroundColor White
Write-Host "  pip --version" -ForegroundColor White
Write-Host "  where python" -ForegroundColor White
Write-Host ""

# Pause so user can see the results
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

