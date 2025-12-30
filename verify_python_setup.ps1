# Python Setup Verification Script
# Run this after the admin setup to verify everything is configured correctly

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Python Setup Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check System PATH
$systemPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")

Write-Host "Checking PATH configuration..." -ForegroundColor Cyan
$pythonInSystemPath = $systemPath -like "*Python313*"
$pythonInUserPath = $userPath -like "*Python313*"

if ($pythonInSystemPath) {
    Write-Host "[OK] Python 3.13.2 is in System PATH" -ForegroundColor Green
} elseif ($pythonInUserPath) {
    Write-Host "[OK] Python 3.13.2 is in User PATH" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Python 3.13.2 not found in PATH" -ForegroundColor Yellow
}

Write-Host ""

# Check Windows Store aliases
Write-Host "Checking Windows Store aliases..." -ForegroundColor Cyan
$windowsAppsPath = "$env:LOCALAPPDATA\Microsoft\WindowsApps"
$pythonAlias = "$windowsAppsPath\python.exe"
$pythonAliasBackup = "$windowsAppsPath\python.exe.backup"

if (Test-Path $pythonAliasBackup) {
    Write-Host "[OK] Windows Store python.exe alias is disabled (backed up)" -ForegroundColor Green
} elseif (-not (Test-Path $pythonAlias)) {
    Write-Host "[OK] Windows Store python.exe alias not found" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Windows Store python.exe alias is still active" -ForegroundColor Yellow
    Write-Host "  Location: $pythonAlias" -ForegroundColor Yellow
    Write-Host "  Please disable it in: Settings > Apps > App execution aliases" -ForegroundColor Cyan
}

Write-Host ""

# Test Python commands
Write-Host "Testing Python commands..." -ForegroundColor Cyan

try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] 'python' command works: $pythonVersion" -ForegroundColor Green
        
        # Check which Python is being used
        $pythonExe = python -c "import sys; print(sys.executable)" 2>&1
        Write-Host "  Executable: $pythonExe" -ForegroundColor Gray
        
        if ($pythonExe -like "*Python313*") {
            Write-Host "[SUCCESS] Using Python 3.13.2!" -ForegroundColor Green
        } elseif ($pythonExe -like "*anaconda*") {
            Write-Host "[INFO] Using Anaconda Python (this is also fine)" -ForegroundColor Cyan
        }
    } else {
        Write-Host "[WARNING] 'python' command returned error" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] 'python' command not found" -ForegroundColor Red
    Write-Host "  You may need to restart your terminal" -ForegroundColor Yellow
}

try {
    $pipVersion = pip --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] 'pip' command works: $pipVersion" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] 'pip' command returned error" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] 'pip' command not found" -ForegroundColor Red
}

Write-Host ""

# Check PATH order
Write-Host "Current PATH order (Python-related entries):" -ForegroundColor Cyan
$allPaths = ($env:Path -split ';') | Where-Object { $_ -like '*python*' -or $_ -like '*anaconda*' -or $_ -like '*Python*' }
$index = 1
foreach ($path in $allPaths) {
    if ($path) {
        Write-Host "  $index. $path" -ForegroundColor Gray
        $index++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Verification Complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If 'python' command doesn't work yet:" -ForegroundColor Yellow
Write-Host "1. Close and reopen your terminal" -ForegroundColor White
Write-Host "2. Or restart your computer" -ForegroundColor White
Write-Host ""

