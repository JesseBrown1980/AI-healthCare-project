"""
Test Result Logger
Captures and logs test execution details for monitoring and analysis.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pytest


class TestResultLogger:
    """
    Logs test results with timing, assertions, and metadata.
    
    Usage:
        logger = TestResultLogger()
        logger.start_test("test_example")
        # ... test runs ...
        logger.end_test("test_example", passed=True)
        logger.save_report()
    """
    
    def __init__(self, output_dir: str = "test-reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results: List[Dict[str, Any]] = []
        self.current_test: Optional[Dict[str, Any]] = None
        self.session_start: float = time.time()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def start_test(self, test_name: str, markers: List[str] = None):
        """Mark the start of a test."""
        self.current_test = {
            "name": test_name,
            "markers": markers or [],
            "start_time": time.time(),
            "start_timestamp": datetime.now().isoformat(),
        }
    
    def end_test(
        self,
        test_name: str,
        passed: bool,
        error: Optional[str] = None,
        duration: Optional[float] = None,
    ):
        """Mark the end of a test and record results."""
        if self.current_test and self.current_test["name"] == test_name:
            end_time = time.time()
            self.current_test.update({
                "passed": passed,
                "error": error,
                "duration": duration or (end_time - self.current_test["start_time"]),
                "end_timestamp": datetime.now().isoformat(),
            })
            self.results.append(self.current_test)
            self.current_test = None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all test results."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("passed", False))
        failed = total - passed
        
        durations = [r.get("duration", 0) for r in self.results]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "session_id": self.session_id,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "N/A",
            "total_duration": sum(durations),
            "avg_duration": avg_duration,
            "slowest_tests": sorted(
                self.results,
                key=lambda x: x.get("duration", 0),
                reverse=True
            )[:5],
        }
    
    def save_report(self, filename: Optional[str] = None) -> Path:
        """Save the test results to a JSON file."""
        if filename is None:
            filename = f"test_results_{self.session_id}.json"
        
        report_path = self.output_dir / filename
        
        report = {
            "summary": self.get_summary(),
            "results": self.results,
            "generated_at": datetime.now().isoformat(),
        }
        
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        return report_path
    
    def print_summary(self):
        """Print a summary to console."""
        summary = self.get_summary()
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} | Failed: {summary['failed']}")
        print(f"Pass Rate: {summary['pass_rate']}")
        print(f"Total Duration: {summary['total_duration']:.2f}s")
        print(f"Average Duration: {summary['avg_duration']:.3f}s")
        print("\nSlowest Tests:")
        for i, test in enumerate(summary['slowest_tests'], 1):
            print(f"  {i}. {test['name']}: {test.get('duration', 0):.3f}s")
        print("=" * 60 + "\n")


# Pytest plugin hooks
_logger = None


def pytest_configure(config):
    """Initialize the logger at session start."""
    global _logger
    _logger = TestResultLogger()


def pytest_runtest_setup(item):
    """Called before each test."""
    if _logger:
        markers = [m.name for m in item.iter_markers()]
        _logger.start_test(item.nodeid, markers=markers)


def pytest_runtest_makereport(item, call):
    """Called after each test phase (setup, call, teardown)."""
    if call.when == "call" and _logger:
        passed = call.excinfo is None
        error = str(call.excinfo.value) if call.excinfo else None
        _logger.end_test(
            item.nodeid,
            passed=passed,
            error=error,
            duration=call.duration,
        )


def pytest_sessionfinish(session, exitstatus):
    """Called at the end of the test session."""
    if _logger:
        _logger.print_summary()
        report_path = _logger.save_report()
        print(f"Test results saved to: {report_path}")
