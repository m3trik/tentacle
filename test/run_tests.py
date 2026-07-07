#!/usr/bin/python
# coding=utf-8
"""
Main test runner for tentacle package.

Three execution modes:

1. Plain Python (workstation, no Maya):
       python run_tests.py
   Maya-dependent tests skip cleanly.

2. mayapy.standalone (CI / fast iteration, no GUI):
       mayapy.exe run_tests.py --include-slots
   Initializes maya.standalone in-process. The overlay widget test still
   skips here because mayapy.standalone's Qt is a non-GUI stub.

3. Real Maya GUI (canonical "everything passes" run):
       python run_tests.py --in-maya
   Uses mayatk.MayaConnection to launch a FRESH Maya instance, dispatches
   the full suite (main + slots) over the command port, polls for
   completion, then closes Maya. Gives genuine 100% — overlay widget
   tests run against real Qt.

   Per the monorepo hard rule (mayatk/CLAUDE.md), --in-maya always uses
   force_new_instance=True. There is no --reuse path; existing Maya
   sessions are never touched.

Other flags:
    -v / --verbose      Increase verbosity
    --log               Save results to a log file
    -q / --quiet        Minimal output
    --no-badge          Skip README badge update
    --keep-maya         Keep Maya open after tests (only with --in-maya)
"""
import argparse
import datetime
import io
import os
import re
import sys
import textwrap
import time
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

    def __init__(
        self,
        test_dir: Path,
        verbosity: int = 1,
        include_slots: bool = False,
    ):
        self.test_dir = test_dir
        self.verbosity = verbosity
        self.include_slots = include_slots
        self.log_buffer = io.StringIO()

    def discover_tests(self) -> unittest.TestSuite:
        """Discover test modules — main directory plus optional slot subdir."""
        loader = unittest.TestLoader()
        suite = loader.discover(
            start_dir=str(self.test_dir),
            pattern="test_*.py",
            top_level_dir=str(self.test_dir),
        )
        if self.include_slots:
            slots_dir = self.test_dir / "slots"
            if slots_dir.is_dir():
                # Slot tests share helpers via top-level imports — make sure
                # the slots dir is on sys.path *before* discover runs.
                if str(slots_dir) not in sys.path:
                    sys.path.insert(0, str(slots_dir))
                slot_suite = loader.discover(
                    start_dir=str(slots_dir),
                    pattern="test_*.py",
                    top_level_dir=str(slots_dir),
                )
                suite.addTests(slot_suite)
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
            try:
                stream.write(text)
            except UnicodeEncodeError:
                # mayapy's console is cp1252 and can't encode every
                # character a test docstring/failure message contains
                # (arrows, em-dashes, ...). Losing those glyphs here beats
                # crashing mid-report and discarding every other result.
                encoding = getattr(stream, "encoding", None) or "ascii"
                stream.write(text.encode(encoding, errors="replace").decode(encoding))
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
        if failed == 0:
            color = "brightgreen"; status = f"{passed} passed"
        elif passed == 0:
            color = "red"; status = f"{failed} failed"
        else:
            color = "orange"; status = f"{passed} passed, {failed} failed"

        # Link target computed relative to the README's location (this runner
        # writes both README.md -> test/ and docs/README.md -> ../test/).
        test_dir = Path(__file__).resolve().parent
        link_target = Path(os.path.relpath(test_dir, readme_path.parent)).as_posix() + "/"
        new_badge = f"[![Tests](https://img.shields.io/badge/Tests-{status.replace(' ', '%20').replace(',', '')}-{color}.svg)]({link_target})"
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

def _initialize_maya_standalone():
    """Bring up an in-process Maya so slot-suite tests can run.

    Idempotent: a no-op if maya.standalone has already been initialized
    (re-running run_tests.py inside a live Maya, etc.).
    """
    try:
        import maya.standalone  # noqa: WPS433
    except ImportError as exc:
        sys.stderr.write(
            "ERROR: --include-slots requires a Maya runtime "
            "(run via mayapy.exe).\n"
            f"        Underlying error: {exc}\n"
        )
        sys.exit(2)
    try:
        maya.standalone.initialize(name="python")
    except RuntimeError:
        # Already initialized — fine.
        pass


def _ensure_ecosystem_paths(monorepo: Path):
    """Push pythontk / uitk / mayatk onto sys.path when running under mayapy.

    The slot modules import mayatk at module top level; in a fresh mayapy
    process those packages aren't on sys.path automatically.
    """
    for pkg in ("pythontk", "uitk", "mayatk"):
        p = monorepo / pkg
        if p.is_dir() and str(p) not in sys.path:
            sys.path.insert(0, str(p))


