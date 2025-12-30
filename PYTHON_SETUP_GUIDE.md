# Python Setup Guide for Healthcare AI Project

## Overview

This guide will help you configure Python properly on your Windows system so that the `python` command works correctly in your terminal, making your development environment more professional and consistent.

## Current Situation

- ✅ Python 3.13.2 is installed at: `C:\Users\acer\AppData\Local\Programs\Python\Python313\`
- ❌ Python is NOT in your system PATH
- ⚠️ Windows Store Python alias is intercepting `python` commands

## Quick Setup (Automated)

### Step 1: Add Python to PATH

Run the setup script:

```powershell
# In PowerShell (run as Administrator for system-wide changes)
.\setup_python_path.ps1
```

**Or manually:**
1. Press `Win + X` and select "System"
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "User variables", select "Path" and click "Edit"
5. Click "New" and add:
   - `C:\Users\acer\AppData\Local\Programs\Python\Python313`
   - `C:\Users\acer\AppData\Local\Programs\Python\Python313\Scripts`
6. Click OK on all dialogs

### Step 2: Disable Windows Store Python Alias

**Option A: Run the script (as Administrator)**
```powershell
.\disable_windows_store_python.ps1
```

**Option B: Manual method**
1. Press `Win + I` to open Settings
2. Go to: **Apps** → **App execution aliases**
3. Find "App Installer" entries for:
   - `python.exe`
   - `python3.exe`
4. Turn both **OFF**
5. Close Settings

### Step 3: Restart Terminal

Close and reopen your terminal/PowerShell window.

### Step 4: Verify

```powershell
python --version    # Should show: Python 3.13.2
pip --version       # Should show pip version
where python        # Should show: C:\Users\acer\AppData\Local\Programs\Python\Python313\python.exe
```

## Manual Setup (If Scripts Don't Work)

### Add Python to PATH Manually

1. **Open Environment Variables:**
   - Press `Win + R`
   - Type: `sysdm.cpl` and press Enter
   - Go to "Advanced" tab
   - Click "Environment Variables"

2. **Edit User PATH:**
   - Under "User variables", find "Path"
   - Click "Edit"
   - Click "New" and add:
     ```
     C:\Users\acer\AppData\Local\Programs\Python\Python313
     ```
   - Click "New" again and add:
     ```
     C:\Users\acer\AppData\Local\Programs\Python\Python313\Scripts
     ```
   - Click OK on all dialogs

3. **Restart your terminal**

### Disable Windows Store Alias Manually

1. Open Windows Settings (`Win + I`)
2. Navigate to: **Apps** → **App execution aliases**
3. Scroll down to find "App Installer"
4. Turn OFF the toggles for:
   - `python.exe`
   - `python3.exe`
5. Close Settings
6. Restart your terminal

## Verification Checklist

After setup, verify everything works:

```powershell
# Test Python
python --version
# Expected: Python 3.13.2

# Test pip
pip --version
# Expected: pip version number

# Test Python location
where python
# Expected: C:\Users\acer\AppData\Local\Programs\Python\Python313\python.exe

# Test pip location
where pip
# Expected: C:\Users\acer\AppData\Local\Programs\Python\Python313\Scripts\pip.exe

# Test Python can import modules
python -c "import sys; print(sys.executable)"
# Expected: Full path to python.exe
```

## Troubleshooting

### Issue: `python` still doesn't work after setup

**Solutions:**
1. **Restart your computer** (sometimes required for PATH changes)
2. **Check PATH order**: Windows Store path might be first
   ```powershell
   $env:PATH -split ';' | Select-String -Pattern 'python'
   ```
3. **Verify Python installation:**
   ```powershell
   Test-Path "C:\Users\acer\AppData\Local\Programs\Python\Python313\python.exe"
   ```
4. **Check Windows Store aliases are disabled:**
   - Settings → Apps → App execution aliases
   - Ensure both python.exe and python3.exe are OFF

### Issue: "Access Denied" when running scripts

**Solution:** Run PowerShell as Administrator
- Right-click PowerShell
- Select "Run as Administrator"
- Navigate to project directory
- Run the script again

### Issue: PATH changes don't persist

**Solution:** Make sure you're editing the correct PATH variable
- **User PATH**: Only affects your user account (recommended)
- **System PATH**: Affects all users (requires admin)

## Why This Matters

### Professional Development
- ✅ Consistent commands across all projects
- ✅ Standard tooling compatibility
- ✅ Better CI/CD integration
- ✅ Easier team collaboration

### Project Benefits
- ✅ Virtual environments work correctly
- ✅ Package installation is reliable
- ✅ Scripts work as expected
- ✅ Documentation commands are accurate

## Next Steps

After Python is properly configured:

1. **Create a virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate
   ```

2. **Install project dependencies:**
   ```powershell
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Run tests:**
   ```powershell
   python -m pytest tests/ -v
   ```

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify Python installation: `py --version` should work
3. Check PATH: `$env:PATH` should include Python directories
4. Verify aliases are disabled in Windows Settings

---

**Status:** Ready to configure ✅
**Python Location:** `C:\Users\acer\AppData\Local\Programs\Python\Python313\`
**Next Action:** Run `.\setup_python_path.ps1` as Administrator

