# Windows System File and Registry Repair Tools

These tools help diagnose and repair Windows file system and registry recognition issues.

## ⚠️ WARNING

These tools modify Windows registry and system settings. **Always backup your system** before running repair tools.

## Tools

### 1. Diagnostic Tool (`diagnose_system.py`)

**Purpose**: Diagnose file system and registry issues without making changes.

**Usage**:
```batch
python windows_build\system_repair\diagnose_system.py
```

**What it checks**:
- File associations
- System file visibility
- Registry access
- File Explorer settings

**Output**: Creates `diagnostic_report.txt` with findings and recommendations.

### 2. Repair Tool (`repair_system.py`)

**Purpose**: Fix file system visibility and registry issues.

**⚠️ Requires Administrator privileges**

**Usage**:
```batch
# Right-click and "Run as administrator"
python windows_build\system_repair\repair_system.py
```

**What it fixes**:
- Restores File Explorer settings (show hidden/system files)
- Repairs file associations
- Rebuilds icon cache
- Optional: Runs DISM repair (takes 15-30 minutes)

### 3. Quick Fix PowerShell Script (`quick_fix.ps1`)

**Purpose**: Quick fix for File Explorer visibility issues.

**⚠️ Requires Administrator privileges**

**Usage**:
```powershell
# Right-click and "Run as Administrator"
.\windows_build\system_repair\quick_fix.ps1
```

**What it does**:
- Shows hidden files
- Shows system files
- Shows file extensions
- Restarts File Explorer

## Step-by-Step Repair Process

### Step 1: Diagnose
```batch
python windows_build\system_repair\diagnose_system.py
```

Review the diagnostic report to understand what's wrong.

### Step 2: Quick Fix (Try First)
```powershell
# Run as Administrator
.\windows_build\system_repair\quick_fix.ps1
```

This fixes most common File Explorer visibility issues.

### Step 3: Full Repair (If Quick Fix Doesn't Work)
```batch
# Run as Administrator
python windows_build\system_repair\repair_system.py
```

Follow the prompts. This will:
1. Restore File Explorer settings
2. Repair file associations
3. Rebuild icon cache
4. Optionally run DISM repair

### Step 4: System File Checker (If Still Having Issues)
```batch
# Run as Administrator in Command Prompt
sfc /scannow
```

This checks and repairs Windows system files (takes 15-30 minutes).

### Step 5: DISM Repair (Last Resort)
```batch
# Run as Administrator in Command Prompt
dism /online /cleanup-image /restorehealth
```

This repairs the Windows image (takes 15-30 minutes).

## Common Issues and Solutions

### Files Not Showing in File Explorer

**Quick Fix**: Run `quick_fix.ps1` as administrator

**Full Fix**: Run `repair_system.py` and select "yes" to restore File Explorer settings

### File Associations Broken

**Fix**: Run `repair_system.py` - it will repair common file associations

### Registry Not Recognizing Files

**Fix**: 
1. Run `repair_system.py`
2. Run `sfc /scannow` as administrator
3. If still broken, run `dism /online /cleanup-image /restorehealth`

### System Files Hidden

**Fix**: Run `quick_fix.ps1` or `repair_system.py` to restore visibility

## Safety

- **Backup First**: Create a system restore point before running repair tools
- **Run as Admin**: Most repairs require administrator privileges
- **Read Prompts**: The tools will ask for confirmation before making changes
- **Restart**: Some changes require a computer restart to take effect

## Creating a System Restore Point

Before running repairs, create a restore point:

1. Press `Win + R`
2. Type: `sysdm.cpl`
3. Go to "System Protection" tab
4. Click "Create"
5. Follow the wizard

## If Nothing Works

If these tools don't fix the issue:

1. **System Restore**: Restore to a point before the issue occurred
2. **Windows Update**: Install all available Windows updates
3. **System File Check**: Run `sfc /scannow` and `dism /online /cleanup-image /restorehealth`
4. **Professional Help**: Consider consulting a Windows system administrator

## Notes

- These tools are designed for Windows 10/11
- Some repairs require a restart to take effect
- DISM and SFC scans can take 15-30 minutes
- Always backup important data before system repairs