def _build_in_maya_dispatcher(test_dir: Path, monorepo: Path,
                              results_file: Path, verbosity: int) -> str:
    """Return the Python source executed inside the Maya GUI process.

    The dispatcher discovers and runs both the main suite and the slots
    subdir, writes a parseable summary to *results_file*, and signals
    completion via __main__._tentacle_test_complete so the launcher can
    poll over the command port.
    """
    monorepo_str = str(monorepo).replace("\\", "/")
    test_dir_str = str(test_dir).replace("\\", "/")
    slots_dir_str = str(test_dir / "slots").replace("\\", "/")
    results_file_str = str(results_file).replace("\\", "/")

    return textwrap.dedent(f"""
        import sys, os, io, time, datetime, traceback, unittest

        for p in (
            r'{monorepo_str}',
            r'{monorepo_str}/pythontk',
            r'{monorepo_str}/uitk',
            r'{monorepo_str}/mayatk',
            r'{monorepo_str}/tentacle',
            r'{test_dir_str}',
            r'{slots_dir_str}',
        ):
            if p not in sys.path:
                sys.path.insert(0, p)

        import __main__ as _main
        _main._tentacle_test_complete = False
        _main._tentacle_test_passed = False
        _main._tentacle_test_summary = ''

        try:
            buf = io.StringIO()

            class _Tee:
                def __init__(self, *streams): self._s = streams
                def write(self, t):
                    for s in self._s:
                        try: s.write(t)
                        except Exception: pass
                def flush(self):
                    for s in self._s:
                        try: s.flush()
                        except Exception: pass

            stream = _Tee(sys.__stdout__, buf)
            ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            stream.write('\\n' + '='*70 + '\\n')
            stream.write('Tentacle Test Suite (in Maya GUI)\\n')
            stream.write('='*70 + '\\n')
            stream.write(f'Started: {{ts}}\\n')
            stream.write('='*70 + '\\n')

            loader = unittest.TestLoader()
            suite = loader.discover(
                start_dir=r'{test_dir_str}',
                pattern='test_*.py',
                top_level_dir=r'{test_dir_str}',
            )
            slot_suite = loader.discover(
                start_dir=r'{slots_dir_str}',
                pattern='test_*.py',
                top_level_dir=r'{slots_dir_str}',
            )
            suite.addTests(slot_suite)

            t0 = time.perf_counter()
            runner = unittest.TextTestRunner(stream=stream, verbosity={verbosity})
            result = runner.run(suite)
            duration = time.perf_counter() - t0

            tests_run = result.testsRun
            failures = len(result.failures)
            errors = len(result.errors)
            skipped = len(result.skipped)
            passed = tests_run - failures - errors - skipped
            success = failures == 0 and errors == 0
            status = 'PASSED' if success else 'FAILED'
            summary = (
                f'{{status}}: {{tests_run}} tests, {{passed}} passed, '
                f'{{failures}} failed, {{errors}} errors, '
                f'{{skipped}} skipped ({{duration:.2f}}s)'
            )

            stream.write('\\n' + '='*70 + '\\n')
            stream.write(summary + '\\n')
            stream.write('='*70 + '\\n')

            if result.failures or result.errors:
                stream.write('\\nDETAILED FAILURES AND ERRORS:\\n')
                stream.write('-'*70 + '\\n')
                for t, tb in result.failures:
                    stream.write(f'\\nFAILED: {{t}}\\n{{tb}}\\n')
                for t, tb in result.errors:
                    stream.write(f'\\nERROR: {{t}}\\n{{tb}}\\n')

            with open(r'{results_file_str}', 'w', encoding='utf-8') as f:
                f.write(buf.getvalue())
                f.write('\\n--- METRICS ---\\n')
                f.write(f'tests={{tests_run}}\\nfailures={{failures}}\\n'
                        f'errors={{errors}}\\nskipped={{skipped}}\\n'
                        f'passed={{passed}}\\n')

            _main._tentacle_test_summary = summary
            _main._tentacle_test_passed = success
        except Exception:
            tb = traceback.format_exc()
            try:
                with open(r'{results_file_str}', 'w', encoding='utf-8') as f:
                    f.write('UNHANDLED ERROR IN TEST DISPATCHER\\n')
                    f.write(tb)
            except Exception:
                pass
            sys.__stderr__.write(tb)
        finally:
            _main._tentacle_test_complete = True
        """).strip()


