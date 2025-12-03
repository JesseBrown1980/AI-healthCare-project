# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Healthcare AI Assistant Windows executable.
"""

import sys
from pathlib import Path

block_cipher = None

# Project paths
# SPECPATH is set by PyInstaller, fallback to current file location
try:
    project_root = Path(SPECPATH).parent.parent
except NameError:
    # Fallback if SPECPATH not defined
    project_root = Path(__file__).resolve().parent.parent

backend_path = project_root / "backend"
frontend_path = project_root / "frontend"
windows_build_path = project_root / "windows_build"

a = Analysis(
    [
        str(windows_build_path / "windows_launcher.py"),
        str(backend_path / "main.py"),
    ],
    pathex=[
        str(project_root),
        str(backend_path),
        str(frontend_path),
    ],
    binaries=[],
    datas=[
        (str(backend_path), "backend"),
        (str(frontend_path), "frontend"),
        (str(windows_build_path / "icon.ico"), "."),
    ],
    hiddenimports=[
        "uvicorn",
        "fastapi",
        "pydantic",
        "sqlalchemy",
        "alembic",
        "httpx",
        "jose",
        "bcrypt",
        "torch",
        "transformers",
        "fhir.resources",
        "streamlit",
        "plotly",
        "pandas",
        "numpy",
        "tkinter",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="HealthcareAIAssistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI only)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(windows_build_path / "icon.ico") if (windows_build_path / "icon.ico").exists() else None,
)

