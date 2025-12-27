"""
Windows System File and Registry Repair Tool
Fixes file system visibility and registry recognition issues.
WARNING: This tool modifies Windows registry. Use with caution.
"""

import os
import sys
import winreg
import subprocess
from pathlib import Path
from typing import Dict, Any

def is_admin() -> bool:
    """Check if running as administrator."""
    try:
        return os.getuid() == 0
    except AttributeError:
        # Windows
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def require_admin():
    """Require administrator privileges."""
    if not is_admin():
        print("ERROR: This script requires administrator privileges!")
        print("Please run as administrator:")
        print("1. Right-click on this script")
        print("2. Select 'Run as administrator'")
        sys.exit(1)

def restore_file_explorer_settings() -> Dict[str, Any]:
    """Restore File Explorer settings to show all files."""
    print("Restoring File Explorer settings...")
    
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced",
            0,
            winreg.KEY_WRITE
        )
        
        changes = []
        
        try:
            # Show hidden files
            try:
                winreg.SetValueEx(key, "Hidden", 0, winreg.REG_DWORD, 1)
                changes.append("Set Hidden files to 'Show'")
            except Exception as e:
                changes.append(f"Failed to set Hidden: {e}")
            
            # Show system files
            try:
                winreg.SetValueEx(key, "ShowSuperHidden", 0, winreg.REG_DWORD, 1)
                changes.append("Set System files to 'Show'")
            except Exception as e:
                changes.append(f"Failed to set ShowSuperHidden: {e}")
            
            # Show file extensions
            try:
                winreg.SetValueEx(key, "HideFileExt", 0, winreg.REG_DWORD, 0)
                changes.append("Set file extensions to 'Show'")
            except Exception as e:
                changes.append(f"Failed to set HideFileExt: {e}")
            
        finally:
            key.Close()
        
        # Refresh File Explorer
        try:
            subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], 
                         capture_output=True, timeout=5)
            subprocess.Popen("explorer.exe")
            changes.append("Refreshed File Explorer")
        except Exception:
            changes.append("Please restart File Explorer manually")
        
        return {"status": "success", "changes": changes}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def repair_file_associations() -> Dict[str, Any]:
    """Repair common file associations."""
    print("Repairing file associations...")
    
    associations = {
        '.txt': ('txtfile', 'Notepad'),
        '.bat': ('batfile', 'Windows Batch File'),
        '.cmd': ('cmdfile', 'Windows Command Script'),
        '.py': ('Python.File', 'Python Script'),
    }
    
    repaired = []
    failed = []
    
    for ext, (progid, description) in associations.items():
        try:
            # Create extension key
            ext_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, ext)
            winreg.SetValue(ext_key, None, winreg.REG_SZ, progid)
            ext_key.Close()
            
            # Create/update ProgID if it doesn't exist
            try:
                progid_key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, progid, 0, winreg.KEY_READ)
                progid_key.Close()
            except FileNotFoundError:
                # Create basic ProgID
                progid_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, progid)
                winreg.SetValue(progid_key, None, winreg.REG_SZ, description)
                progid_key.Close()
            
            repaired.append(ext)
        except Exception as e:
            failed.append(f"{ext}: {e}")
    
    return {
        "status": "success" if not failed else "partial",
        "repaired": repaired,
        "failed": failed
    }

def rebuild_icon_cache() -> Dict[str, Any]:
    """Rebuild Windows icon cache."""
    print("Rebuilding icon cache...")
    
    try:
        # Delete icon cache files
        cache_paths = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "IconCache.db",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Explorer" / "iconcache*.db",
        ]
        
        deleted = []
        for cache_path in cache_paths:
            if cache_path.exists():
                try:
                    cache_path.unlink()
                    deleted.append(str(cache_path))
                except Exception:
                    pass
        
        # Restart explorer to rebuild cache
        try:
            subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], 
                         capture_output=True, timeout=5)
            subprocess.Popen("explorer.exe")
        except Exception:
            pass
        
        return {"status": "success", "deleted": deleted}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def run_dism_repair() -> Dict[str, Any]:
    """Run DISM repair commands."""
    print("Running DISM repair (this may take a while)...")
    
    commands = [
        ["dism", "/online", "/cleanup-image", "/restorehealth"],
    ]
    
    results = []
    for cmd in commands:
        try:
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            results.append({
                "command": " ".join(cmd),
                "returncode": result.returncode,
                "success": result.returncode == 0
            })
        except subprocess.TimeoutExpired:
            results.append({
                "command": " ".join(cmd),
                "success": False,
                "error": "Timeout"
            })
        except Exception as e:
            results.append({
                "command": " ".join(cmd),
                "success": False,
                "error": str(e)
            })
    
    return {"status": "completed", "results": results}

def main():
    """Main repair function."""
    print("=" * 60)
    print("Windows System Repair Tool")
    print("=" * 60)
    print("\nWARNING: This tool will modify Windows registry and system settings.")
    print("Make sure you have a backup before proceeding.\n")
    
    response = input("Do you want to continue? (yes/no): ")
    if response.lower() != "yes":
        print("Aborted.")
        return
    
    require_admin()
    
    print("\nStarting repair process...\n")
    
    results = {}
    
    # Step 1: Restore File Explorer settings
    print("Step 1: Restoring File Explorer settings...")
    results["file_explorer"] = restore_file_explorer_settings()
    print(f"  Status: {results['file_explorer']['status']}\n")
    
    # Step 2: Repair file associations
    print("Step 2: Repairing file associations...")
    results["file_associations"] = repair_file_associations()
    print(f"  Status: {results['file_associations']['status']}\n")
    
    # Step 3: Rebuild icon cache
    print("Step 3: Rebuilding icon cache...")
    results["icon_cache"] = rebuild_icon_cache()
    print(f"  Status: {results['icon_cache']['status']}\n")
    
    # Step 4: Ask about DISM (takes a long time)
    print("Step 4: DISM repair (optional, takes 15-30 minutes)")
    response = input("  Run DISM repair? (yes/no): ")
    if response.lower() == "yes":
        results["dism"] = run_dism_repair()
        print(f"  Status: {results['dism']['status']}\n")
    else:
        results["dism"] = {"status": "skipped"}
    
    # Summary
    print("\n" + "=" * 60)
    print("Repair Summary")
    print("=" * 60)
    
    for step, result in results.items():
        status = result.get("status", "unknown")
        print(f"{step.replace('_', ' ').title()}: {status}")
    
    print("\n" + "=" * 60)
    print("\nRepair completed!")
    print("Please restart your computer for all changes to take effect.")
    print("\nIf issues persist, you may need to:")
    print("1. Run SFC /scannow as administrator")
    print("2. Check Windows Update for system updates")
    print("3. Consider a system restore point")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nPress Enter to exit...")