def _run_in_maya_gui(test_dir: Path, monorepo: Path, verbosity: int,
                     no_badge: bool, keep_maya: bool, root_dir: Path) -> int:
    """Launch a FRESH Maya GUI and dispatch the full suite over command port.

    This is the canonical "100% verified" path — every test runs against
    real Qt, including the overlay widget test that mayapy.standalone
    cannot host.

    Hard rule (mayatk/CLAUDE.md): force_new_instance=True always. Never
    --reuse, never attach to a live session.
    """
    if str(monorepo) not in sys.path:
        sys.path.insert(0, str(monorepo))

    try:
        from mayatk.env_utils.maya_connection import MayaConnection
    except ImportError as exc:
        sys.stderr.write(
            f"ERROR: --in-maya requires mayatk on sys.path (looked under "
            f"{monorepo}). Underlying: {exc}\n"
        )
        return 2

    temp_dir = test_dir / "temp_tests"
    temp_dir.mkdir(exist_ok=True)
    results_file = temp_dir / "_in_maya_results.txt"
    dispatcher_file = temp_dir / "_in_maya_dispatcher.py"
    if results_file.exists():
        results_file.unlink()

    dispatcher_code = _build_in_maya_dispatcher(
        test_dir, monorepo, results_file, verbosity
    )
    dispatcher_file.write_text(dispatcher_code, encoding="utf-8")

    print("\n" + "=" * 70)
    print("Tentacle Test Suite — launching FRESH Maya GUI")
    print("=" * 70)
    print("A new Maya instance is being launched on an unused port.")
    print("Existing Maya sessions are NOT touched (per monorepo hard rule).")
    print("Maya UI startup typically takes 30-60s; tests follow.")
    print("=" * 70)

    conn = MayaConnection.get_instance()
    if not conn.connect(
        mode="auto",
        force_new_instance=True,  # HARD RULE — never False
        launch=True,
        confirm_existing=True,
    ):
        sys.stderr.write("[ERROR] Could not launch / connect to Maya.\n")
        return 2

    if conn.mode != "port":
        sys.stderr.write(
            f"[ERROR] Expected port mode for fresh Maya GUI launch, got "
            f"mode={conn.mode!r}.\n"
        )
        return 2

    print(f"[OK] Connected to Maya in {conn.mode} mode (port={conn.port})")

    try:
        # Send a small bootstrap that imports the on-disk dispatcher.
        # Keeps the wire payload trivial regardless of dispatcher size.
        temp_dir_str = str(temp_dir).replace("\\", "/")
        bootstrap = (
            f"import sys\n"
            f"if r'{temp_dir_str}' not in sys.path:\n"
            f"    sys.path.insert(0, r'{temp_dir_str}')\n"
            f"if '_in_maya_dispatcher' in sys.modules:\n"
            f"    del sys.modules['_in_maya_dispatcher']\n"
            f"import _in_maya_dispatcher  # runs the suite at import time\n"
        )
        print("\n[INFO] Dispatching test suite to Maya...\n")
        conn.execute(bootstrap, wait_for_response=False)

        # Poll for completion via socket sentinel.
        timeout = 600
        poll = 2.0
        start = time.monotonic()
        last_size = 0
        print(f"Waiting for tests to finish (timeout: {timeout}s) ...")

        while (time.monotonic() - start) < timeout:
            elapsed = int(time.monotonic() - start)
            try:
                done = conn.execute(
                    "getattr(__import__('__main__'), "
                    "'_tentacle_test_complete', False)",
                    wait_for_response=True,
                    timeout=5,
                )
                if done and str(done).strip().lower() == "true":
                    summary = conn.execute(
                        "getattr(__import__('__main__'), "
                        "'_tentacle_test_summary', '')",
                        wait_for_response=True,
                        timeout=5,
                    ) or ""
                    passed_flag = conn.execute(
                        "getattr(__import__('__main__'), "
                        "'_tentacle_test_passed', False)",
                        wait_for_response=True,
                        timeout=5,
                    )
                    print(f"\n  Tests finished in {elapsed}s")
                    print(f"  Maya reports: {summary.strip()}")

                    if results_file.exists():
                        print("\n" + "-" * 70)
                        print("IN-MAYA OUTPUT")
                        print("-" * 70)
                        try:
                            content = results_file.read_text(encoding="utf-8")
                            try:
                                print(content)
                            except UnicodeEncodeError:
                                # Windows cp1252 console can't render UTF-8
                                # arrows etc. — fall back to a safe write.
                                enc = (sys.stdout.encoding or "ascii")
                                sys.stdout.write(
                                    content.encode(enc, errors="replace")
                                    .decode(enc)
                                )
                                sys.stdout.write("\n")
                        except Exception as e:
                            print(f"[WARN] Could not read results: {e}")

                        if not no_badge:
                            content = results_file.read_text(encoding="utf-8")
                            mp = re.search(r"^passed=(\d+)$", content, re.MULTILINE)
                            mf = re.search(r"^failures=(\d+)$", content, re.MULTILINE)
                            me = re.search(r"^errors=(\d+)$", content, re.MULTILINE)
                            if mp and mf and me:
                                p = int(mp.group(1))
                                f_ = int(mf.group(1)) + int(me.group(1))
                                for cand in (
                                    root_dir / "docs" / "README.md",
                                    root_dir / "README.md",
                                ):
                                    if cand.exists():
                                        update_readme_badge(p, f_, cand)
                                        break

                    return 0 if str(passed_flag).strip().lower() == "true" else 1
            except Exception:
                pass

            if results_file.exists():
                try:
                    cur = results_file.stat().st_size
                    if cur != last_size:
                        print(
                            f"\r  [{elapsed}s] writing results "
                            f"({cur} bytes) ...",
                            end="",
                            flush=True,
                        )
                        last_size = cur
                except Exception:
                    pass

            time.sleep(poll)

        print(f"\n[TIMEOUT] No completion after {timeout}s.")
        if results_file.exists():
            print("\n[PARTIAL]")
            print(results_file.read_text(encoding="utf-8"))
        return 2
    finally:
        if not keep_maya and conn.is_connected:
            print("\nClosing Maya instance ...")
            try:
                conn.shutdown(force=True)
                print("[OK] Maya closed.")
            except Exception as e:
                print(f"[WARN] Failed to close Maya gracefully: {e}")


