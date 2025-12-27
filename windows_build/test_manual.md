# Manual Testing Guide for Windows Build

Since automated testing requires Python in PATH, here's a manual testing guide.

## Prerequisites Check

1. **Python Installation**
   - Open Command Prompt
   - Run: `python --version` or `py --version`
   - Should show Python 3.9 or higher

2. **Virtual Environment**
   - Navigate to project directory
   - Run: `python -m venv .venv`
   - Activate: `.venv\Scripts\activate`

3. **Dependencies**
   - Install: `pip install -r requirements.txt`
   - Install: `pip install -r backend/requirements.txt`
   - Install: `pip install pyinstaller`

## Test Steps

### 1. Test Version Module
```python
python -c "from windows_build.version import get_version; print(get_version())"
```
Expected: `1.0.0`

### 2. Test Auto-Update Module
```python
python -c "from windows_build.auto_update import UpdateChecker; print('OK')"
```
Expected: `OK`

### 3. Test Launcher Import
```python
python -c "import windows_build.windows_launcher; print('OK')"
```
Expected: `OK`

### 4. Test Launcher GUI (Optional)
```python
python windows_build\windows_launcher.py
```
Expected: GUI window opens

### 5. Run Full Test Script
```python
python windows_build\test_build.py
```
Expected: All tests pass

### 6. Build Executable
```batch
windows_build\build_windows.bat
```
Expected: `dist\HealthcareAIAssistant.exe` created

### 7. Test Executable
- Navigate to `dist` folder
- Double-click `HealthcareAIAssistant.exe`
- Expected: Launcher GUI opens

### 8. Test Update Checker
- In launcher, click "Check for Updates"
- Expected: Status updates (may show "Up to date" or "Update available")

## Common Issues

### Python Not Found
- Install Python from python.org
- Or use `py` launcher: `py -m pip install ...`

### Import Errors
- Ensure you're in project root directory
- Activate virtual environment
- Install all requirements

### PyInstaller Errors
- Update PyInstaller: `pip install --upgrade pyinstaller`
- Check spec file syntax
- Ensure all dependencies are installed

### GUI Doesn't Open
- Check if tkinter is installed: `python -m tkinter`
- On some systems, may need: `pip install tk`

## Build Output

After successful build:
- **Executable**: `dist\HealthcareAIAssistant.exe`
- **Installer** (if Inno Setup installed): `windows_build\dist\*.exe`

## Next Steps

1. Test the executable
2. Create installer (if Inno Setup available)
3. Test installation process
4. Test auto-update functionality
5. Create GitHub release for update testing

