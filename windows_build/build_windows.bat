@echo off
REM Build script for Windows executable and installer
REM Requires: Python, PyInstaller, Inno Setup

echo Building Healthcare AI Assistant for Windows...

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install/upgrade build dependencies
echo Installing build dependencies...
pip install --upgrade pip
pip install pyinstaller
pip install -r requirements.txt
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt

REM Create dist directory
if not exist "dist" mkdir dist
if not exist "windows_build\dist" mkdir windows_build\dist

REM Build executable with PyInstaller
echo Building executable...
pyinstaller --clean --noconfirm windows_build\healthcare_ai.spec

REM Check if build was successful
if not exist "dist\HealthcareAIAssistant.exe" (
    echo ERROR: Executable build failed!
    pause
    exit /b 1
)

echo Executable built successfully!

REM Build installer with Inno Setup (if available)
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    echo Building installer...
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" windows_build\installer.iss
    echo Installer built successfully!
) else (
    echo Inno Setup not found. Skipping installer build.
    echo Installer can be built manually with: iscc windows_build\installer.iss
)

echo.
echo Build complete!
echo Executable: dist\HealthcareAIAssistant.exe
if exist "windows_build\dist\*.exe" (
    echo Installer: windows_build\dist\*.exe
)
pause