def main():
    parser = argparse.ArgumentParser(description="Run tentacle test suite")
    parser.add_argument("-v", "--verbose", action="count", default=1, help="Increase verbosity")
    parser.add_argument("--log", action="store_true", help="Save results to a log file")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--no-badge", action="store_true", help="Skip updating README badge")
    parser.add_argument(
        "--include-slots",
        action="store_true",
        help="Also run the Maya-required slot migration tests "
        "(requires mayapy / maya.standalone). Initializes maya.standalone "
        "automatically.",
    )
    parser.add_argument(
        "--in-maya",
        action="store_true",
        help="Launch a FRESH Maya GUI via mayatk.MayaConnection and run the "
        "full suite (main + slots) inside it via the command port. "
        "This is the canonical 100%% verified path — gives genuine pass on "
        "the overlay widget test that mayapy.standalone cannot host. "
        "Always uses force_new_instance=True (per monorepo hard rule).",
    )
    parser.add_argument(
        "--keep-maya",
        action="store_true",
        help="Keep the launched Maya open after tests (only with --in-maya).",
    )
    args = parser.parse_args()

    verbosity = 0 if args.quiet else args.verbose
    test_dir = Path(__file__).parent
    root_dir = test_dir.parent
    monorepo = root_dir.parent

    # Ensure root and test dirs are in path
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    if str(test_dir) not in sys.path:
        sys.path.insert(0, str(test_dir))

    # --in-maya: hand off to the GUI launcher and exit.
    if args.in_maya:
        if args.include_slots:
            sys.stderr.write(
                "ERROR: --in-maya and --include-slots are mutually exclusive. "
                "--in-maya already runs the full suite (main + slots) "
                "inside Maya GUI.\n"
            )
            sys.exit(2)
        sys.exit(_run_in_maya_gui(
            test_dir, monorepo, verbosity,
            no_badge=args.no_badge,
            keep_maya=args.keep_maya,
            root_dir=root_dir,
        ))

    # Maya-bound: bootstrap maya.standalone and the ecosystem packages.
    if args.include_slots:
        _ensure_ecosystem_paths(monorepo)
        _initialize_maya_standalone()

    # Try to verify package import
    try:
        if (root_dir / "tentacle").exists():
             import tentacle
             print(f"DEBUG: tentacle imported from: {getattr(tentacle, '__file__', 'namespace')}")
    except ImportError:
        print("DEBUG: Could not import tentacle")

    runner = TestRunner(test_dir, verbosity=verbosity, include_slots=args.include_slots)
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
