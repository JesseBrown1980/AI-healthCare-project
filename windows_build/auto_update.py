"""
Auto-update service for Windows application.
Checks for updates and installs them automatically.
"""

import os
import sys
import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import httpx
import zipfile

from .version import get_version, compare_versions

logger = logging.getLogger(__name__)


class UpdateChecker:
    """Service for checking and installing application updates."""
    
    def __init__(
        self,
        update_url: Optional[str] = None,
        current_version: Optional[str] = None,
        app_name: str = "Healthcare AI Assistant",
    ):
        self.update_url = update_url or os.getenv(
            "UPDATE_URL",
            "https://api.github.com/repos/JesseBrown1980/AI-healthCare-project/releases/latest"
        )
        self.current_version = current_version or get_version()
        self.app_name = app_name
        self.app_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent
        self.update_dir = self.app_dir / "updates"
        self.update_dir.mkdir(exist_ok=True)
    
    async def check_for_updates(self) -> Optional[Dict[str, Any]]:
        """Check if a newer version is available."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if "github.com" in self.update_url:
                    # GitHub Releases API
                    response = await client.get(self.update_url)
                    response.raise_for_status()
                    release_data = response.json()
                    
                    latest_version = release_data.get("tag_name", "").lstrip("v")
                    if not latest_version:
                        return None
                    
                    if compare_versions(self.current_version, latest_version) < 0:
                        # Find Windows installer asset
                        assets = release_data.get("assets", [])
                        installer_asset = None
                        for asset in assets:
                            if asset.get("name", "").endswith(".exe") and "installer" in asset.get("name", "").lower():
                                installer_asset = asset
                                break
                        
                        if installer_asset:
                            return {
                                "available": True,
                                "current_version": self.current_version,
                                "latest_version": latest_version,
                                "release_notes": release_data.get("body", ""),
                                "download_url": installer_asset.get("browser_download_url"),
                                "download_size": installer_asset.get("size", 0),
                                "published_at": release_data.get("published_at"),
                            }
                else:
                    # Custom update server
                    response = await client.get(self.update_url)
                    response.raise_for_status()
                    update_data = response.json()
                    
                    latest_version = update_data.get("version", "")
                    if latest_version and compare_versions(self.current_version, latest_version) < 0:
                        return {
                            "available": True,
                            "current_version": self.current_version,
                            "latest_version": latest_version,
                            "release_notes": update_data.get("release_notes", ""),
                            "download_url": update_data.get("download_url"),
                            "download_size": update_data.get("size", 0),
                        }
            
            return {"available": False, "current_version": self.current_version}
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            return None
    
    async def download_update(self, download_url: str, progress_callback=None) -> Optional[Path]:
        """Download the update installer."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("GET", download_url) as response:
                    response.raise_for_status()
                    
                    # Determine file extension
                    file_ext = ".exe" if download_url.endswith(".exe") else ".zip"
                    temp_file = self.update_dir / f"update_installer{file_ext}"
                    
                    total_size = int(response.headers.get("content-length", 0))
                    downloaded = 0
                    
                    with open(temp_file, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                progress = (downloaded / total_size) * 100
                                progress_callback(progress)
                    
                    return temp_file
        except Exception as e:
            logger.error(f"Failed to download update: {e}")
            return None
    
    def install_update(self, installer_path: Path, silent: bool = True) -> bool:
        """Install the update using the downloaded installer."""
        try:
            if installer_path.suffix == ".exe":
                # Run installer silently
                if silent:
                    subprocess.Popen(
                        [str(installer_path), "/SILENT", "/NORESTART"],
                        cwd=str(installer_path.parent)
                    )
                else:
                    subprocess.Popen([str(installer_path)], cwd=str(installer_path.parent))
                return True
            elif installer_path.suffix == ".zip":
                # Extract and replace files
                extract_dir = self.update_dir / "extracted"
                extract_dir.mkdir(exist_ok=True)
                
                with zipfile.ZipFile(installer_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Copy files to app directory (implementation depends on structure)
                # This is a simplified version - adjust based on your needs
                for file in extract_dir.rglob("*"):
                    if file.is_file():
                        dest = self.app_dir / file.relative_to(extract_dir)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file, dest)
                
                return True
        except Exception as e:
            logger.error(f"Failed to install update: {e}")
            return False
    
    async def update_application(self, update_info: Dict[str, Any], progress_callback=None) -> bool:
        """Complete update process: download and install."""
        download_url = update_info.get("download_url")
        if not download_url:
            logger.error("No download URL in update info")
            return False
        
        # Download update
        installer_path = await self.download_update(download_url, progress_callback)
        if not installer_path:
            return False
        
        # Install update
        return self.install_update(installer_path)


class UpdateService:
    """Background service for checking and applying updates."""
    
    def __init__(self, update_checker: UpdateChecker, check_interval: int = 3600):
        self.update_checker = update_checker
        self.check_interval = check_interval  # Check every hour by default
        self.running = False
    
    async def start(self):
        """Start the update service."""
        self.running = True
        import asyncio
        
        while self.running:
            try:
                update_info = await self.update_checker.check_for_updates()
                if update_info and update_info.get("available"):
                    logger.info(f"Update available: {update_info['latest_version']}")
                    # In a real implementation, you might want to notify the user
                    # or automatically download and install
            except Exception as e:
                logger.error(f"Update check failed: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Stop the update service."""
        self.running = False

