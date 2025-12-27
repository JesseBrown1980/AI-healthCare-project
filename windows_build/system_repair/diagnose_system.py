"""
Windows System File and Registry Diagnostic Tool
Diagnoses file system and registry recognition issues.
"""

import os
import sys
import winreg
import subprocess
from pathlib import Path
from typing import List, Dict, Any

def check_file_associations() -> Dict[str, Any]:
    """Check if file associations are working."""
    print("Checking file associations...")
    issues = []
    
    # Test common file types
    test_files = {
        '.txt': 'txtfile',
        '.py': 'Python.File',
        '.exe': 'exefile',
        '.bat': 'batfile',
    }
    
    for ext, expected_progid in test_files.items():
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                ext,
                0,
                winreg.KEY_READ
            )
            try:
                progid = winreg.QueryValue(key, None)
                if progid != expected_progid:
                    issues.append(f"{ext} association incorrect: {progid}")
            finally:
                key.Close()
        except Exception as e:
            issues.append(f"{ext} association missing: {e}")
    
    return {"status": "ok" if not issues else "issues", "issues": issues}

def check_system_file_visibility() -> Dict[str, Any]:
    """Check if system files are visible."""
    print("Checking system file visibility...")
    
    # Check common system directories
    system_dirs = [
        "C:\\Windows\\System32",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\Users",
    ]
    
    accessible = []
    inaccessible = []
    
    for dir_path in system_dirs:
        if os.path.exists(dir_path):
            try:
                # Try to list contents
                files = os.listdir(dir_path)
                accessible.append(dir_path)
            except PermissionError:
                inaccessible.append(f"{dir_path} - Permission denied")
            except Exception as e:
                inaccessible.append(f"{dir_path} - {str(e)}")
        else:
            inaccessible.append(f"{dir_path} - Not found")
    
    return {
        "accessible": accessible,
        "inaccessible": inaccessible,
        "status": "ok" if not inaccessible else "issues"
    }

def check_registry_access() -> Dict[str, Any]:
    """Check if registry is accessible."""
    print("Checking registry access...")
    
    test_keys = [
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion"),
        (winreg.HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion"),
        (winreg.HKEY_CLASSES_ROOT, ".txt"),
    ]
    
    accessible = []
    inaccessible = []
    
    for hkey, subkey in test_keys:
        try:
            key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ)
            key.Close()
            accessible.append(f"{hkey.name}\\{subkey}")
        except Exception as e:
            inaccessible.append(f"{hkey.name}\\{subkey} - {str(e)}")
    
    return {
        "accessible": accessible,
        "inaccessible": inaccessible,
        "status": "ok" if not inaccessible else "issues"
    }

def check_file_explorer_settings() -> Dict[str, Any]:
    """Check File Explorer folder options."""
    print("Checking File Explorer settings...")
    
    issues = []
    
    # Check registry for hidden file settings
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced",
            0,
            winreg.KEY_READ
        )
        
        try:
            # Check Hidden setting (1 = show, 2 = hide)
            hidden = winreg.QueryValueEx(key, "Hidden")[0]
            if hidden == 2:
                issues.append("Hidden files are set to not show")
            
            # Check ShowSuperHidden (system files)
            try:
                super_hidden = winreg.QueryValueEx(key, "ShowSuperHidden")[0]
                if super_hidden == 0:
                    issues.append("System files are hidden")
            except FileNotFoundError:
                issues.append("ShowSuperHidden setting not found")
            
            # Check HideFileExt
            try:
                hide_ext = winreg.QueryValueEx(key, "HideFileExt")[0]
                if hide_ext == 1:
                    issues.append("File extensions are hidden")
            except FileNotFoundError:
                pass
                
        finally:
            key.Close()
    except Exception as e:
        issues.append(f"Cannot read File Explorer settings: {e}")
    
    return {"status": "ok" if not issues else "issues", "issues": issues}

def run_sfc_scan() -> Dict[str, Any]:
    """Run System File Checker scan."""
    print("Running System File Checker (SFC) scan...")
    print("This may take several minutes...")
    
    try:
        result = subprocess.run(
            ["sfc", "/scannow"],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        return {
            "status": "completed",
            "returncode": result.returncode,
            "output": result.stdout,
            "errors": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": "SFC scan took too long"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def generate_report() -> str:
    """Generate diagnostic report."""
    print("\n" + "=" * 60)
    print("Windows System Diagnostic Report")
    print("=" * 60 + "\n")
    
    results = {}
    
    # Run all checks
    results["file_associations"] = check_file_associations()
    results["system_file_visibility"] = check_system_file_visibility()
    results["registry_access"] = check_registry_access()
    results["file_explorer_settings"] = check_file_explorer_settings()
    
    # Generate report
    report = []
    report.append("DIAGNOSTIC RESULTS\n")
    report.append("-" * 60)
    
    for check_name, result in results.items():
        report.append(f"\n{check_name.replace('_', ' ').title()}:")
        if result.get("status") == "ok":
            report.append("  ✓ OK")
        else:
            report.append("  ✗ ISSUES FOUND")
            if "issues" in result:
                for issue in result["issues"]:
                    report.append(f"    - {issue}")
            if "inaccessible" in result:
                for item in result["inaccessible"]:
                    report.append(f"    - {item}")
    
    report.append("\n" + "-" * 60)
    report.append("\nRECOMMENDATIONS:")
    
    # Generate recommendations
    if results["file_explorer_settings"].get("status") != "ok":
        report.append("1. Run the repair tool to fix File Explorer settings")
    
    if results["file_associations"].get("status") != "ok":
        report.append("2. Run file association repair")
    
    if results["system_file_visibility"].get("status") != "ok":
        report.append("3. Check system file visibility settings")
        report.append("4. Consider running SFC /scannow as administrator")
    
    report.append("\n" + "=" * 60)
    
    return "\n".join(report)

if __name__ == "__main__":
    print("Windows System Diagnostic Tool")
    print("=" * 60)
    print("\nThis tool will check your system for file and registry issues.")
    print("It will NOT make any changes to your system.\n")
    
    input("Press Enter to continue...")
    
    report = generate_report()
    print(report)
    
    # Save report to file
    report_file = Path(__file__).parent / "diagnostic_report.txt"
    with open(report_file, "w") as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_file}")
    print("\nYou can now run the repair tool if needed.")
    
    input("\nPress Enter to exit...")

