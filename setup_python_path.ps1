# Python PATH Configuration Script for Healthcare AI Project
# Run this script as Administrator to properly configure Python in system PATH

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Python PATH Configuration Script" -ForegroundColor Cyan
Write-Host "Healthcare AI Project Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "NOTE: Running without Administrator privileges." -ForegroundColor Yellow
    Write-Host "Changes will be made to User PATH (this is usually sufficient)." -ForegroundColor Yellow
    Write-Host ""
}

# Python installation paths
$pythonPath = "C:\Users\acer\AppData\Local\Programs\Python\Python313"
$pythonScriptsPath = "$pythonPath\Scripts"
$pythonExe = "$pythonPath\python.exe"

# Verify Python exists
if (-not (Test-Path $pythonExe)) {
    Write-Host "ERROR: Python not found at expected location: $pythonExe" -ForegroundColor Red
    Write-Host "Please verify your Python installation." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Found Python installation at: $pythonPath" -ForegroundColor Green
Write-Host ""

# Get current PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
$systemPath = [Environment]::GetEnvironmentVariable("Path", "Machine")

# Check if Python is already in PATH
$pathNeedsUpdate = $true
$scriptsNeedsUpdate = $true

if ($currentPath -like "*$pythonPath*") {
    Write-Host "[OK] Python directory already in User PATH" -ForegroundColor Green
    $pathNeedsUpdate = $false
} else {
    Write-Host "[MISSING] Python directory NOT in User PATH" -ForegroundColor Yellow
}

if ($currentPath -like "*$pythonScriptsPath*") {
    Write-Host "[OK] Python Scripts directory already in User PATH" -ForegroundColor Green
    $scriptsNeedsUpdate = $false
} else {
    Write-Host "[MISSING] Python Scripts directory NOT in User PATH" -ForegroundColor Yellow
}

Write-Host ""

# Add to PATH if needed
if ($pathNeedsUpdate -or $scriptsNeedsUpdate) {
    Write-Host "Adding Python to PATH..." -ForegroundColor Cyan
    
    $newPath = $currentPath
    
    if ($pathNeedsUpdate) {
        if ($newPath -and -not $newPath.EndsWith(";")) {
            $newPath += ";"
        }
        $newPath += $pythonPath
        Write-Host "  [Added] $pythonPath" -ForegroundColor Green
    }
    
    if ($scriptsNeedsUpdate) {
        if ($newPath -and -not $newPath.EndsWith(";")) {
            $newPath += ";"
        }
        $newPath += $pythonScriptsPath
        Write-Host "  [Added] $pythonScriptsPath" -ForegroundColor Green
    }
    
    # Update User PATH
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    
    # Also update current session
    $env:Path = $newPath + ";" + $env:Path
    
    Write-Host ""
    Write-Host "[SUCCESS] PATH updated successfully!" -ForegroundColor Green
} else {
    Write-Host "[OK] PATH already configured correctly" -ForegroundColor Green
}

Write-Host ""

# Verify Python is accessible
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

# Check for Windows Store Python alias
$windowsAppsPython = "C:\Users\acer\AppData\Local\Microsoft\WindowsApps\python.exe"
if (Test-Path $windowsAppsPython) {
    Write-Host "WARNING: Windows Store Python alias detected!" -ForegroundColor Yellow
    Write-Host "Location: $windowsAppsPython" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "This alias can interfere with the real Python installation." -ForegroundColor Yellow
    Write-Host "To disable it:" -ForegroundColor Yellow
    Write-Host "1. Open Windows Settings" -ForegroundColor Cyan
    Write-Host "2. Go to: Apps > App execution aliases" -ForegroundColor Cyan
    Write-Host "3. Turn OFF 'App Installer' for python.exe and python3.exe" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or run this command (requires restart):" -ForegroundColor Cyan
    Write-Host "  Remove-Item '$windowsAppsPython' -ErrorAction SilentlyContinue" -ForegroundColor White
    Write-Host ""
}

# Test if 'python' command works
Write-Host "Testing 'python' command..." -ForegroundColor Cyan
try {
    $testResult = & python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] 'python' command works: $testResult" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] 'python' command not working yet" -ForegroundColor Yellow
        Write-Host "  You may need to:" -ForegroundColor Yellow
        Write-Host "  1. Close and reopen this terminal" -ForegroundColor Cyan
        Write-Host "  2. Or restart your computer" -ForegroundColor Cyan
    }
} catch {
    Write-Host "[WARNING] 'python' command not found" -ForegroundColor Yellow
    Write-Host "  Close and reopen your terminal, then test again" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[COMPLETE] Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Close and reopen your terminal" -ForegroundColor White
Write-Host "2. Run: python --version" -ForegroundColor White
Write-Host "3. Run: pip --version" -ForegroundColor White
Write-Host "4. If 'python' still doesn't work, disable Windows Store aliases" -ForegroundColor White
Write-Host ""

