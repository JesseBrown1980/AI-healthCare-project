"""
Test runner script for Healthcare AI Assistant.
Runs all tests and generates coverage report.
"""

import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run a command and display results."""
    print(f"\n{'=' * 60}")
    print(f"{description}")
    print(f"{'=' * 60}\n")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def main():
    """Run test suite."""
    print("Healthcare AI Assistant - Test Suite")
    print("=" * 60)
    
    # Check if pytest is installed
    try:
        import pytest
        print(f"✓ pytest version: {pytest.__version__}")
    except ImportError:
        print("✗ pytest not installed. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio", "pytest-cov"])
    
    results = []
    
    # Run existing tests
    print("\n1. Running existing test suite...")
    results.append(("Existing Tests", run_command(
        "pytest tests/ -v --tb=short -x",
        "Existing Test Suite"
    )))
    
    # Run new auth tests
    print("\n2. Running authentication tests...")
    results.append(("Auth Tests", run_command(
        "pytest tests/test_auth.py -v",
        "Authentication Tests"
    )))
    
    # Run calendar tests
    print("\n3. Running calendar integration tests...")
    results.append(("Calendar Tests", run_command(
        "pytest tests/test_calendar_integration.py -v",
        "Calendar Integration Tests"
    )))
    
    # Run email tests
    print("\n4. Running email service tests...")
    results.append(("Email Tests", run_command(
        "pytest tests/test_email_service.py -v",
        "Email Service Tests"
    )))
    
    # Run graph visualization tests
    print("\n5. Running graph visualization tests...")
    results.append(("Graph Tests", run_command(
        "pytest tests/test_graph_visualization.py -v",
        "Graph Visualization Tests"
    )))
    
    # Run auto-update tests
    print("\n6. Running auto-update tests...")
    results.append(("Auto-Update Tests", run_command(
        "pytest tests/test_auto_update.py -v",
        "Auto-Update Tests"
    )))
    
    # Generate coverage report
    print("\n7. Generating coverage report...")
    results.append(("Coverage Report", run_command(
        "pytest --cov=backend --cov=windows_build --cov-report=term --cov-report=html -q",
        "Coverage Report"
    )))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        print("Coverage report generated in: htmlcov/index.html")
        return 0
    else:
        print(f"\n✗ {total - passed} test suite(s) failed.")
        print("Review errors above and fix issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

