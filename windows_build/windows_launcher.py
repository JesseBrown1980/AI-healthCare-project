"""
Windows launcher for Healthcare AI Assistant.
Provides GUI interface and handles auto-updates.
"""

import sys
import os
import asyncio
import logging
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
import threading
import subprocess
import webbrowser

# Add project root to path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from windows_build.auto_update import UpdateChecker, UpdateService
from windows_build.version import get_version

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthcareAILauncher:
    """Main launcher GUI for Windows application."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Healthcare AI Assistant")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        # Set window icon if available
        icon_path = _project_root / "windows_build" / "icon.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except:
                pass
        
        self.update_checker = UpdateChecker()
        self.update_service = None
        self.server_process = None
        
        self.setup_ui()
        self.check_updates_on_startup()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Header
        header_frame = tk.Frame(self.root, bg="#2c3e50", height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="🏥 Healthcare AI Assistant",
            font=("Arial", 20, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=20)
        
        version_label = tk.Label(
            header_frame,
            text=f"Version {get_version()}",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#ecf0f1"
        )
        version_label.pack()
        
        # Main content
        content_frame = tk.Frame(self.root, padx=20, pady=20)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status frame
        status_frame = tk.LabelFrame(content_frame, text="Status", padx=10, pady=10)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.status_label = tk.Label(
            status_frame,
            text="Ready to start",
            font=("Arial", 11),
            anchor="w"
        )
        self.status_label.pack(fill=tk.X)
        
        # Buttons frame
        buttons_frame = tk.Frame(content_frame)
        buttons_frame.pack(fill=tk.X, pady=20)
        
        self.start_button = tk.Button(
            buttons_frame,
            text="▶ Start Application",
            font=("Arial", 12, "bold"),
            bg="#27ae60",
            fg="white",
            padx=20,
            pady=10,
            command=self.start_application,
            cursor="hand2"
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(
            buttons_frame,
            text="⏹ Stop Application",
            font=("Arial", 12),
            bg="#e74c3c",
            fg="white",
            padx=20,
            pady=10,
            command=self.stop_application,
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.open_browser_button = tk.Button(
            buttons_frame,
            text="🌐 Open in Browser",
            font=("Arial", 12),
            bg="#3498db",
            fg="white",
            padx=20,
            pady=10,
            command=self.open_browser,
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.open_browser_button.pack(side=tk.LEFT, padx=5)
        
        # Update frame
        update_frame = tk.LabelFrame(content_frame, text="Updates", padx=10, pady=10)
        update_frame.pack(fill=tk.X, pady=10)
        
        self.update_status_label = tk.Label(
            update_frame,
            text="Checking for updates...",
            font=("Arial", 10),
            anchor="w"
        )
        self.update_status_label.pack(fill=tk.X)
        
        update_button = tk.Button(
            update_frame,
            text="Check for Updates",
            command=self.check_updates,
            cursor="hand2"
        )
        update_button.pack(side=tk.LEFT, pady=5)
    
    def update_status(self, message: str):
        """Update status label."""
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def start_application(self):
        """Start the FastAPI server."""
        try:
            self.update_status("Starting application...")
            
            # Determine if running as executable or script
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                server_script = sys.executable
                server_args = ["-m", "backend.main"]
            else:
                # Running as script
                server_script = sys.executable
                server_args = ["-m", "backend.main"]
            
            # Start server in background
            self.server_process = subprocess.Popen(
                [server_script] + server_args,
                cwd=str(_project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.open_browser_button.config(state=tk.NORMAL)
            
            self.update_status("Application started successfully")
            
            # Open browser after a short delay
            self.root.after(2000, self.open_browser)
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            messagebox.showerror("Error", f"Failed to start application: {str(e)}")
            self.update_status("Failed to start")
    
    def stop_application(self):
        """Stop the FastAPI server."""
        try:
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                self.server_process = None
            
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.open_browser_button.config(state=tk.DISABLED)
            
            self.update_status("Application stopped")
        except Exception as e:
            logger.error(f"Failed to stop application: {e}")
            messagebox.showerror("Error", f"Failed to stop application: {str(e)}")
    
    def open_browser(self):
        """Open the application in default browser."""
        webbrowser.open("http://localhost:8000")
    
    def check_updates_on_startup(self):
        """Check for updates when launcher starts."""
        threading.Thread(target=self._check_updates_async, daemon=True).start()
    
    def _check_updates_async(self):
        """Check for updates asynchronously."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            update_info = loop.run_until_complete(self.update_checker.check_for_updates())
            loop.close()
            
            if update_info and update_info.get("available"):
                self.root.after(0, lambda: self._show_update_available(update_info))
            else:
                self.root.after(0, lambda: self.update_status_label.config(
                    text=f"Up to date (Version {get_version()})"
                ))
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            self.root.after(0, lambda: self.update_status_label.config(
                text="Update check failed"
            ))
    
    def check_updates(self):
        """Manually check for updates."""
        self.update_status_label.config(text="Checking for updates...")
        threading.Thread(target=self._check_updates_async, daemon=True).start()
    
    def _show_update_available(self, update_info: Dict):
        """Show update available dialog."""
        latest_version = update_info.get("latest_version", "Unknown")
        current_version = update_info.get("current_version", "Unknown")
        release_notes = update_info.get("release_notes", "")
        
        message = f"Update available!\n\n"
        message += f"Current version: {current_version}\n"
        message += f"Latest version: {latest_version}\n\n"
        if release_notes:
            message += f"Release notes:\n{release_notes[:200]}...\n\n"
        message += "Would you like to download and install the update?"
        
        if messagebox.askyesno("Update Available", message):
            self._download_and_install_update(update_info)
        else:
            self.update_status_label.config(
                text=f"Update available: {latest_version} (Click 'Check for Updates' to install)"
            )
    
    def _download_and_install_update(self, update_info: Dict):
        """Download and install update."""
        self.update_status_label.config(text="Downloading update...")
        
        def download_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                def progress_callback(progress):
                    self.root.after(0, lambda: self.update_status_label.config(
                        text=f"Downloading update... {progress:.1f}%"
                    ))
                
                success = loop.run_until_complete(
                    self.update_checker.update_application(update_info, progress_callback)
                )
                loop.close()
                
                if success:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Update",
                        "Update downloaded successfully. The installer will start shortly."
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Update Failed",
                        "Failed to download or install update."
                    ))
            except Exception as e:
                logger.error(f"Update failed: {e}")
                self.root.after(0, lambda: messagebox.showerror(
                    "Update Failed",
                    f"Update failed: {str(e)}"
                ))
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def run(self):
        """Run the launcher."""
        self.root.mainloop()
        
        # Cleanup on exit
        if self.server_process:
            self.stop_application()


if __name__ == "__main__":
    launcher = HealthcareAILauncher()
    launcher.run()

