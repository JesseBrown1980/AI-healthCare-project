"""
Test script to validate Windows build components without actually building.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    errors = []
    
    try:
        from windows_build.version import get_version, get_version_info, compare_versions
        print(f"✓ Version module: {get_version()}")
    except Exception as e:
        errors.append(f"Version module: {e}")
    
    try:
        from windows_build.auto_update import UpdateChecker, UpdateService
        print("✓ Auto-update module")
    except Exception as e:
        errors.append(f"Auto-update module: {e}")
    
    try:
        import tkinter
        print("✓ tkinter available")
    except Exception as e:
        errors.append(f"tkinter: {e}")
    
    try:
        import httpx
        print("✓ httpx available")
    except Exception as e:
        errors.append(f"httpx: {e}")
    
    try:
        import asyncio
        print("✓ asyncio available")
    except Exception as e:
        errors.append(f"asyncio: {e}")
    
    if errors:
        print("\n✗ Import errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✓ All imports successful!")
        return True

def test_version_functions():
    """Test version comparison functions."""
    print("\nTesting version functions...")
    try:
        from windows_build.version import get_version, compare_versions
        
        version = get_version()
        print(f"✓ Current version: {version}")
        
        # Test version comparison
        result = compare_versions("1.0.0", "1.0.1")
        assert result == -1, "Version comparison failed"
        print("✓ Version comparison works")
        
        result = compare_versions("1.0.1", "1.0.0")
        assert result == 1, "Version comparison failed"
        
        result = compare_versions("1.0.0", "1.0.0")
        assert result == 0, "Version comparison failed"
        
        return True
    except Exception as e:
        print(f"✗ Version function test failed: {e}")
        return False

def test_update_checker():
    """Test update checker initialization."""
    print("\nTesting update checker...")
    try:
        from windows_build.auto_update import UpdateChecker
        
        checker = UpdateChecker()
        print(f"✓ UpdateChecker initialized")
        print(f"  - Current version: {checker.current_version}")
        print(f"  - Update URL: {checker.update_url}")
        print(f"  - App directory: {checker.app_dir}")
        
        return True
    except Exception as e:
        print(f"✗ Update checker test failed: {e}")
        return False

def test_launcher_import():
    """Test launcher can be imported."""
    print("\nTesting launcher import...")
    try:
        # Don't actually instantiate it (would open GUI)
        import windows_build.windows_launcher
        print("✓ Launcher module imports successfully")
        return True
    except Exception as e:
        print(f"✗ Launcher import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_spec_file():
    """Test PyInstaller spec file syntax."""
    print("\nTesting PyInstaller spec file...")
    try:
        spec_path = Path(__file__).parent / "healthcare_ai.spec"
        if not spec_path.exists():
            print("✗ Spec file not found")
            return False
        
        # Try to parse it (basic syntax check)
        with open(spec_path, 'r') as f:
            content = f.read()
        
        # Check for required elements
        required = ['Analysis', 'EXE', 'PYZ']
        for req in required:
            if req not in content:
                print(f"✗ Spec file missing {req}")
                return False
        
        print("✓ Spec file syntax looks valid")
        return True
    except Exception as e:
        print(f"✗ Spec file test failed: {e}")
        return False

def test_file_structure():
    """Test that required files exist."""
    print("\nTesting file structure...")
    build_dir = Path(__file__).parent
    required_files = [
        "version.py",
        "auto_update.py",
        "windows_launcher.py",
        "healthcare_ai.spec",
        "installer.iss",
        "build_windows.bat",
        "README.md",
    ]
    
    missing = []
    for file in required_files:
        if not (build_dir / file).exists():
            missing.append(file)
    
    if missing:
        print(f"✗ Missing files: {', '.join(missing)}")
        return False
    else:
        print("✓ All required files present")
        return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("Windows Build System Test")
    print("=" * 60)
    
    results = []
    results.append(("File Structure", test_file_structure()))
    results.append(("Imports", test_imports()))
    results.append(("Version Functions", test_version_functions()))
    results.append(("Update Checker", test_update_checker()))
    results.append(("Launcher Import", test_launcher_import()))
    results.append(("Spec File", test_spec_file()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Build system is ready.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please fix issues before building.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

