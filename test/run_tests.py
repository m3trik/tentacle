#!/usr/bin/python
# coding=utf-8
"""
Main test runner for tentacle package.

This script discovers and runs all test modules, collecting results
and outputting them to both console and a log file. It also updates
the README.md badge with test results.

Run with:
    python run_tests.py
    python run_tests.py -v          # Verbose output
    python run_tests.py --log       # Enable log file output
    python run_tests.py -v --log    # Both
    python run_tests.py --no-badge  # Skip README badge update
"""
import argparse
import datetime
import io
import os
import re
import sys
import unittest
from pathlib import Path

class TestResult:
    """Container for test result statistics."""

    def __init__(self, result: unittest.TestResult, duration: float):
        self.tests_run = result.testsRun
        self.failures = len(result.failures)
        self.errors = len(result.errors)
        self.skipped = len(result.skipped)
        self.passed = self.tests_run - self.failures - self.errors - self.skipped
        self.duration = duration
        self.failure_details = result.failures
        self.error_details = result.errors
        self.success = self.failures == 0 and self.errors == 0

    @property
    def summary(self) -> str:
        """Return a one-line summary of results."""
        status = "PASSED" if self.success else "FAILED"
        return (
            f"{status}: {self.tests_run} tests, "
            f"{self.passed} passed, "
            f"{self.failures} failed, "
            f"{self.errors} errors, "
            f"{self.skipped} skipped "
            f"({self.duration:.2f}s)"
        )

class TestRunner:
    """Discovers and runs all test modules."""

    def __init__(self, test_dir: Path, verbosity: int = 1):
        self.test_dir = test_dir
        self.verbosity = verbosity
        self.log_buffer = io.StringIO()

    def discover_tests(self) -> unittest.TestSuite:
        """Discover all test modules in the test directory."""
        loader = unittest.TestLoader()
        suite = loader.discover(
            start_dir=str(self.test_dir),
            pattern="test_*.py",
            top_level_dir=str(self.test_dir),
        )
        return suite

    def run(self, log_to_file: bool = False) -> TestResult:
        """Run all discovered tests and collect results."""
        suite = self.discover_tests()

        # Create stream that writes to both console and buffer
        stream = TeeStream(sys.stdout, self.log_buffer)

        # Print header
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"""
{'=' * 70}
Tentacle Test Suite
{'=' * 70}
Started: {timestamp}
Test Directory: {self.test_dir}
{'=' * 70}
"""
        stream.write(header)

        # Run tests
        import time
        start_time = time.perf_counter()

        runner = unittest.TextTestRunner(
            stream=stream, verbosity=self.verbosity, resultclass=DetailedTestResult
        )
        result = runner.run(suite)

        duration = time.perf_counter() - start_time
        test_result = TestResult(result, duration)

        # Print footer
        footer = f"""
{'=' * 70}
{test_result.summary}
{'=' * 70}
"""
        stream.write(footer)

        if test_result.failure_details or test_result.error_details:
            stream.write("\nDETAILED FAILURES AND ERRORS:\n")
            stream.write("-" * 70 + "\n")
            for test, traceback in test_result.failure_details:
                stream.write(f"\nFAILED: {test}\n")
                stream.write(traceback)
                stream.write("\n")
            for test, traceback in test_result.error_details:
                stream.write(f"\nERROR: {test}\n")
                stream.write(traceback)
                stream.write("\n")

        if log_to_file:
            self._save_log(timestamp)

        return test_result

    def _save_log(self, timestamp: str):
        log_dir = self.test_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        safe_timestamp = timestamp.replace(":", "-").replace(" ", "_")
        log_file = log_dir / f"test_results_{safe_timestamp}.log"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(self.log_buffer.getvalue())
        print(f"\nLog saved to: {log_file}")

class TeeStream:
    """Stream that writes to multiple outputs."""
    def __init__(self, *streams):
        self.streams = streams
    def write(self, text):
        for stream in self.streams:
            stream.write(text)
    def flush(self):
        for stream in self.streams:
            stream.flush()

class DetailedTestResult(unittest.TextTestResult):
    """Extended test result with better output formatting."""
    def addSuccess(self, test):
        super().addSuccess(test)
        if self.showAll: self.stream.write(" ok\n")
        elif self.dots: self.stream.write("."); self.stream.flush()
    def addError(self, test, err):
        super().addError(test, err)
        if self.showAll: self.stream.write(" ERROR\n")
        elif self.dots: self.stream.write("E"); self.stream.flush()
    def addFailure(self, test, err):
        super().addFailure(test, err)
        if self.showAll: self.stream.write(" FAIL\n")
        elif self.dots: self.stream.write("F"); self.stream.flush()
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        if self.showAll: self.stream.write(f" skipped ({reason})\n")
        elif self.dots: self.stream.write("s"); self.stream.flush()

def update_readme_badge(passed: int, failed: int, readme_path: Path) -> bool:
    if not readme_path.exists():
        print(f"README not found at {readme_path}")
        return False
    
    try:
        content = readme_path.read_text(encoding="utf-8")
        total = passed + failed
        if failed == 0:
            color = "brightgreen"; status = f"{passed} passed"
        elif passed == 0:
            color = "red"; status = f"{failed} failed"
        else:
            color = "orange"; status = f"{passed} passed, {failed} failed"

        new_badge = f"[![Tests](https://img.shields.io/badge/Tests-{status.replace(' ', '%20').replace(',', '')}-{color}.svg)](test/)"
        tests_badge_pattern = r"\[!\[Tests\]\(https://img\.shields\.io/badge/Tests-[^\)]+\)\]\([^\)]+\)"

        if re.search(tests_badge_pattern, content):
            new_content = re.sub(tests_badge_pattern, new_badge, content)
        else:
            python_badge_pattern = r"(\[!\[Python\]\(https://img\.shields\.io/badge/Python-[^\)]+\)\]\([^\)]+\))"
            match = re.search(python_badge_pattern, content)
            if match:
                insert_pos = match.end()
                new_content = content[:insert_pos] + "\n" + new_badge + content[insert_pos:]
            else:
                new_content = new_badge + "\n" + content

        readme_path.write_text(new_content, encoding="utf-8")
        print(f"\nREADME badge updated: {status}")
        return True
    except Exception as e:
        print(f"Failed to update badge: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run tentacle test suite")
    parser.add_argument("-v", "--verbose", action="count", default=1, help="Increase verbosity")
    parser.add_argument("--log", action="store_true", help="Save results to a log file")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--no-badge", action="store_true", help="Skip updating README badge")
    args = parser.parse_args()

    verbosity = 0 if args.quiet else args.verbose
    test_dir = Path(__file__).parent
    root_dir = test_dir.parent

    # Ensure root and test dirs are in path
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    if str(test_dir) not in sys.path:
        sys.path.insert(0, str(test_dir))

    # Try to verify package import
    try:
        if (root_dir / "tentacle").exists():
             import tentacle
             print(f"DEBUG: tentacle imported from: {getattr(tentacle, '__file__', 'namespace')}")
    except ImportError:
        print("DEBUG: Could not import tentacle")

    runner = TestRunner(test_dir, verbosity=verbosity)
    result = runner.run(log_to_file=args.log)

    if not args.no_badge:
        # Check standard locations for README
        possible_readmes = [root_dir / "docs" / "README.md", root_dir / "README.md"]
        for p in possible_readmes:
            if p.exists():
                update_readme_badge(result.passed, result.failures + result.errors, p)
                break

    sys.exit(0 if result.success else 1)

if __name__ == "__main__":
    main()
