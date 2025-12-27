# Create System Restore Point
# Run as Administrator

Write-Host "Creating System Restore Point..." -ForegroundColor Cyan
Write-Host ""

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script requires administrator privileges!" -ForegroundColor Red
    Write-Host "Right-click and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit 1
}

try {
    $restorePointName = "Healthcare AI Assistant Repair - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    
    Write-Host "Creating restore point: $restorePointName" -ForegroundColor Green
    
    # Enable System Restore if disabled
    $drive = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'"
    if ($drive) {
        vssadmin list volumes | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Enabling System Restore on C: drive..." -ForegroundColor Yellow
            Enable-ComputerRestore -Drive "C:"
        }
    }
    
    # Create restore point
    Checkpoint-Computer -Description $restorePointName -RestorePointType "MODIFY_SETTINGS"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "System Restore Point created successfully!" -ForegroundColor Green
        Write-Host "Name: $restorePointName" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "Failed to create restore point. You may need to enable System Restore manually." -ForegroundColor Red
        Write-Host "Go to: System Properties > System Protection > Configure" -ForegroundColor Yellow
    }
} catch {
    Write-Host ""
    Write-Host "Error creating restore point: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual method:" -ForegroundColor Yellow
    Write-Host "1. Press Win + R" -ForegroundColor Yellow
    Write-Host "2. Type: sysdm.cpl" -ForegroundColor Yellow
    Write-Host "3. Go to 'System Protection' tab" -ForegroundColor Yellow
    Write-Host "4. Click 'Create'" -ForegroundColor Yellow
}

Write-Host ""
pause

