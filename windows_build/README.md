# Windows Build and Installation

This directory contains files for building a Windows executable and
installer for the Healthcare AI Assistant.

## Prerequisites

1. **Python 3.9+** installed on Windows
2. **PyInstaller** - Will be installed automatically
3. **Inno Setup 6** (optional, for creating installer) - Download from
   [Inno Setup](https://jrsoftware.org/isdl.php)

## Building the Application

### Quick Build

Run the build script:

```batch
windows_build\build_windows.bat
```

This will:

1. Create/activate a virtual environment
2. Install all dependencies
3. Build the executable using PyInstaller
4. Create an installer using Inno Setup (if available)

### Manual Build

1. **Install dependencies:**

   ```batch
   pip install pyinstaller
   pip install -r requirements.txt
   pip install -r backend/requirements.txt
   pip install -r frontend/requirements.txt
   ```

2. **Build executable:**

   ```batch
   pyinstaller --clean --noconfirm windows_build\healthcare_ai.spec
   ```

3. **Build installer (if Inno Setup is installed):**

   ```batch
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" windows_build\installer.iss
   ```

## Output Files

- **Executable:** `dist\HealthcareAIAssistant.exe`
- **Installer:** `windows_build\dist\HealthcareAIAssistant-Setup-1.0.0.exe`

## Installation

1. Run the installer executable
2. Follow the installation wizard
3. Choose installation options:
   - Desktop shortcut
   - Start menu shortcut
   - Start on Windows startup (optional)

## Auto-Update

The application includes automatic update functionality:

- Checks for updates on startup
- Can check manually via the launcher
- Downloads and installs updates from GitHub Releases
- Supports both automatic and manual update installation

### Update Configuration

Set the `UPDATE_URL` environment variable to customize the update source:

- Default: GitHub Releases API
- Custom: Your own update server endpoint

## Launcher Features

The Windows launcher provides:

- **Start/Stop Application** - Control the FastAPI server
- **Open in Browser** - Quick access to the web interface
- **Update Checker** - Automatic and manual update checking
- **Status Display** - Real-time application status

## Icon

Place a `icon.ico` file in the `windows_build` directory to use a custom
icon for the executable and installer.

## Troubleshooting

### Build Fails

1. Ensure all dependencies are installed
2. Check that Python version is 3.9+
3. Verify PyInstaller is installed: `pip show pyinstaller`

### Executable Doesn't Run

1. Check Windows Event Viewer for errors
2. Run from command line to see error messages
3. Verify all required files are included in the build

### Updates Don't Work

1. Check internet connectivity
2. Verify GitHub Releases API is accessible
3. Check application logs for update errors
