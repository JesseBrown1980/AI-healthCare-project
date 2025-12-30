# Script to disable Windows Store Python aliases
# This prevents Windows Store from intercepting 'python' commands

Write-Host "Disabling Windows Store Python Aliases" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "This script requires Administrator privileges." -ForegroundColor Yellow
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Right-click PowerShell > Run as Administrator" -ForegroundColor Cyan
    exit 1
}

$windowsAppsPath = "$env:LOCALAPPDATA\Microsoft\WindowsApps"

# Check for Python aliases
$pythonAlias = "$windowsAppsPath\python.exe"
$python3Alias = "$windowsAppsPath\python3.exe"

Write-Host "Checking for Windows Store Python aliases..." -ForegroundColor Cyan

if (Test-Path $pythonAlias) {
    Write-Host "Found: $pythonAlias" -ForegroundColor Yellow
    try {
        # Rename instead of delete (safer)
        $backupName = "python.exe.backup"
        $backupPath = "$windowsAppsPath\$backupName"
        
        if (Test-Path $backupPath) {
            Remove-Item $backupPath -Force
        }
        
        Rename-Item $pythonAlias $backupName -Force
        Write-Host "✓ Disabled python.exe alias (backed up as $backupName)" -ForegroundColor Green
    } catch {
        Write-Host "✗ Error disabling python.exe alias: $_" -ForegroundColor Red
        Write-Host "  You may need to disable it manually in Windows Settings" -ForegroundColor Yellow
    }
} else {
    Write-Host "✓ python.exe alias not found (already disabled or doesn't exist)" -ForegroundColor Green
}

if (Test-Path $python3Alias) {
    Write-Host "Found: $python3Alias" -ForegroundColor Yellow
    try {
        $backupName = "python3.exe.backup"
        $backupPath = "$windowsAppsPath\$backupName"
        
        if (Test-Path $backupPath) {
            Remove-Item $backupPath -Force
        }
        
        Rename-Item $python3Alias $backupName -Force
        Write-Host "✓ Disabled python3.exe alias (backed up as $backupName)" -ForegroundColor Green
    } catch {
        Write-Host "✗ Error disabling python3.exe alias: $_" -ForegroundColor Red
    }
} else {
    Write-Host "✓ python3.exe alias not found (already disabled or doesn't exist)" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Alternative Method (if script doesn't work):" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Open Windows Settings (Win + I)" -ForegroundColor White
Write-Host "2. Go to: Apps > App execution aliases" -ForegroundColor White
Write-Host "3. Find 'App Installer' entries for python.exe and python3.exe" -ForegroundColor White
Write-Host "4. Turn them OFF" -ForegroundColor White
Write-Host "5. Restart your terminal" -ForegroundColor White
Write-Host ""

