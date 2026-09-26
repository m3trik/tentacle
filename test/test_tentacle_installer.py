# !/usr/bin/python
# coding=utf-8
"""Tests for ``tentacle_installer.py`` -- the one-file install / update / uninstall for Maya and Blender.

Structural and mocked tests run anywhere. The clean-room live tests drive the REAL entry
points (Blender's add-on install/enable and its preferences verbs, Maya's drop hook and the
command line) in fresh DCC processes whose environment hides this machine's dev checkouts
(``PYTHONPATH`` stripped, ``PYTHONUSERBASE`` and the DCC user dir pointed at temp) -- so they
provision from PyPI exactly as an end user's machine would, PySide6 included (~100 MB for
Blender). They are gated behind ``TENTACLE_LIVE_INSTALL=1`` because of that download; run them
after any change to the installer or to ``pythontk.PackageManager.install_targeted``.
"""

import ast
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent / "tentacle"
INSTALLER = PACKAGE / "tentacle_installer.py"
TCL_BLENDER = PACKAGE / "tcl_blender.py"
TEMP = HERE / "temp_tests" / "tentacle_installer"
LIVE = os.environ.get("TENTACLE_LIVE_INSTALL") == "1"
LIVE_TIMEOUT = 1200  # PySide6 for a fresh interpreter is a big download


def _load():
    """A fresh module object each time -- the class keeps worker/timer state."""
    spec = importlib.util.spec_from_file_location("tentacle_installer", INSTALLER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _clean_env(userbase, **extra):
    """An end user's environment: no dev checkouts on PYTHONPATH, a private user site."""
    drop = {
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONSTARTUP",
        "PYTHONUSERBASE",
        "TENTACLE_MONOREPO",
        "TENTACLE_QT_DEPS",
    }
    env = {k: v for k, v in os.environ.items() if k not in drop}
    env["PYTHONUSERBASE"] = str(userbase)
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env.update(extra)
    return env


def _under(path, root):
    return os.path.normcase(os.path.normpath(path)).startswith(
        os.path.normcase(os.path.normpath(root))
    )


def _write_dist(target, name, version, record=()):
    """A minimal dist-info for *name* in *target*, the way ``pip --target`` leaves one.

    *record* lists RECORD paths as pip writes them -- staging-relative, so a console
    script reads ``../../bin/<name>.exe``.
    """
    info = Path(target) / f"{name}-{version}.dist-info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
    )
    if record:
        (info / "RECORD").write_text("".join(f"{path},,\n" for path in record))
    return info


def _find_blender():
    if sys.platform != "win32":
        return None
    root = (
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Blender Foundation"
    )
    found = sorted(root.glob("Blender */blender.exe")) if root.is_dir() else []
    return str(found[-1]) if found else None


def _find_mayapy():
    if sys.platform != "win32":
        return None
    root = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Autodesk"
    found = sorted(root.glob("Maya20*/bin/mayapy.exe")) if root.is_dir() else []
    return str(found[-1]) if found else None


def _write_wheel(folder, name, version, files):
    """A minimal pure-Python wheel pip will install: METADATA, WHEEL and a hashed RECORD."""
    import base64
    import hashlib
    import zipfile

    info = f"{name}-{version}.dist-info"
    contents = dict(files)
    contents[f"{info}/METADATA"] = (
        f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
    )
    contents[f"{info}/WHEEL"] = (
        "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    )
    record = []
    for path, text in contents.items():
        data = text.encode("utf-8")
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
        record.append(f"{path},sha256={digest.decode()},{len(data)}")
    record.append(f"{info}/RECORD,,")
    wheel = Path(folder) / f"{name}-{version}-py3-none-any.whl"
    wheel.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel, "w") as zf:
        for path, text in contents.items():
            zf.writestr(path, text)
        zf.writestr(f"{info}/RECORD", "\n".join(record) + "\n")
    return wheel


class TestBootstrapTarget(unittest.TestCase):
    """The pythontk bootstrap hands pip its target as ``PIP_TARGET``, never on argv.

    mayapy.exe decodes its ANSI command line as UTF-8: measured on Maya 2025, an
    accented letter arrived as a lone surrogate and Cyrillic as "???", while the
    environment arrived intact. Under the prefs dir of a user named José,
    ``--target <site>`` sent pip to a DIFFERENT directory and the install failed with
    "No module named 'pythontk'" (the live clean room, run under such a dir).
    """

    def setUp(self):
        self.installer = _load().TentacleInstaller

    def test_the_target_travels_in_the_environment(self):
        target = "X:/Users/José/site"
        with mock.patch.object(self.installer, "_run_checked") as run:
            self.installer._bootstrap_pythontk("PY", target)
        command, env = run.call_args.args[0], run.call_args.kwargs["env"]
        self.assertTrue(all(part.isascii() for part in command), command)
        self.assertNotIn("--target", command)
        self.assertEqual(command[-1], "pythontk")
        self.assertEqual(env["PIP_TARGET"], target)

    @unittest.skipUnless(_find_mayapy(), "mayapy.exe not installed")
    def test_mayapy_installs_into_a_non_ascii_target(self):
        """The measured failure itself, through the real mayapy and offline: a stand-in
        pythontk wheel lands in a site dir named like José's, and nowhere else (on the
        argv route pip wrote a mangled sibling of that dir)."""
        root = TEMP / "bootstrap_target"
        shutil.rmtree(root, ignore_errors=True)
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        wheel = _write_wheel(
            root / "wheels", "pythontk", "99.0", {"pythontk/__init__.py": "PROBE = 1\n"}
        )
        prefs = "José Ångström"
        target = root / prefs / "site"
        offline = {
            "PIP_FIND_LINKS": str(wheel.parent),
            "PIP_NO_INDEX": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        }
        with mock.patch.dict(os.environ, offline):
            self.installer._bootstrap_pythontk(_find_mayapy(), str(target))
        self.assertEqual(
            (target / "pythontk" / "__init__.py").read_text(), "PROBE = 1\n"
        )
        self.assertEqual(
            sorted(p.name for p in root.iterdir()), sorted([prefs, "wheels"])
        )


class TestStructure(unittest.TestCase):
    """The file is imported by three loaders before anything is called: it must be inert."""

    def setUp(self):
        self.tree = ast.parse(INSTALLER.read_text(encoding="utf-8"))

    def test_import_has_no_side_effects(self):
        allowed = (ast.Import, ast.ImportFrom, ast.ClassDef, ast.FunctionDef)
        for node in self.tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                continue  # docstring
            if isinstance(node, ast.Assign) and [t.id for t in node.targets] == [
                "bl_info"
            ]:
                continue
            if isinstance(node, ast.If):  # the ``__main__`` guard only
                self.assertIn("__main__", ast.unparse(node.test))
                continue
            self.assertIsInstance(
                node,
                allowed,
                f"module-level statement at line {node.lineno} runs at import",
            )

    def test_host_entry_points(self):
        names = {n.name for n in self.tree.body if isinstance(n, ast.FunctionDef)}
        self.assertTrue(
            {"register", "unregister", "onMayaDroppedPythonFile"} <= names, names
        )
        module = _load()
        for key in ("name", "blender", "version", "category"):
            self.assertIn(key, module.bl_info)

    def test_logic_lives_on_the_class(self):
        # Entry points delegate; every function body is a docstring plus at most two calls.
        for node in self.tree.body:
            if isinstance(node, ast.FunctionDef):
                stmts = [
                    s
                    for s in node.body
                    if not (
                        isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                    )
                ]
                self.assertLessEqual(
                    len(stmts),
                    2,
                    f"{node.name} carries logic; move it onto TentacleInstaller",
                )

    def test_qt_specs_match_tcl_blender(self):
        """One list of Qt requirements, in two files: pin them together."""
        tree = ast.parse(TCL_BLENDER.read_text(encoding="utf-8"))
        specs = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "_QtBootstrap":
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == "QT_SPECS"
                        for t in stmt.targets
                    ):
                        specs = tuple(ast.literal_eval(stmt.value))
        self.assertIsNotNone(specs, "_QtBootstrap.QT_SPECS not found in tcl_blender.py")
        self.assertEqual(_load().TentacleInstaller.QT_SPECS, specs)

    def test_specs_per_host_and_update_never_names_qt(self):
        installer = _load().TentacleInstaller
        self.assertEqual(installer.specs("maya"), ["tentacletk[maya]"])
        self.assertEqual(
            installer.specs("blender"), ["tentacletk[blender]", "PySide6", "qtpy"]
        )
        self.assertEqual(
            installer.specs("blender", fresh=False),
            ["tentacletk[blender]"],
            "an update with --upgrade must not pull a newer Qt nobody asked for",
        )

    def test_a_bare_folder_is_not_an_install(self):
        """``mayapy -c`` run from the monorepo put the repo root on sys.path[0]: every repo
        folder resolved as an EMPTY namespace package and the installer skipped the install."""
        installer = _load().TentacleInstaller
        root = TEMP / "namespace"
        shutil.rmtree(root, ignore_errors=True)
        (root / "ghostpkg").mkdir(parents=True)
        (root / "realpkg").mkdir()
        (root / "realpkg" / "__init__.py").write_text("")
        sys.path.insert(0, str(root))
        try:
            self.assertFalse(
                installer._has("ghostpkg"), "a folder without __init__ is not a package"
            )
            self.assertTrue(installer._has("realpkg"))
            self.assertFalse(installer._has("no_such_package_anywhere"))
        finally:
            sys.path.remove(str(root))
            shutil.rmtree(root, ignore_errors=True)

    def test_outside_a_dcc_is_an_error(self):
        installer = _load().TentacleInstaller
        with mock.patch.object(installer, "host", return_value=None):
            with self.assertRaises(RuntimeError):
                installer.ensure_and_launch()
            self.assertEqual(installer.main(["install"]), 2)

    def test_unknown_verb_is_rejected(self):
        installer = _load().TentacleInstaller
        with self.assertRaises(ValueError):
            installer.request("maya", "reinstall")

    def test_blender_popup_shows_every_line(self):
        """Blender's popup showed the first line only, so "could not be installed:"
        arrived without the reason that followed it on the next line."""
        installer = _load().TentacleInstaller
        labels = []

        def popup_menu(draw, title, icon):
            menu = mock.MagicMock()
            menu.layout.label.side_effect = lambda **kw: labels.append(kw["text"])
            draw(menu, None)

        fake_bpy = types.ModuleType("bpy")
        fake_bpy.context = mock.MagicMock()
        fake_bpy.context.window_manager.popup_menu.side_effect = popup_menu
        fake_bpy.app = mock.MagicMock()
        with (
            mock.patch.dict(sys.modules, {"bpy": fake_bpy}),
            mock.patch.object(installer, "headless", return_value=False),
        ):
            installer._say(
                "blender",
                "Tentacle could not be installed:\nno route to PyPI",
                error=True,
            )
            fake_bpy.app.timers.register.call_args.args[0]()  # the deferred popup
        self.assertEqual(
            labels, ["Tentacle could not be installed:", "no route to PyPI"]
        )

    def test_a_blender_message_waits_for_a_window(self):
        """``popup_menu`` needs a window, and ``register()`` at start has none.

        Measured on 5.1.2 (GUI, called from an enabled add-on's register() at start):
        it raised 'context "window" is None', so the report of a pending uninstall
        completed at start -- warnings included -- reached only the system console,
        which Windows hides. From a timer the same popup renders (measured, by
        screenshot), so the popup always goes out on a persistent timer.
        """
        installer = _load().TentacleInstaller
        fake_bpy = types.ModuleType("bpy")
        fake_bpy.context = mock.MagicMock()
        fake_bpy.app = mock.MagicMock()
        with (
            mock.patch.dict(sys.modules, {"bpy": fake_bpy}),
            mock.patch.object(installer, "headless", return_value=False),
        ):
            installer._say("blender", "Tentacle uninstalled")
            fake_bpy.context.window_manager.popup_menu.assert_not_called()
            register = fake_bpy.app.timers.register
            self.assertIs(register.call_args.kwargs.get("persistent"), True)
            self.assertIsNone(register.call_args.args[0](), "a one-shot, not a poll")
        fake_bpy.context.window_manager.popup_menu.assert_called_once()

    def test_every_blender_timer_survives_a_file_load(self):
        """A default ``bpy.app.timers`` timer is dropped when Blender loads a .blend, and
        Blender enables add-ons BEFORE it opens the file a user double-clicked.

        Measured on 5.1.2, GUI, timers registered from register() at start with a .blend
        on the command line: the default one never fired, a ``persistent=True`` one did.
        Here that meant no report and no launch after a first install or a pending
        update, and a pending uninstall that removed the packages but never the add-on
        -- which then reinstalled everything at the next start.
        """
        calls = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Call)
            and ast.unparse(node.func).endswith("timers.register")
        ]
        self.assertTrue(
            calls, "no bpy.app.timers.register call found: the scan is stale"
        )
        for call in calls:
            persistent = {kw.arg: kw.value for kw in call.keywords}.get("persistent")
            self.assertTrue(
                isinstance(persistent, ast.Constant) and persistent.value is True,
                f"line {call.lineno}: {ast.unparse(call)} must pass persistent=True",
            )

    def test_mayapy_is_found_where_maya_keeps_it(self):
        """Beside the binary on Windows and Linux; under ``MAYA_LOCATION`` on macOS, where
        the binary is ``Maya.app/Contents/MacOS/Maya`` and mayapy ``Contents/bin/mayapy``."""
        installer = _load().TentacleInstaller
        name = "mayapy.exe" if os.name == "nt" else "mayapy"
        bundle = TEMP / "maya_bundle"
        shutil.rmtree(bundle, ignore_errors=True)
        (bundle / "MacOS").mkdir(parents=True)
        (bundle / "bin").mkdir()
        (bundle / "bin" / name).write_text("")
        self.addCleanup(shutil.rmtree, bundle, ignore_errors=True)
        with (
            mock.patch.object(sys, "executable", str(bundle / "MacOS" / "Maya")),
            mock.patch.dict(os.environ, {"MAYA_LOCATION": str(bundle)}),
        ):
            self.assertEqual(installer.python_exe("maya"), str(bundle / "bin" / name))
        with mock.patch.object(sys, "executable", str(bundle / "bin" / "maya.exe")):
            self.assertEqual(installer.python_exe("maya"), str(bundle / "bin" / name))

    def test_pip_never_runs_through_the_dcc_binary(self):
        """With no interpreter found this fell back to ``sys.executable`` -- the DCC binary
        in a GUI session -- so ``<that> -s -m pip ...`` started another copy of the
        application and the install worker waited on it. It is an error instead."""
        installer = _load().TentacleInstaller
        empty = TEMP / "no_interpreter"
        shutil.rmtree(empty, ignore_errors=True)
        empty.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, empty, ignore_errors=True)
        env = {k: v for k, v in os.environ.items() if k != "MAYA_LOCATION"}
        for host, binary in (("maya", "maya.exe"), ("blender", "blender.exe")):
            with (
                self.subTest(host=host),
                mock.patch.object(sys, "executable", str(empty / binary)),
                mock.patch.object(sys, "prefix", str(empty)),
                mock.patch.dict(os.environ, env, clear=True),
            ):
                with self.assertRaisesRegex(RuntimeError, "interpreter"):
                    installer.python_exe(host)

    def test_blender_preferences_say_when_an_install_is_running(self):
        """Blender has no progress window: while the worker runs, the add-on's own
        preferences panel is the one place that can say so."""
        installer = _load().TentacleInstaller
        fake_bpy = types.ModuleType("bpy")
        fake_bpy.types = types.SimpleNamespace(
            Operator=type("Operator", (), {}),
            AddonPreferences=type("AddonPreferences", (), {}),
        )
        fake_bpy.utils = types.SimpleNamespace(register_class=lambda cls: None)
        fake_bpy.utils.unregister_class = lambda cls: None
        with (
            mock.patch.dict(sys.modules, {"bpy": fake_bpy}),
            mock.patch.object(installer, "target_dir", return_value=str(TEMP)),
            mock.patch.object(installer, "installed_version", return_value=None),
            mock.patch.object(installer, "_in_progress", return_value=True),
        ):
            installer.register_blender_ui("tentacle_installer")
            prefs = installer._blender_ui[-1]()
            prefs.layout = mock.MagicMock()
            prefs.draw(None)
            installer.unregister_blender_ui()
        texts = [kw.get("text", "") for _, kw in prefs.layout.label.call_args_list]
        self.assertTrue(any("installing" in t.lower() for t in texts), texts)


class TestManifest(unittest.TestCase):
    def setUp(self):
        self.installer = _load().TentacleInstaller
        self.target = TEMP / "manifest"
        shutil.rmtree(self.target, ignore_errors=True)
        self.target.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.target, ignore_errors=True)

    def test_absent_and_unreadable_manifests_are_told_apart(self):
        """An unreadable manifest still describes an install that is on disk.

        Both used to read as an empty dict, which is how a truncated manifest -- a DCC
        crash or a full disk during the old non-atomic write -- turned into an
        uninstall that removed nothing and reported success.
        """
        t = str(self.target)
        self.assertEqual(self.installer._read_manifest(t), {})  # absent
        self.installer.write_manifest(t, pins=["a==1"])
        self.assertEqual(self.installer._read_manifest(t)["pins"], ["a==1"])

        (self.target / self.installer.MANIFEST).write_text('{"pins": ["a=')
        self.assertIsNone(self.installer._read_manifest(t))  # unreadable
        # the public contract is unchanged for both
        self.assertEqual(self.installer.read_manifest(t), {})

    def test_a_corrupt_manifest_is_preserved_not_overwritten(self):
        """Its pins cannot be merged, but they name packages that ARE on disk."""
        t = str(self.target)
        path = self.target / self.installer.MANIFEST
        path.write_text('{"pins": ["pythontk==1.0", "PySide')
        self.installer.write_manifest(t, pins=["tentacletk==1.2"])

        kept = self.target / (self.installer.MANIFEST + ".corrupt")
        self.assertTrue(
            kept.exists(), "the only record of what to remove was destroyed"
        )
        self.assertIn("pythontk==1.0", kept.read_text())
        self.assertEqual(self.installer.read_manifest(t)["pins"], ["tentacletk==1.2"])

    def test_write_is_atomic_and_leaves_no_temp_behind(self):
        t = str(self.target)
        self.installer.write_manifest(t, pins=["a==1"])
        self.installer.write_manifest(t, pins=["b==2"])
        strays = [f.name for f in self.target.iterdir() if f.name.endswith(".tmp")]
        self.assertEqual(strays, [])

    def test_a_sharing_violation_on_the_write_is_waited_out(self):
        """Windows answers a file an antivirus scan or a sync client holds for a
        moment with PermissionError: on this repo's synced drive the manifest's
        replace was refused within a few writes, and a full-suite run lost the
        Uninstall a flow test had queued (1 run in 3). The write waits it out."""
        t = str(self.target)
        real = os.replace
        refusals = []

        def replace(src, dst):
            if len(refusals) < 2:
                refusals.append(dst)
                raise PermissionError(5, "Access is denied")
            return real(src, dst)

        with mock.patch("os.replace", side_effect=replace):
            self.installer.write_manifest(t, pending="uninstall")
        self.assertEqual(len(refusals), 2)
        self.assertEqual(self.installer.read_manifest(t).get("pending"), "uninstall")

    def test_a_sharing_violation_on_the_read_is_waited_out(self):
        """...and a held manifest is not "unreadable": ``_settle_pending`` clears
        what it cannot see, so that verdict dropped a queued verb."""
        module = _load()
        installer = module.TentacleInstaller
        t = str(self.target)
        installer.write_manifest(t, pending="uninstall")
        refusals = []

        def held_open(path, *args, **kwargs):
            if not refusals and str(path).endswith(installer.MANIFEST):
                refusals.append(path)
                raise PermissionError(13, "Permission denied")
            return open(path, *args, **kwargs)

        with mock.patch.object(module, "open", held_open, create=True):
            data = installer._read_manifest(t)
        self.assertTrue(refusals, "the read never met the held file")
        self.assertIsNotNone(data, "a held manifest read as unreadable")
        self.assertEqual(data.get("pending"), "uninstall")

    def test_a_refusal_that_outlasts_the_wait_is_raised(self):
        """A folder this user cannot write is no moment's contention."""
        t = str(self.target)
        with (
            mock.patch.object(self.installer, "SHARE_WAIT", 0.1),
            mock.patch(
                "os.replace", side_effect=PermissionError(5, "Access is denied")
            ),
        ):
            with self.assertRaises(PermissionError):
                self.installer.write_manifest(t, pins=["a==1"])

    def test_an_error_that_is_no_sharing_violation_is_raised_at_once(self):
        """Only a sharing violation is a moment's contention: a full disk is
        raised on the first attempt, not retried for SHARE_WAIT."""
        t = str(self.target)
        attempts = []

        def replace(src, dst):
            attempts.append(dst)
            raise OSError(28, "No space left on device")

        with (
            mock.patch.object(self.installer, "SHARE_WAIT", 5.0),
            mock.patch("os.replace", side_effect=replace),
        ):
            with self.assertRaises(OSError) as raised:
                self.installer.write_manifest(t, pins=["a==1"])
        self.assertNotIsInstance(raised.exception, PermissionError)
        self.assertEqual(len(attempts), 1)

    def test_a_failed_provision_records_what_landed_and_nothing_else(self):
        """A part-provisioned Blender target must not orphan shared dists -- nor claim any.

        install() once wrote the manifest only AFTER provision() returned, so a provision
        that raised left dists in the shared addons/modules that nothing recorded. The
        first repair recorded the REQUESTED spec names instead, which is wrong both ways:
        it missed every dependency that had landed, and on a fresh Blender install it
        claimed PySide6 / qtpy outright -- so a PySide6 another add-on had already put in
        that shared folder was removed by the next Uninstall. What arrived during the
        failed run is what gets recorded, and only that.
        """
        t = str(self.target)
        path_before = list(sys.path)
        self.addCleanup(sys.path.__setitem__, slice(None), path_before)
        _write_dist(self.target, "PySide6", "6.8.0")  # another add-on's, there first

        def partial(*_args):
            _write_dist(self.target, "pythontk", "0.11.3")
            _write_dist(self.target, "uitk", "1.5.1")
            raise RuntimeError("pip blew up")

        with (
            mock.patch.object(self.installer, "is_installed", return_value=False),
            mock.patch.object(self.installer, "_provision_locked", side_effect=partial),
        ):
            with self.assertRaisesRegex(RuntimeError, "pip blew up"):
                self.installer.install("blender", t, python="PY")

        self.assertEqual(
            self.installer.read_manifest(t)["pins"],
            ["pythontk==0.11.3", "uitk==1.5.1"],
        )

    def test_pins_accumulate_and_pending_round_trips(self):
        t = str(self.target)
        self.assertEqual(self.installer.read_manifest(t), {})
        self.installer.write_manifest(t, spec="tentacletk[maya]", pins=["a==1", "b==2"])
        self.installer.write_manifest(t, pins=["c==3"], pending="update")
        data = self.installer.read_manifest(t)
        self.assertEqual(data["pins"], ["a==1", "b==2", "c==3"])
        self.assertEqual(data["pending"], "update")
        self.assertEqual(data["spec"], "tentacletk[maya]")
        (self.target / self.installer.MANIFEST).write_text("not json")
        self.assertEqual(self.installer.read_manifest(t), {}, "garbage reads as absent")

    def test_installed_version_reads_dist_info_without_importing(self):
        t = str(self.target)
        self.assertIsNone(self.installer.installed_version(t))
        info = self.target / "tentacletk-9.9.9.dist-info"
        info.mkdir()
        (info / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: tentacletk\nVersion: 9.9.9\n"
        )
        self.assertEqual(self.installer.installed_version(t), "9.9.9")

    def test_a_dist_written_after_an_earlier_scan_is_still_found(self):
        """``importlib.metadata`` caches a directory listing under
        ``(path, st_mtime)``, and Windows' mtime resolution is coarse enough
        that writing a dist-info in the same tick as an earlier scan leaves
        that key unchanged -- so the stale EMPTY listing is served and the
        package that is right there reports as absent. Measured on mayapy
        2025 before the fix: 14 of 60 scan/create/scan cycles came back
        stale, which is why the single-shot test above passed in isolation
        and failed inside the full suite.

        Repeated because the collision is timing-dependent: one cycle proves
        nothing, and the loop reproduces it in well under a second.
        """
        for i in range(40):
            target = self.target / f"tick{i}"
            target.mkdir()
            t = str(target)
            self.assertIsNone(self.installer.installed_version(t))
            info = target / "tentacletk-9.9.9.dist-info"
            info.mkdir()
            (info / "METADATA").write_text(
                "Metadata-Version: 2.1\nName: tentacletk\nVersion: 9.9.9\n"
            )
            self.assertEqual(
                self.installer.installed_version(t),
                "9.9.9",
                f"cycle {i}: a dist-info written after an earlier scan read as absent",
            )

    def test_the_copy_an_update_wrote_last_is_the_installed_version(self):
        """``pip install --target --upgrade`` left the superseded dist-info beside the one
        it installed (measured, pip 23.2 under mayapy) until pythontk's install_targeted
        pruned it -- so a target updated before that holds both. Name order is no
        tie-break (``0.13.100`` sorts before ``0.13.99``): the copy written last is the
        release on disk, and the re-drop dialog / preferences must name it."""
        old = _write_dist(self.target, "tentacletk", "0.13.99")
        _write_dist(self.target, "tentacletk", "0.13.100")
        os.utime(old, (time.time() - 60, time.time() - 60))
        self.assertEqual(self.installer.installed_version(str(self.target)), "0.13.100")


class TestMayaModule(unittest.TestCase):
    """The user-owned Maya module the drop hook registers (no Maya needed)."""

    def setUp(self):
        self.app = TEMP / "maya_module"
        shutil.rmtree(self.app, ignore_errors=True)
        self.app.mkdir(parents=True)
        self.installer = _load().TentacleInstaller

    def tearDown(self):
        shutil.rmtree(self.app, ignore_errors=True)

    def test_writes_mod_scripts_and_site(self):
        root = self.installer.write_maya_module(str(INSTALLER), str(self.app), "2025")
        self.assertTrue(_under(root, self.app / "2025"))
        mod = self.app / "2025" / "modules" / "tentacle.mod"
        text = mod.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            r"(?m)^\+ tentacle \d+\.\d+ \.\./tentacle\s*$",
            text.splitlines()[0],
        )
        self.assertIn(
            "PYTHONPATH +:= site",
            text,
            "the site dir must ride the module's PYTHONPATH",
        )
        scripts = Path(root) / "scripts"
        startup = self.installer.MAYA_STARTUP
        self.assertEqual(
            (scripts / f"{startup}.py").read_bytes(),
            INSTALLER.read_bytes(),
            "the module must carry a verbatim copy of the installer",
        )
        user_setup = (scripts / "userSetup.py").read_text(encoding="utf-8")
        self.assertIn(f"import {startup}", user_setup)
        self.assertIn("ensure_and_launch('maya')", user_setup)
        self.assertTrue((Path(root) / "site").is_dir())

    def test_the_mod_locates_its_root_relative_to_itself(self):
        """Maya never resolved an absolute non-ASCII module path from a .mod.

        Measured on Maya 2025 with a prefs dir named "José Ångström": the absolute path
        this file used to write (UTF-8) left the module unloaded -- no ``site`` on the
        path, no ``userSetup.py`` -- while ``../tentacle`` loaded there, and in a plain
        dir and one with a space. A user named José got a working first drop and no
        tentacle at any start after it. The relative form is pure ASCII.
        """
        app = self.app / "José Ångström"
        root = self.installer.write_maya_module(str(INSTALLER), str(app), "2025")
        mod = app / "2025" / "modules" / "tentacle.mod"
        raw = mod.read_bytes()
        self.assertTrue(raw.isascii(), raw)
        path = raw.decode("ascii").splitlines()[0].split(" ", 3)[3]
        self.assertFalse(os.path.isabs(path), path)
        self.assertEqual(
            os.path.normcase(os.path.normpath(os.path.join(mod.parent, path))),
            os.path.normcase(os.path.normpath(root)),
        )

    def test_rerun_is_idempotent_and_survives_dropping_the_copy(self):
        root = self.installer.write_maya_module(str(INSTALLER), str(self.app), "2025")
        first = {p: p.read_bytes() for p in Path(self.app).rglob("*") if p.is_file()}
        self.installer.write_maya_module(str(INSTALLER), str(self.app), "2025")
        # Dropping the module's own copy onto the viewport must not raise on copyfile.
        self.installer.write_maya_module(
            str(Path(root) / "scripts" / f"{self.installer.MAYA_STARTUP}.py"),
            str(self.app),
            "2025",
        )
        second = {p: p.read_bytes() for p in Path(self.app).rglob("*") if p.is_file()}
        self.assertEqual(first, second)

    def test_a_redrop_imports_the_dropped_file_not_the_startup_copy(self):
        """Maya's drop executor is ``importlib.import_module(<file stem>)`` -- a CACHE HIT
        once a module of that name is imported. The startup copy that the module's own
        ``userSetup.py`` imports at every start therefore must not share the dropped
        file's name: with installer 1.1 it did, so a re-drop of a newer file ran the
        old copy's ``dropped()`` and the copy was never refreshed (a fix in the file
        being dropped could never take effect on an installed machine).
        """
        root = self.installer.write_maya_module(str(INSTALLER), str(self.app), "2025")
        scripts = Path(root) / "scripts"
        user_setup = (scripts / "userSetup.py").read_text(encoding="utf-8")
        startup_name = re.search(r"^import (\w+)", user_setup, re.M).group(1)
        downloads = self.app / "downloads"
        downloads.mkdir()
        newer = downloads / "tentacle_installer.py"
        newer.write_bytes(INSTALLER.read_bytes() + b"\n# a newer build\n")

        saved = {k: sys.modules.get(k) for k in (startup_name, "tentacle_installer")}
        path_before = list(sys.path)
        try:
            for name in saved:
                sys.modules.pop(name, None)
            # 1. a Maya start: userSetup.py imports the startup copy (scripts/ is on
            #    the path through the .mod).
            sys.path.append(str(scripts))
            startup = importlib.import_module(startup_name)
            self.assertTrue(_under(startup.__file__, root))
            # 2. a drop, exactly as maya.app.general.executeDroppedPythonFile does it.
            sys.path.insert(0, str(downloads))
            dropped = importlib.import_module("tentacle_installer")
            self.assertEqual(
                os.path.normcase(dropped.__file__),
                os.path.normcase(str(newer)),
                "the drop ran the cached startup copy, not the file that was dropped",
            )
            # 3. ...and the dropped file refreshes the startup copy with itself.
            dropped.TentacleInstaller.write_maya_module(
                str(newer), str(self.app), "2025"
            )
            self.assertEqual(
                (scripts / f"{startup_name}.py").read_bytes(), newer.read_bytes()
            )
        finally:
            sys.path[:] = path_before
            for name, module in saved.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module

    def test_a_legacy_startup_copy_is_retired(self):
        """Installer 1.1 named the startup copy after the dropped file. Left beside the
        new copy it is the cache-hit hazard above, one start later."""
        root = self.installer.write_maya_module(str(INSTALLER), str(self.app), "2025")
        legacy = Path(root) / "scripts" / "tentacle_installer.py"
        legacy.write_bytes(b"# installer 1.1\n")
        self.installer.write_maya_module(str(INSTALLER), str(self.app), "2025")
        self.assertFalse(legacy.exists(), "the 1.1 startup copy must be removed")

    def test_the_redrop_dialog_offers_install_when_nothing_is_installed(self):
        """A failed first install leaves the module shell behind, and the re-drop
        dialog then offered "Update" for a package that had never been installed."""
        root, mod = self.installer.maya_paths(str(self.app), "2025")
        self.installer.write_maya_module(str(INSTALLER), str(self.app), "2025")
        offered = []
        fake_maya = types.ModuleType("maya")
        fake_maya.cmds = mock.MagicMock()

        def confirm(**kw):
            offered.append(kw["button"][0])
            return kw["button"][0]

        fake_maya.cmds.confirmDialog.side_effect = confirm

        def drop(version):
            with (
                mock.patch.dict(
                    sys.modules, {"maya": fake_maya, "maya.cmds": fake_maya.cmds}
                ),
                mock.patch.object(
                    self.installer, "maya_paths", return_value=(root, mod)
                ),
                mock.patch.object(self.installer, "is_installed", return_value=False),
                mock.patch.object(self.installer, "_ui", side_effect=lambda fn: fn()),
                mock.patch.object(
                    self.installer, "installed_version", return_value=version
                ),
                mock.patch.object(self.installer, "request") as request,
            ):
                return self.installer.dropped(str(INSTALLER)), request

        verb, request = drop(None)
        self.assertEqual(verb, "install")
        request.assert_called_once_with("maya", "install")
        drop("1.0")
        self.assertEqual(offered, ["Install", "Update"])

    def test_a_drop_during_an_install_is_refused(self):
        """A second drop while the first is provisioning used to reach the dialog and
        could start a second pip into the same target."""
        root, mod = self.installer.maya_paths(str(self.app), "2025")
        said = []
        with (
            mock.patch.object(self.installer, "maya_paths", return_value=(root, mod)),
            mock.patch.object(self.installer, "_in_progress", return_value=True),
            mock.patch.object(
                self.installer, "_say", side_effect=lambda h, m, **k: said.append(m)
            ),
            mock.patch.object(self.installer, "request") as request,
            mock.patch.object(self.installer, "ensure_and_launch") as ensure,
        ):
            verb = self.installer.dropped(str(INSTALLER))
        self.assertEqual(verb, "busy")
        self.assertFalse(
            os.path.exists(mod), "nothing is written while an install runs"
        )
        request.assert_not_called()
        ensure.assert_not_called()
        self.assertTrue(said and "install" in said[0].lower(), said)

    def test_rmtree_names_what_it_could_not_remove(self):
        installer = self.installer
        tree = self.app / "tree" / "deep"
        tree.mkdir(parents=True)
        (tree / "a.txt").write_text("x")
        installer._rmtree(str(self.app / "tree"))
        self.assertFalse((self.app / "tree").exists())
        installer._rmtree(str(self.app / "missing"))  # absent: a no-op
        if (
            os.name == "nt"
        ):  # an open file is the realistic failure: report it, never hide it
            tree.mkdir(parents=True)
            held = tree / "held.txt"
            with open(held, "w") as fh:
                fh.write("x")
                with self.assertRaisesRegex(RuntimeError, "held.txt"):
                    installer._rmtree(str(self.app / "tree"))

    def test_long_path_uses_the_UNC_form_for_a_network_prefs_dir(self):
        r"""A UNC path takes \\?\UNC\, not \\?\.

        A studio that points MAYA_APP_DIR at a network home (or has Documents
        folder-redirected) gets a prefs dir of exactly that shape. Prefixed the
        plain way it became "\\?\\\server\..." -- WinError 123 -- and _rmtree
        then raised 'close the application and delete by hand', blaming a lock
        that never existed. Uninstall could not succeed on such a machine.
        """
        installer = self.installer
        if os.name != "nt":
            self.assertEqual(installer._long_path("/tmp/x"), "/tmp/x")
            return

        unc = r"\\studio\home\jdoe\maya\2025\tentacle"
        self.assertEqual(
            installer._long_path(unc),
            r"\\?\UNC\studio\home\jdoe\maya\2025\tentacle",
        )
        drive = os.path.abspath("C:/Windows")
        self.assertEqual(installer._long_path(drive), "\\\\?\\" + drive)

        # ...and the prefixed UNC form is one Windows actually resolves.
        live = r"\\localhost\C$\Windows"
        if os.path.isdir(live):
            self.assertTrue(os.path.isdir(installer._long_path(live)))

        # already-prefixed input is left alone
        pre = "\\\\?\\C:\\Windows"
        self.assertEqual(installer._long_path(pre), pre)

    def test_short_path_round_trips_both_prefixes(self):
        """A failure message must name the path the user recognises."""
        installer = self.installer
        if os.name != "nt":
            return
        for original in (os.path.abspath("C:/Windows"), r"\\srv\share\deep"):
            with self.subTest(path=original):
                self.assertEqual(
                    installer._short_path(installer._long_path(original)), original
                )

    def test_blender_uninstall_clears_its_own_leftovers(self):
        """addons/modules is SHARED, so uninstall must not leave our files in it.

        Includes the ``.corrupt`` breadcrumb a failed manifest read leaves behind:
        it exists for hand-recovery, and once the user has uninstalled there is
        nothing left to recover.
        """
        target = self.app / "addons_modules"
        target.mkdir(parents=True, exist_ok=True)
        manifest = Path(self.installer.manifest_path(str(target)))
        manifest.write_text('{"pins": ["tentacletk==1"]}')
        _write_dist(target, "tentacletk", "1")
        corrupt = Path(str(manifest) + ".corrupt")
        corrupt.write_text('{"pins": ["pythontk==1.0')

        with (
            mock.patch.object(self.installer, "python_exe", return_value="PY"),
            mock.patch.object(self.installer, "_run_checked"),
            mock.patch.object(self.installer, "_remove_blender_addon"),
        ):
            names = self.installer.uninstall("blender", str(target))

        self.assertEqual(names, ["tentacletk"])
        self.assertFalse(manifest.exists())
        self.assertFalse(corrupt.exists(), "the .corrupt breadcrumb was left behind")

    def test_an_unrecorded_package_in_the_shared_dir_is_NAMED(self):
        """The removal is driven ENTIRELY by recorded pins, and the on-demand
        Qt bootstrap installs by a path that records none.

        `_QtBootstrap` puts PySide6/qtpy into the installer's own target dir
        through its own route, so nothing lands in the manifest, the uninstall
        removes none of it, and until now said nothing about it either.
        Measured on this machine: PySide6, qtpy, shiboken6, PIL, a pillow
        dist-info and a bin folder, with no manifest beside them.
        """
        target = self.app / "addons_modules"
        (target / "PySide6").mkdir(parents=True)
        (target / "qtpy").mkdir(parents=True)

        message = self.installer._uninstall_message("blender", str(target), [], {})

        self.assertIn("PySide6", message)
        self.assertIn("qtpy", message)

    def test_naming_a_leftover_never_deletes_it(self):
        """Report, never remove: `addons/modules` is SHARED with every other
        add-on, the Qt may predate tentacle entirely, and deleting an
        unrecorded PySide6 can break somebody else's tool."""
        target = self.app / "addons_modules"
        (target / "PySide6").mkdir(parents=True)

        self.installer._uninstall_message("blender", str(target), [], {})

        self.assertTrue((target / "PySide6").is_dir(), "the report deleted it")

    def test_an_EMPTY_shared_dir_is_not_reported_as_holding_leftovers(self):
        """Pre-existing overclaim, reachable now that the contents are read:
        with no pins the message asserted packages "are still in" the target
        without ever looking. Blender's popup shows the first line only, so
        that assertion was the entire report.
        """
        target = self.app / "addons_modules_empty"
        target.mkdir(parents=True, exist_ok=True)

        message = self.installer._uninstall_message("blender", str(target), [], {})

        self.assertIn("nothing is left", message)
        self.assertNotIn("are still in", message)

    def test_a_package_the_manifest_DID_account_for_is_not_listed(self):
        """A recorded pin was removed by the uninstall, so it is not a leftover."""
        target = self.app / "addons_modules"
        target.mkdir(parents=True, exist_ok=True)
        (target / "leftover_thing").mkdir()

        message = self.installer._uninstall_message(
            "blender", str(target), ["leftover_thing"], {}
        )

        self.assertNotIn("leftover_thing", message.split("recorded by nothing")[-1])

    def test_maya_reports_no_leftovers_because_its_removal_is_exclusive(self):
        """The whole module folder is ours there, so the removal is complete
        whatever the manifest said -- listing its contents would be noise."""
        target = self.app / "maya_module"
        (target / "PySide6").mkdir(parents=True)

        message = self.installer._uninstall_message("maya", str(target), [], {})

        self.assertNotIn("PySide6", message)

    def test_a_redrop_after_a_failed_first_install_offers_uninstall(self):
        """The module is written BEFORE provisioning, so a failed first install
        left a permanent startup hook whose own userSetup.py tells the user to
        "drop tentacle_installer.py in and choose Uninstall" -- while the drop
        dialog was gated on the install having succeeded, so re-dropping only
        retried the same failing pip and Uninstall was unreachable.
        """
        # first drop: the module lands, provisioning never succeeds
        root, mod = self.installer.maya_paths(str(self.app), "2025")
        self.installer.write_maya_module(str(INSTALLER), str(self.app), "2025")
        self.assertTrue(os.path.isdir(root))

        asked = {}

        def fake_ui(fn):
            asked["shown"] = True
            return "Uninstall"

        # the dialog branch imports maya.cmds before _ui is reached
        fake_maya = types.ModuleType("maya")
        fake_maya.cmds = mock.MagicMock()

        with (
            mock.patch.dict(
                sys.modules, {"maya": fake_maya, "maya.cmds": fake_maya.cmds}
            ),
            mock.patch.object(self.installer, "maya_paths", return_value=(root, mod)),
            mock.patch.object(self.installer, "is_installed", return_value=False),
            mock.patch.object(self.installer, "installed_version", return_value=None),
            mock.patch.object(self.installer, "_ui", side_effect=fake_ui),
            mock.patch.object(self.installer, "request") as request,
            mock.patch.object(self.installer, "ensure_and_launch") as ensure,
        ):
            verb = self.installer.dropped(str(INSTALLER))

        self.assertTrue(asked.get("shown"), "the re-drop never offered the dialog")
        self.assertEqual(verb, "uninstall")
        request.assert_called_once_with("maya", "uninstall")
        ensure.assert_not_called()

    def test_the_redrop_dialog_says_where_tentacle_actually_resolved(self):
        """The dialog is what makes the user expect the Uninstall to remove something.

        ``dropped`` writes the module first, so a re-drop on a machine whose ``tentacle``
        comes from elsewhere (a checkout on ``PYTHONPATH``, a plain ``pip install``) hits
        the dialog with an EMPTY site: it reported "Tentacle ? is installed in <root>",
        the user chose Uninstall, and the only thing removed was the shell the drop had
        just written.
        """
        root, mod = self.installer.maya_paths(str(self.app), "2025")
        outside = str(TEMP / "elsewhere" / "tentacle" / "__init__.py")
        shown = {}

        def fake_ui(fn):
            shown["message"] = fn()
            return "Cancel"

        fake_maya = types.ModuleType("maya")
        fake_maya.cmds = mock.MagicMock()
        fake_maya.cmds.confirmDialog.side_effect = lambda **kw: kw["message"]

        with (
            mock.patch.dict(
                sys.modules, {"maya": fake_maya, "maya.cmds": fake_maya.cmds}
            ),
            mock.patch.object(self.installer, "maya_paths", return_value=(root, mod)),
            mock.patch.object(self.installer, "is_installed", return_value=True),
            mock.patch.object(self.installer, "installed_version", return_value=None),
            mock.patch.object(
                self.installer,
                "_origin",
                side_effect=lambda name: outside if name == "tentacle" else None,
            ),
            mock.patch.object(self.installer, "_ui", side_effect=fake_ui),
            mock.patch.object(self.installer, "request"),
        ):
            self.installer.dropped(str(INSTALLER))

        message = shown.get("message", "")
        self.assertNotIn(
            "Tentacle ? is installed", message, "an empty site is not an install"
        )
        self.assertIn(os.path.dirname(outside), message)

    def test_uninstall_honours_the_target_it_was_given(self):
        """The Maya branch used to discard *target* and recompute the tree.

        A caller honouring the published signature deleted the real
        ``~/Documents/maya/<ver>/tentacle`` instead of the directory it named. The
        existing uninstall test only avoided that by patching ``maya_paths`` --
        under mayapy, dropping that patch would have removed the developer's own
        module. This one deliberately does NOT patch it.
        """
        root = self.installer.write_maya_module(str(INSTALLER), str(self.app), "2025")
        mod = self.app / "2025" / "modules" / "tentacle.mod"
        site = Path(root) / "site"
        site.mkdir(parents=True, exist_ok=True)
        self.installer.write_manifest(str(site), pins=["tentacletk==1"])

        def boom(*a, **k):  # noqa: ARG001
            raise AssertionError(
                "uninstall recomputed the path instead of using target"
            )

        with (
            mock.patch.object(self.installer, "maya_paths", side_effect=boom),
            mock.patch.object(self.installer, "python_exe", return_value="PY"),
        ):
            self.installer.uninstall("maya", str(site))

        self.assertFalse(Path(root).exists())
        self.assertFalse(mod.exists())

    def test_uninstall_refuses_a_tree_that_is_not_a_tentacle_module(self):
        """The one destructive rmtree must not trust a computed path.

        The .mod still goes, so a half-written module stays uninstallable -- the
        guard only stops an unrelated directory being taken with it.
        """
        stranger = self.app / "2025" / "not_ours"
        (stranger / "site").parent.mkdir(parents=True, exist_ok=True)
        stranger.mkdir(parents=True, exist_ok=True)
        (stranger / "someones_work.txt").write_text("keep me")

        mod = self.app / "2025" / "modules" / "tentacle.mod"
        mod.parent.mkdir(parents=True, exist_ok=True)
        mod.write_text("+ tentacle 1.0 .")

        with (
            mock.patch.object(self.installer, "python_exe", return_value="PY"),
        ):
            # target points INTO the stranger, so root resolves to it
            self.installer.uninstall("maya", str(stranger / "site"))

        self.assertTrue(
            (stranger / "someones_work.txt").exists(),
            "uninstall deleted a directory that was not a tentacle module",
        )
        self.assertFalse(mod.exists(), "the .mod should still be removed")

    def test_uninstall_removes_the_module_and_its_mod(self):
        root = self.installer.write_maya_module(str(INSTALLER), str(self.app), "2025")
        mod = self.app / "2025" / "modules" / "tentacle.mod"
        site = Path(root) / "site"
        self.installer.write_manifest(str(site), pins=["tentacletk==1"])
        with (
            mock.patch.object(
                self.installer, "maya_paths", return_value=(root, str(mod))
            ),
            mock.patch.object(self.installer, "python_exe", return_value="PY"),
        ):
            names = self.installer.uninstall("maya", str(site))
        self.assertEqual(names, ["tentacletk"])
        self.assertFalse(Path(root).exists())
        self.assertFalse(mod.exists())


class TestFlow(unittest.TestCase):
    """ensure_and_launch / request / provision orchestration with the subprocess + host seams mocked."""

    def setUp(self):
        self.module = _load()
        self.installer = self.module.TentacleInstaller
        self.target = TEMP / "flow_target"
        shutil.rmtree(self.target, ignore_errors=True)
        self.target.mkdir(parents=True)
        self.patches = [
            mock.patch.object(
                self.installer, "target_dir", return_value=str(self.target)
            ),
            mock.patch.object(self.installer, "python_exe", return_value="PY"),
            mock.patch.object(self.installer, "_say"),
        ]
        for p in self.patches:
            p.start()
        self.path_before = list(sys.path)

    def tearDown(self):
        for p in self.patches:
            p.stop()
        sys.path[:] = self.path_before
        shutil.rmtree(self.target, ignore_errors=True)

    def test_installed_launches_without_a_subprocess(self):
        with (
            mock.patch.object(self.installer, "is_installed", return_value=True),
            mock.patch.object(self.installer, "install") as install,
            mock.patch.object(self.installer, "_provision_async") as async_,
            mock.patch.object(self.installer, "launch", return_value="menu") as launch,
        ):
            self.assertEqual(self.installer.ensure_and_launch("maya"), "menu")
        install.assert_not_called()
        async_.assert_not_called()
        launch.assert_called_once_with("maya")
        self.assertEqual(
            sys.path[-1], str(self.target), "the target is APPENDED, never inserted"
        )

    def test_headless_provisions_synchronously_then_launches(self):
        with (
            mock.patch.object(self.installer, "is_installed", return_value=False),
            mock.patch.object(self.installer, "headless", return_value=True),
            mock.patch.object(
                self.installer, "install", return_value=["x==1"]
            ) as install,
            mock.patch.object(self.installer, "_report"),
            mock.patch.object(self.installer, "launch") as launch,
        ):
            self.installer.ensure_and_launch("blender")
        install.assert_called_once_with("blender", str(self.target), upgrade=False)
        launch.assert_called_once_with("blender")

    def test_pending_update_at_start_upgrades_then_launches(self):
        self.installer.write_manifest(str(self.target), pending="update")
        with (
            mock.patch.object(self.installer, "is_installed", return_value=True),
            mock.patch.object(self.installer, "headless", return_value=True),
            mock.patch.object(self.installer, "install", return_value=[]) as install,
            mock.patch.object(self.installer, "_report"),
            mock.patch.object(self.installer, "launch") as launch,
        ):
            self.installer.ensure_and_launch("maya")
        install.assert_called_once_with("maya", str(self.target), upgrade=True)
        launch.assert_called_once_with("maya")

    def test_pending_uninstall_at_start_removes_and_never_launches(self):
        self.installer.write_manifest(str(self.target), pending="uninstall")
        with (
            mock.patch.object(
                self.installer, "uninstall", return_value=["tentacletk"]
            ) as uninstall,
            mock.patch.object(self.installer, "install") as install,
            mock.patch.object(self.installer, "launch") as launch,
        ):
            self.assertIsNone(self.installer.ensure_and_launch("blender"))
        uninstall.assert_called_once_with("blender", str(self.target))
        install.assert_not_called()
        launch.assert_not_called()

    def test_request_defers_when_our_code_is_loaded(self):
        with (
            mock.patch.object(self.installer, "loaded", return_value=True),
            mock.patch.object(self.installer, "uninstall") as uninstall,
            mock.patch.object(self.installer, "update") as update,
        ):
            message = self.installer.request("maya", "uninstall")
            self.installer.request("maya", "update")
        uninstall.assert_not_called()
        update.assert_not_called()
        self.assertIn("restart", message)
        self.assertEqual(
            self.installer.read_manifest(str(self.target))["pending"], "update"
        )

    def test_blender_uninstall_that_removed_nothing_does_not_claim_success(self):
        """The add-on deletes itself, so the message is the only record left.

        Blender's uninstall is driven ENTIRELY by the manifest's pins into a SHARED
        addons/modules. With no pins recorded -- a failed or partial first install, or
        a manifest truncated by a crash -- pip is never called, nothing is removed, and
        the add-on that is the only UI to retry from is deleted anyway. Reporting
        "Tentacle uninstalled" there left the user with orphaned packages and no sign
        anything was wrong. Maya is unaffected: its removal is exclusive and complete
        whatever the manifest said.
        """
        with (
            mock.patch.object(self.installer, "loaded", return_value=False),
            mock.patch.object(self.installer, "headless", return_value=True),
            mock.patch.object(self.installer, "uninstall", return_value=[]),
            mock.patch.object(self.installer, "_origin", return_value=None),
            mock.patch.object(self.installer, "_say"),
        ):
            message = self.installer.request("blender", "uninstall")
        self.assertNotEqual(message, "Tentacle uninstalled")
        self.assertIn("Nothing was recorded to remove", message)
        self.assertIn(str(self.target), message)

    def test_maya_uninstall_reports_success_even_with_no_pins(self):
        """Maya removes its own module folder outright; pins do not gate it."""
        with (
            mock.patch.object(self.installer, "loaded", return_value=False),
            mock.patch.object(self.installer, "headless", return_value=True),
            mock.patch.object(self.installer, "uninstall", return_value=[]),
            mock.patch.object(self.installer, "_origin", return_value=None),
            mock.patch.object(self.installer, "_say"),
        ):
            message = self.installer.request("maya", "uninstall")
        self.assertEqual(message, "Tentacle uninstalled")

    def test_uninstall_reports_a_copy_it_could_not_reach(self):
        """A removal that leaves the menu running must not report a bare success.

        Nothing this installer removes can touch a ``tentacle`` that resolves from
        somewhere else on ``sys.path`` -- a dev checkout on ``PYTHONPATH``, a stale
        plain ``pip install tentacletk`` in the user site -- so the next start brings
        the menu straight back and the uninstall looks like it did nothing. Measured:
        a drop-then-Uninstall on such a machine removed only the empty module shell
        the drop had just written, said "Tentacle uninstalled", and relaunched at the
        next start. The launch path already detects this (:meth:`_advise_shadow`);
        the uninstall path reported success regardless.
        """
        outside = str(TEMP / "elsewhere" / "tentacle" / "__init__.py")
        for host in ("maya", "blender"):
            with self.subTest(host=host):
                with (
                    mock.patch.object(self.installer, "loaded", return_value=False),
                    mock.patch.object(self.installer, "headless", return_value=True),
                    mock.patch.object(
                        self.installer, "uninstall", return_value=["tentacletk"]
                    ),
                    mock.patch.object(
                        self.installer,
                        "_origin",
                        side_effect=lambda name: (
                            outside if name == "tentacle" else None
                        ),
                    ),
                    mock.patch.object(self.installer, "_say"),
                ):
                    message = self.installer.request(host, "uninstall")
                self.assertIn(
                    os.path.dirname(outside),
                    message,
                    "the uninstall must name the copy it could not remove",
                )
                self.assertIn("still", message.splitlines()[0].lower())

    def test_uninstall_is_a_plain_success_when_nothing_else_resolves(self):
        """The warning is the exception, not a permanent caveat on every uninstall."""
        with (
            mock.patch.object(self.installer, "loaded", return_value=False),
            mock.patch.object(self.installer, "headless", return_value=True),
            mock.patch.object(self.installer, "uninstall", return_value=["tentacletk"]),
            mock.patch.object(self.installer, "_origin", return_value=None),
            mock.patch.object(self.installer, "_say"),
        ):
            message = self.installer.request("maya", "uninstall")
        self.assertEqual(message, "Tentacle uninstalled (1 package(s) removed)")

    def test_a_pending_uninstall_at_start_reports_the_copy_it_could_not_reach(self):
        """The pending path is where a real Maya lands, and it built its own message."""
        self.installer.write_manifest(str(self.target), pending="uninstall")
        outside = str(TEMP / "elsewhere" / "tentacle" / "__init__.py")
        with (
            mock.patch.object(self.installer, "uninstall", return_value=[]) as remove,
            mock.patch.object(
                self.installer,
                "_origin",
                side_effect=lambda name: outside if name == "tentacle" else None,
            ),
            mock.patch.object(self.installer, "launch") as launch,
            mock.patch.object(self.installer, "_say") as say,
        ):
            self.assertIsNone(self.installer.ensure_and_launch("maya"))
        remove.assert_called_once_with("maya", str(self.target))
        launch.assert_not_called()
        self.assertIn(os.path.dirname(outside), say.call_args[0][1])

    def test_outside_origins_ignores_what_lives_in_the_target(self):
        """Its own install is not a shadow -- only a copy the removal cannot reach."""
        inside = str(self.target / "tentacle" / "__init__.py")
        with mock.patch.object(self.installer, "_origin", return_value=inside):
            self.assertEqual(
                self.installer._outside_origins("maya", str(self.target)), {}
            )

    def test_outside_origins_does_not_swallow_a_sibling_of_the_target(self):
        """A bare prefix test reads ``<target>_old`` as inside -- it is not reachable."""
        sibling = str(
            self.target.parent
            / (self.target.name + "_old")
            / "tentacle"
            / "__init__.py"
        )
        with mock.patch.object(self.installer, "_origin", return_value=sibling):
            self.assertIn(
                "tentacle", self.installer._outside_origins("maya", str(self.target))
            )

    def test_an_unreachable_copy_is_reported_on_the_channel_that_waits(self):
        """Maya's success channel is a four-second fading inViewMessage.

        That is the wrong carrier for the one message explaining why the menu is still
        there, so a shadowed removal reports as an error (a dialog) instead.
        """
        outside = str(TEMP / "elsewhere" / "tentacle" / "__init__.py")
        with (
            mock.patch.object(self.installer, "loaded", return_value=False),
            mock.patch.object(self.installer, "headless", return_value=True),
            mock.patch.object(self.installer, "uninstall", return_value=[]),
            mock.patch.object(self.installer, "_say") as say,
            mock.patch.object(
                self.installer,
                "_origin",
                side_effect=lambda name: outside if name == "tentacle" else None,
            ),
        ):
            self.installer.request("maya", "uninstall")
            self.assertTrue(say.call_args.kwargs.get("error"), say.call_args)

            say.reset_mock()
            with mock.patch.object(self.installer, "_origin", return_value=None):
                self.installer.request("maya", "uninstall")
            self.assertFalse(
                say.call_args.kwargs.get("error"),
                "a clean removal must not report as an error",
            )

    def test_a_failed_pending_update_still_launches_the_install_on_disk(self):
        """One unreachable index must not cost the artist the menu, forever.

        `pending` was only ever cleared on the SUCCESS path, and the failure path
        skipped the launch. So a single Update click plus an offline morning meant
        a modal error and no marking menu at every start thereafter -- with a
        perfectly good install sitting in the target dir -- recoverable only by
        hand-editing the manifest.
        """
        self.installer.write_manifest(str(self.target), pending="update")
        with (
            mock.patch.object(self.installer, "headless", return_value=True),
            mock.patch.object(self.installer, "is_installed", return_value=True),
            mock.patch.object(
                self.installer, "install", side_effect=RuntimeError("offline")
            ),
            mock.patch.object(self.installer, "launch") as launch,
        ):
            self.installer.ensure_and_launch("maya")

        launch.assert_called_once_with("maya")
        self.assertIsNone(
            self.installer.read_manifest(str(self.target)).get("pending"),
            "the failed verb would be retried at every start",
        )

    def test_a_failed_install_with_nothing_on_disk_does_not_abort_registration(self):
        """Unguarded, the error propagates and the host calls the ADD-ON broken."""
        with (
            mock.patch.object(self.installer, "headless", return_value=True),
            mock.patch.object(self.installer, "is_installed", return_value=False),
            mock.patch.object(
                self.installer, "install", side_effect=RuntimeError("offline")
            ),
            mock.patch.object(self.installer, "launch") as launch,
        ):
            result = self.installer.ensure_and_launch("blender")
        self.assertIsNone(result)
        launch.assert_not_called()

    def test_request_applies_immediately_when_nothing_is_loaded(self):
        with (
            mock.patch.object(self.installer, "loaded", return_value=False),
            mock.patch.object(self.installer, "headless", return_value=True),
            mock.patch.object(
                self.installer, "uninstall", return_value=["tentacletk"]
            ) as uninstall,
            mock.patch.object(
                self.installer, "update", return_value=["tentacletk==2"]
            ) as update,
            mock.patch.object(self.installer, "_origin", return_value=None),
            mock.patch.object(self.installer, "_report"),
            mock.patch.object(self.installer, "launch") as launch,
        ):
            self.assertEqual(
                self.installer.request("blender", "uninstall"),
                "Tentacle uninstalled (1 package(s) removed)",
            )
            uninstall.assert_called_once_with("blender", str(self.target))
            self.assertEqual(
                self.installer.request("blender", "update"), "Tentacle updated"
            )
            update.assert_called_once_with("blender", str(self.target))
            launch.assert_called_once_with("blender")
        self.assertNotIn("pending", self.installer.read_manifest(str(self.target)))

    def test_gui_provisions_on_a_worker_and_launches_on_finish(self):
        outcome = {}
        host_query_threads = []
        for name in ("target_dir", "python_exe"):
            real = getattr(self.installer, name)

            def spy(host, _real=real):
                host_query_threads.append(threading.current_thread())
                return _real(host)

            self.patches.append(
                mock.patch.object(self.installer, name, side_effect=spy)
            )
            self.patches[-1].start()

        def poll(
            host, finish
        ):  # stand in for the host timer: wait, then finish on this thread
            self.installer._worker.join(10)
            finish()

        with (
            mock.patch.object(self.installer, "is_installed", return_value=False),
            mock.patch.object(self.installer, "headless", return_value=False),
            mock.patch.object(
                self.installer, "install", return_value=["y==2"]
            ) as install,
            mock.patch.object(self.installer, "_poll", side_effect=poll),
            mock.patch.object(self.installer, "_feedback_begin") as begin,
            mock.patch.object(
                self.installer,
                "_feedback_end",
                side_effect=lambda h, u, o: outcome.update(o),
            ) as end,
            mock.patch.object(self.installer, "_report"),
            mock.patch.object(self.installer, "launch") as launch,
        ):
            self.assertIsNone(self.installer.ensure_and_launch("blender"))
        install.assert_called_once_with(
            "blender", str(self.target), "PY", upgrade=False
        )
        self.assertEqual(
            [threading.main_thread()] * len(host_query_threads),
            host_query_threads,
            "target_dir / python_exe (cmds / bpy) must only ever run on the main thread",
        )
        begin.assert_called_once_with("blender", False)
        end.assert_called_once()
        self.assertEqual(outcome, {"pins": ["y==2"]})
        launch.assert_called_once_with("blender")

    def test_gui_failure_is_reported_and_does_not_launch(self):
        outcome = {}

        def poll(host, finish):
            self.installer._worker.join(10)
            finish()

        with (
            mock.patch.object(self.installer, "is_installed", return_value=False),
            mock.patch.object(self.installer, "headless", return_value=False),
            mock.patch.object(
                self.installer, "install", side_effect=RuntimeError("no network")
            ),
            mock.patch.object(self.installer, "_poll", side_effect=poll),
            mock.patch.object(self.installer, "_feedback_begin"),
            mock.patch.object(
                self.installer,
                "_feedback_end",
                side_effect=lambda h, u, o: outcome.update(o),
            ),
            mock.patch.object(self.installer, "launch") as launch,
        ):
            self.installer.ensure_and_launch("blender")
        self.assertIsInstance(outcome.get("error"), RuntimeError)
        launch.assert_not_called()

    def test_install_records_the_manifest(self):
        with mock.patch.object(
            self.installer, "provision", return_value=["a==1"]
        ) as provision:
            self.installer.install("blender", str(self.target))
            self.installer.install("blender", str(self.target), upgrade=True)
        fresh, upgrade = provision.call_args_list
        self.assertEqual(
            fresh.kwargs["specs"], ["tentacletk[blender]", "PySide6", "qtpy"]
        )
        self.assertEqual(upgrade.kwargs["specs"], ["tentacletk[blender]"])
        data = self.installer.read_manifest(str(self.target))
        self.assertEqual(
            (data["spec"], data["pins"], data["pending"]),
            ("tentacletk[blender]", ["a==1"], None),
        )

    def test_blender_uninstall_removes_only_the_recorded_dists(self):
        self.installer.write_manifest(
            str(self.target), pins=["blendertk==1", "PySide6==6"]
        )
        for name, version in (("blendertk", "1"), ("PySide6", "6"), ("other", "2")):
            _write_dist(self.target, name, version)  # "other": another add-on's
        with (
            mock.patch.object(self.installer, "_run_checked") as run_checked,
            mock.patch.object(self.installer, "_remove_blender_addon") as remove_addon,
        ):
            names = self.installer.uninstall("blender", str(self.target))
        self.assertEqual(names, ["PySide6", "blendertk"])
        command, kwargs = run_checked.call_args.args[0], run_checked.call_args.kwargs
        self.assertEqual(command[:6], ["PY", "-s", "-m", "pip", "uninstall", "-y"])
        self.assertEqual(
            kwargs["env"]["PYTHONPATH"],
            str(self.target),
            "pip must see the targeted dists",
        )
        self.assertFalse((self.target / self.installer.MANIFEST).exists())
        remove_addon.assert_called_once()

    def test_blender_uninstall_never_reaches_past_the_target(self):
        """``pip uninstall`` removes the FIRST dist of that name on sys.path.

        With ``PYTHONPATH=<target>`` that is the target's copy -- while it is there. A
        recorded dist that has since left the target resolves to the next copy on the
        path, which is Blender's own bundled site-packages (numpy, requests and
        packaging ship there): deleted outright from a portable Blender, and from
        Program Files a failed pip that aborted the whole uninstall.
        """
        t = str(self.target)
        _write_dist(self.target, "blendertk", "0.11.0")
        self.installer.write_manifest(t, pins=["blendertk==0.11.0", "packaging==26.0"])
        with (
            mock.patch.object(self.installer, "_run_checked") as run_checked,
            mock.patch.object(self.installer, "_remove_blender_addon"),
        ):
            self.assertEqual(self.installer.uninstall("blender", t), ["blendertk"])
        self.assertEqual(run_checked.call_args.args[0][6:], ["blendertk"])

        # Nothing recorded is left in the target: pip does not run at all.
        shutil.rmtree(self.target / "blendertk-0.11.0.dist-info")
        self.installer.write_manifest(t, pins=["packaging==26.0"])
        with (
            mock.patch.object(self.installer, "_run_checked") as run_checked,
            mock.patch.object(self.installer, "_remove_blender_addon"),
        ):
            self.assertEqual(self.installer.uninstall("blender", t), [])
        run_checked.assert_not_called()

    def test_blender_uninstall_removes_every_copy_an_update_left(self):
        """pip removes ONE dist of a name per run. A target updated before pythontk's
        install_targeted pruned superseded dist-infos holds two copies, and one pass
        removed the stale copy (by its own RECORD) and left the current dist-info in the
        SHARED addons/modules, named by nothing (measured: ``QtPy-2.4.3.dist-info`` stayed
        after ``pip uninstall qtpy`` took ``QtPy-2.4.2``)."""
        t = str(self.target)
        _write_dist(self.target, "QtPy", "2.4.2")
        _write_dist(self.target, "QtPy", "2.4.3")
        self.installer.write_manifest(t, pins=["QtPy==2.4.3"])

        def pip(command, env=None):  # as pip does: the first copy of each name goes
            for name in command[6:]:
                copies = sorted(self.target.glob(f"{name}-*.dist-info"))
                if copies:
                    shutil.rmtree(copies[0])

        with (
            mock.patch.object(self.installer, "_run_checked", side_effect=pip) as run,
            mock.patch.object(self.installer, "_remove_blender_addon"),
        ):
            self.assertEqual(self.installer.uninstall("blender", t), ["QtPy"])
        self.assertEqual(sorted(self.target.glob("*.dist-info")), [])
        self.assertEqual(run.call_count, 2, "one pass per copy, then stop")

    def test_blender_uninstall_removes_the_launchers_pip_cannot_find(self):
        """``pip install --target`` stages into a temp prefix and moves the result in, so a
        dist's RECORD keeps the STAGING path of its console scripts (``../../bin/qtpy.exe``)
        -- which ``pip uninstall`` resolves two levels above the target and never finds.
        Measured on 5.1.2: after Uninstall, ``bin/`` with PySide6's 23 launchers and
        qtpy.exe stayed in the SHARED addons/modules. Mapped back into the target here;
        nothing another add-on put there, and nothing outside the target, is touched."""
        t = str(self.target)
        _write_dist(
            self.target,
            "QtPy",
            "2.4.3",
            record=["qtpy/__init__.py", "../../bin/qtpy.exe", "../../../escape.txt"],
        )
        (self.target / "bin").mkdir()
        (self.target / "bin" / "qtpy.exe").write_text("")
        (self.target / "bin" / "other.exe").write_text("")  # another add-on's
        outside = self.target.parent / "escape.txt"
        outside.write_text("not ours")
        self.addCleanup(outside.unlink, missing_ok=True)
        self.installer.write_manifest(t, pins=["QtPy==2.4.3"])
        with (
            mock.patch.object(self.installer, "_run_checked"),
            mock.patch.object(self.installer, "_remove_blender_addon"),
        ):
            self.installer.uninstall("blender", t)
        self.assertFalse((self.target / "bin" / "qtpy.exe").exists())
        self.assertTrue((self.target / "bin" / "other.exe").exists())
        self.assertTrue(
            outside.exists(), "a RECORD path must never reach past the target"
        )

        # From Python 3.12, Distribution.files drops every RECORD entry whose file does not
        # exist where it RESOLVES -- exactly these launchers (measured: 0 of 24 found under
        # Blender 5.1's 3.13, all 24 under 3.11, which is why this test once passed while
        # the live clean room still found bin/ left behind). Emulated here on any Python.
        (self.target / "bin" / "qtpy.exe").write_text("")
        self.installer.write_manifest(t, pins=["QtPy==2.4.3"])
        from importlib import metadata as md

        with (
            mock.patch.object(
                md.PathDistribution, "files", new_callable=mock.PropertyMock
            ) as files,
            mock.patch.object(self.installer, "_run_checked"),
            mock.patch.object(self.installer, "_remove_blender_addon"),
        ):
            files.return_value = []
            self.installer.uninstall("blender", t)
        self.assertFalse(
            (self.target / "bin" / "qtpy.exe").exists(),
            "found through Distribution.files, which 3.12+ filters",
        )

        # With nothing else in it, bin/ itself goes.
        (self.target / "bin" / "other.exe").unlink()
        (self.target / "bin" / "qtpy.exe").write_text("")
        self.installer.write_manifest(t, pins=["QtPy==2.4.3"])
        with (
            mock.patch.object(self.installer, "_run_checked"),
            mock.patch.object(self.installer, "_remove_blender_addon"),
        ):
            self.installer.uninstall("blender", t)
        self.assertFalse((self.target / "bin").exists())

    def test_a_startup_that_fails_never_raises_into_the_host(self):
        """register() and userSetup.py belong to the host's own startup.

        Blender answers an exception out of register() by deleting the module and, when
        the add-on is being enabled, dropping it from the preferences -- and with it the
        Update and Uninstall buttons that are the way out. Two shapes escaped: a pending
        uninstall whose removal failed (a second Blender still holding PySide6's DLLs),
        and a release whose import is broken. Each is now reported on the channel that
        waits, and the start carries on.
        """
        t = str(self.target)
        self.installer.write_manifest(t, pending="uninstall")
        with (
            mock.patch.object(
                self.installer,
                "uninstall",
                side_effect=RuntimeError("PySide6 is in use"),
            ),
            mock.patch.object(self.installer, "launch") as launch,
            mock.patch.object(self.installer, "_say") as say,
        ):
            self.assertIsNone(self.installer.ensure_and_launch("blender"))
        launch.assert_not_called()
        self.assertIn("PySide6 is in use", say.call_args.args[1])
        self.assertTrue(say.call_args.kwargs.get("error"))
        self.assertEqual(
            self.installer.read_manifest(t).get("pending"),
            "uninstall",
            "a removal that failed is retried at the next start",
        )

        self.installer.write_manifest(t, pending=None)
        with (
            mock.patch.object(self.installer, "is_installed", return_value=True),
            mock.patch.object(
                self.installer, "launch", side_effect=ImportError("broken release")
            ),
            mock.patch.object(self.installer, "_say") as say,
        ):
            self.assertIsNone(self.installer.ensure_and_launch("blender"))
        self.assertIn("broken release", say.call_args.args[1])
        self.assertTrue(say.call_args.kwargs.get("error"))

    def test_a_menu_that_will_not_start_after_an_install_is_reported(self):
        """The install succeeded, the user was told so -- and then the launch raised out of
        the host's timer: a traceback in Maya's script editor, and nothing at all in
        Blender, where a timer callback's error goes to the hidden system console."""
        captured = {}
        with (
            mock.patch.object(self.installer, "is_installed", return_value=False),
            mock.patch.object(self.installer, "headless", return_value=False),
            mock.patch.object(self.installer, "install", return_value=["y==2"]),
            mock.patch.object(
                self.installer,
                "_poll",
                side_effect=lambda host, finish: captured.update(finish=finish),
            ),
            mock.patch.object(self.installer, "_feedback_begin"),
            mock.patch.object(self.installer, "_feedback_end"),
            mock.patch.object(self.installer, "_report"),
            mock.patch.object(
                self.installer, "launch", side_effect=ImportError("no module uitk")
            ),
            mock.patch.object(self.installer, "_say") as say,
        ):
            self.installer.ensure_and_launch("blender")
            self.installer._worker.join(10)
            captured["finish"]()  # what the host timer calls: must not raise
        self.assertIn("no module uitk", say.call_args.args[1])
        self.assertTrue(say.call_args.kwargs.get("error"))

    def test_a_cli_install_that_did_not_take_exits_nonzero(self):
        """A deployment script reads the exit code. A failed provision printed 'install
        failed', then 'Tentacle is installed', and exited 0 -- on both hosts."""
        fake_maya = types.ModuleType("maya")
        fake_maya.cmds = mock.MagicMock()
        with (
            mock.patch.dict(
                sys.modules, {"maya": fake_maya, "maya.cmds": fake_maya.cmds}
            ),
            mock.patch.object(self.installer, "host", return_value="maya"),
            mock.patch.object(self.installer, "write_maya_module"),
            mock.patch.object(self.installer, "ensure_and_launch"),
            mock.patch.object(self.installer, "is_installed", return_value=False),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            self.assertEqual(self.installer.main(["install"]), 1)
        self.assertNotIn("is installed", out.getvalue())

        fake_bpy = types.ModuleType("bpy")
        fake_bpy.ops = mock.MagicMock()
        fake_bpy.app = types.SimpleNamespace(factory_startup=False)
        with (
            mock.patch.dict(sys.modules, {"bpy": fake_bpy}),
            mock.patch.object(self.installer, "host", return_value="blender"),
            mock.patch.object(self.installer, "is_installed", return_value=False),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.installer.main(["install"]), 1)
        fake_bpy.ops.preferences.addon_enable.assert_called_once()

    # ---------------------------------------------------------------- install lock
    def _hold_lock(self, age=0):
        """A lock some other process wrote *age* seconds ago (0 = its heartbeat is live)."""
        path = self.installer.lock_path(str(self.target))
        Path(path).write_text("999999 deadbeef", encoding="utf-8")
        if age:
            os.utime(path, (time.time() - age, time.time() - age))
        return path

    def test_provision_waits_for_a_concurrent_install_then_does_nothing(self):
        """Two Mayas starting on the same pending update provisioned into the same
        target at once (two pips writing one directory). The second now waits for the
        first's lock and, finding the install there, runs no pip at all."""
        lock = self._hold_lock()
        state = {"installed": False}

        def finish_other():
            time.sleep(0.6)
            state["installed"] = True
            os.remove(lock)

        threading.Thread(target=finish_other, daemon=True).start()
        with (
            mock.patch.object(
                self.installer, "is_installed", side_effect=lambda h: state["installed"]
            ),
            mock.patch.object(self.installer, "_run") as run,
            mock.patch.object(self.installer, "_run_checked") as checked,
            mock.patch.object(self.installer, "LOCK_POLL", 0.1),
        ):
            pins = self.installer.provision(
                "maya", target=str(self.target), python="PY"
            )
        self.assertEqual(pins, [])
        run.assert_not_called()
        checked.assert_not_called()
        self.assertFalse(os.path.exists(lock), "the lock is released afterwards")

    def test_a_stale_lock_is_claimed_not_waited_on(self):
        """A DCC killed mid-install leaves its lock behind. Once its heartbeat has been
        silent for LOCK_STALE the next install takes the lock over -- by writing its own
        token into it (see _acquire_lock for why it is never deleted) -- and runs."""
        target = str(self.target)
        path = self._hold_lock(age=self.installer.LOCK_STALE + 60)
        with (
            mock.patch.object(self.installer, "LOCK_BEAT", 0.05),
            mock.patch.object(self.installer, "LOCK_POLL", 0.1),
        ):
            with self.installer._locked(target):
                content = Path(path).read_text(encoding="utf-8")
                self.assertTrue(content.startswith(f"{os.getpid()} "), content)
                self.assertTrue(self.installer._lock_held(target))
        self.assertFalse(os.path.exists(path), "released on exit")

    def test_a_held_lock_outlives_a_long_pip(self):
        """Liveness is the holder's heartbeat, never a PID: a pip that runs longer than
        LOCK_STALE keeps its lock, and a lock nobody heartbeats goes stale."""
        target = str(self.target)
        with (
            mock.patch.object(self.installer, "LOCK_BEAT", 0.05),
            mock.patch.object(self.installer, "LOCK_STALE", 0.3),
        ):
            with self.installer._locked(target):
                time.sleep(0.7)
                self.assertTrue(self.installer._lock_held(target), "heartbeat kept it")
            self._hold_lock()
            time.sleep(0.5)
            self.assertFalse(self.installer._lock_held(target), "no heartbeat: stale")

    def test_verbs_are_refused_while_an_install_runs(self):
        """An uninstall or update against a target another process is still writing
        would race its pip; only install queues (it waits on the lock, then launches)."""
        self._hold_lock()
        with (
            mock.patch.object(self.installer, "loaded", return_value=False),
            mock.patch.object(self.installer, "uninstall") as uninstall,
            mock.patch.object(self.installer, "_provision_async") as provision,
        ):
            refused = self.installer.request("blender", "uninstall")
            self.installer.request("blender", "update")
        uninstall.assert_not_called()
        provision.assert_not_called()
        self.assertIn("install", refused.lower())
        self.assertIsNone(
            self.installer.read_manifest(str(self.target)).get("pending"),
            "a refused verb must not be recorded as pending either",
        )
        with mock.patch.object(self.installer, "ensure_and_launch") as ensure:
            self.installer.request("blender", "install")
        ensure.assert_called_once_with("blender")

    def test_a_second_process_on_one_pending_update_runs_no_pip(self):
        """Two sessions starting on one pending update both run an upgrade provision.

        The lock serialised them, but ``pending`` was cleared only once ``provision``
        had returned -- outside the lock -- and the one early return under it covered
        a fresh install that appeared while waiting. So the second process re-ran the
        whole upgrade the moment the first let go. The first now clears ``pending``
        under the lock, and a process that finds the verb it came for already done
        runs no pip.
        """
        target = str(self.target)
        self.installer.write_manifest(target, pending="update")
        upgrades = []
        first_inside = threading.Event()
        second_queued = threading.Event()

        class FakePackageManager:
            def __init__(self, python_path):
                pass

            def install_targeted(self, specs, target, upgrade=False):
                upgrades.append(upgrade)
                first_inside.set()
                second_queued.wait(5)  # hold the lock until the other one queues on it
                return ["tentacletk==2"]

        real_lock_held = self.installer._lock_held

        def lock_held(target_dir):
            second_queued.set()  # only a process waiting behind the holder asks this
            return real_lock_held(target_dir)

        fake_ptk = types.ModuleType("pythontk")
        fake_ptk.PackageManager = FakePackageManager
        pins = {}

        def start(name):
            pins[name] = self.installer.provision(
                "maya", upgrade=True, target=target, python="PY"
            )

        with (
            mock.patch.dict(sys.modules, {"pythontk": fake_ptk}),
            mock.patch.object(self.installer, "_has", return_value=True),
            mock.patch.object(self.installer, "is_installed", return_value=True),
            mock.patch.object(
                self.installer, "_run", return_value=types.SimpleNamespace(returncode=0)
            ) as run,
            mock.patch.object(self.installer, "_run_checked") as checked,
            mock.patch.object(self.installer, "_lock_held", side_effect=lock_held),
            mock.patch.object(self.installer, "LOCK_BEAT", 0.05),
            mock.patch.object(self.installer, "LOCK_POLL", 0.05),
        ):
            first = threading.Thread(target=start, args=("first",), daemon=True)
            first.start()
            self.assertTrue(first_inside.wait(5), "the first upgrade never started")
            start("second")
            first.join(5)

        self.assertEqual(upgrades, [True], "the second process ran the upgrade again")
        self.assertEqual((pins["first"], pins["second"]), (["tentacletk==2"], []))
        run.assert_called_once()  # the first process's ``pip --version``, nobody else's
        checked.assert_not_called()
        self.assertIsNone(self.installer.read_manifest(target).get("pending"))
        self.assertFalse(os.path.exists(self.installer.lock_path(target)))

    def test_a_failed_upgrade_is_run_again_by_the_process_queued_behind_it(self):
        """A waiter skips an update only when one actually FINISHED while it waited.

        ``pending`` cannot tell it that on its own: a failed upgrade that has been
        reported clears it as well (so a dead index does not error at every start), and
        that clear lands milliseconds after the lock is released -- before the queued
        process gets its turn. Keyed on ``pending`` alone, the queued process read the
        failure as done, ran nothing and reported the update as applied.
        """
        target = str(self.target)
        self.installer.write_manifest(target, pending="update")
        upgrades = []
        first_inside = threading.Event()
        second_queued = threading.Event()
        first_reported = threading.Event()

        class FlakyPackageManager:
            def __init__(self, python_path):
                pass

            def install_targeted(self, specs, target, upgrade=False):
                upgrades.append(upgrade)
                if len(upgrades) > 1:
                    return ["tentacletk==2"]
                first_inside.set()
                second_queued.wait(5)
                raise RuntimeError("no route to PyPI")

        real_acquire = self.installer._acquire_lock

        def acquire(target_dir, token):
            if threading.current_thread() is threading.main_thread():
                second_queued.set()  # the second process has read what it came for
                first_reported.wait(5)  # ...and gets its turn after the report
            return real_acquire(target_dir, token)

        fake_ptk = types.ModuleType("pythontk")
        fake_ptk.PackageManager = FlakyPackageManager
        with (
            mock.patch.dict(sys.modules, {"pythontk": fake_ptk}),
            mock.patch.object(self.installer, "_has", return_value=True),
            mock.patch.object(self.installer, "is_installed", return_value=True),
            mock.patch.object(self.installer, "headless", return_value=True),
            mock.patch.object(
                self.installer, "_run", return_value=types.SimpleNamespace(returncode=0)
            ),
            mock.patch.object(self.installer, "_acquire_lock", side_effect=acquire),
            mock.patch.object(
                self.installer, "launch", side_effect=lambda h: first_reported.set()
            ) as launch,
        ):
            first = threading.Thread(
                target=self.installer.ensure_and_launch, args=("maya",), daemon=True
            )
            first.start()
            self.assertTrue(first_inside.wait(5), "the first upgrade never started")
            pins = self.installer.provision(
                "maya", upgrade=True, target=target, python="PY"
            )
            first.join(5)

        launch.assert_called_once_with("maya")  # reported, then launched
        self.assertEqual(upgrades, [True, True], "the failed upgrade was read as done")
        self.assertEqual(pins, ["tentacletk==2"])
        self.assertIsNone(self.installer.read_manifest(target).get("pending"))

    def test_a_stale_lock_that_cannot_be_claimed_still_gives_up_at_the_deadline(self):
        """LOCK_WAIT was checked only while a LIVE holder kept the lock.

        A stale lock this process cannot write its token into (read-only, another
        account's) never gets a fresh mtime, so every pass took the stale-claim branch,
        which never looked at the deadline: the wait spun for good -- a start that
        never finishes -- instead of ending in the "held for over N minutes" report.
        """
        target = str(self.target)
        path = self._hold_lock(age=self.installer.LOCK_STALE + 60)
        real_open = open

        def refuse_the_claim(file, mode="r", *args, **kwargs):
            if "w" in mode and os.path.normcase(str(file)) == os.path.normcase(path):
                raise PermissionError(13, "Access is denied", str(file))
            return real_open(file, mode, *args, **kwargs)

        outcome = {}

        def wait():
            outcome["acquired"] = self.installer._acquire_lock(target, "token")

        with (
            mock.patch.object(
                self.module, "open", create=True, side_effect=refuse_the_claim
            ),
            mock.patch.object(self.installer, "LOCK_WAIT", 0.3),
            mock.patch.object(self.installer, "LOCK_BEAT", 0.005),
            mock.patch.object(self.installer, "LOCK_POLL", 0.01),
        ):
            waiter = threading.Thread(target=wait, daemon=True)
            waiter.start()
            waiter.join(5)
            self.assertFalse(waiter.is_alive(), "the wait ran on past LOCK_WAIT")
        self.assertIs(outcome.get("acquired"), False)

    def test_a_lock_windows_refuses_to_create_is_waited_on_like_a_held_one(self):
        """``os.open(O_CREAT | O_EXCL)`` answers PermissionError on Windows, not
        FileExistsError, for a lock another process is deleting or has open (a sharing
        violation). Only FileExistsError was caught, so that moment of contention
        crashed the start instead of being waited out."""
        target = str(self.target)
        path = self.installer.lock_path(target)
        real_os_open = os.open
        refused = []

        def refuse_once(file, flags, *args, **kwargs):
            if not refused and os.path.normcase(str(file)) == os.path.normcase(path):
                refused.append(file)
                raise PermissionError(13, "Access is denied", str(file))
            return real_os_open(file, flags, *args, **kwargs)

        with (
            mock.patch.object(self.module.os, "open", side_effect=refuse_once),
            mock.patch.object(self.installer, "LOCK_BEAT", 0.005),
            mock.patch.object(self.installer, "LOCK_POLL", 0.01),
        ):
            self.assertTrue(self.installer._acquire_lock(target, "token"))
        self.assertEqual(len(refused), 1)
        self.assertEqual(Path(path).read_text(encoding="utf-8"), "token")

    def test_a_lock_that_stays_refused_is_an_error_not_a_wait(self):
        """A refusal outlasting LOCK_STALE is no lock state -- nothing takes that long
        to delete -- but a folder this user cannot write (a read-only scripts share).
        It raises that error instead of waiting out LOCK_WAIT and then blaming
        "another install" for a lock that was never there."""
        target = str(self.target)
        path = self.installer.lock_path(target)
        real_os_open = os.open

        def refuse(file, flags, *args, **kwargs):
            if os.path.normcase(str(file)) == os.path.normcase(path):
                raise PermissionError(13, "Access is denied", str(file))
            return real_os_open(file, flags, *args, **kwargs)

        started = time.time()
        with (
            mock.patch.object(self.module.os, "open", side_effect=refuse),
            mock.patch.object(self.installer, "LOCK_STALE", 0.05),
            mock.patch.object(self.installer, "LOCK_WAIT", 3),
            mock.patch.object(self.installer, "LOCK_BEAT", 0.005),
            mock.patch.object(self.installer, "LOCK_POLL", 0.01),
        ):
            with self.assertRaises(PermissionError):
                self.installer._acquire_lock(target, "token")
        self.assertLess(time.time() - started, 2, "waited instead of raising")
        self.assertFalse(os.path.exists(path))

    # ---------------------------------------------------------------- pending verbs
    def test_a_direct_update_keeps_an_uninstall_queued_while_it_ran(self):
        """A write-out clears only the verb its own process settled.

        Update with nothing pending (``mayapy tentacle_installer.py update``) while
        another session, menu loaded, chooses Uninstall: both writes that follow the
        pip -- under the lock, then in ``install`` -- blanked ``pending``, and that
        user's Uninstall silently never happened. The update is still stamped.
        """
        target = str(self.target)
        installer = self.installer

        class QueuingPackageManager:
            def __init__(self, python_path):
                pass

            def install_targeted(self, specs, target_dir, upgrade=False):
                installer.write_manifest(target_dir, pending="uninstall")
                return ["tentacletk==2"]

        fake_ptk = types.ModuleType("pythontk")
        fake_ptk.PackageManager = QueuingPackageManager
        with (
            mock.patch.dict(sys.modules, {"pythontk": fake_ptk}),
            mock.patch.object(installer, "_has", return_value=True),
            mock.patch.object(installer, "is_installed", return_value=True),
            mock.patch.object(
                installer, "_run", return_value=types.SimpleNamespace(returncode=0)
            ),
        ):
            self.assertEqual(installer.update("maya", target), ["tentacletk==2"])
        data = installer.read_manifest(target)
        self.assertEqual(data.get("pending"), "uninstall", "the Uninstall was dropped")
        self.assertIsNotNone(data.get("updated"), "the update must be stamped anyway")

    def test_install_clears_only_the_verb_it_carried_out(self):
        """``install``'s own write-out, with provisioning stubbed: a fresh install
        carries out no verb, so it clears none; an upgrade clears a pending update and
        nothing else. It still clears a value that is no verb at all, and it always
        leaves the key -- the live clean rooms read ``manifest["pending"]``."""
        cases = (
            # upgrade, pending at start, queued by another session meanwhile, after
            (True, None, "uninstall", "uninstall"),
            (False, None, "uninstall", "uninstall"),
            (False, None, "update", "update"),
            (True, "update", None, None),
            (False, None, None, None),
            (False, "no-such-verb", None, None),
        )
        for i, (upgrade, pending, queued, expected) in enumerate(cases):
            with self.subTest(upgrade=upgrade, pending=pending, queued=queued):
                target = self.target / f"case{i}"
                target.mkdir()
                if pending:
                    self.installer.write_manifest(str(target), pending=pending)

                def provision(host, queued=queued, **kwargs):
                    if queued:
                        self.installer.write_manifest(kwargs["target"], pending=queued)
                    return ["tentacletk==2"]

                with mock.patch.object(
                    self.installer, "provision", side_effect=provision
                ):
                    self.installer.install(
                        "blender", str(target), "PY", upgrade=upgrade
                    )
                data = self.installer.read_manifest(str(target))
                self.assertIn("pending", data)
                self.assertEqual(data["pending"], expected)

    def test_the_headless_failure_report_clears_only_its_own_update(self):
        """A failed update that has been reported still drops its own ``pending``
        rather than retry it at every start -- but only that: an Uninstall another
        session chose while the pip ran is kept."""
        target = str(self.target)
        self.installer.write_manifest(target, pending="update")

        def failing_install(host, target_dir, upgrade=False):
            self.installer.write_manifest(target_dir, pending="uninstall")
            raise RuntimeError("offline")

        with (
            mock.patch.object(self.installer, "headless", return_value=True),
            mock.patch.object(self.installer, "is_installed", return_value=True),
            mock.patch.object(self.installer, "install", side_effect=failing_install),
            mock.patch.object(self.installer, "launch") as launch,
        ):
            self.installer.ensure_and_launch("maya")
        launch.assert_called_once_with("maya")
        self.assertEqual(
            self.installer.read_manifest(target).get("pending"), "uninstall"
        )

    def test_the_gui_failure_report_clears_only_its_own_update(self):
        """The same rule on the worker path, where ``finish`` reports the failure."""
        target = str(self.target)
        for queued, expected in (("uninstall", "uninstall"), (None, None)):
            with self.subTest(queued=queued):
                self.installer.write_manifest(target, pending="update")

                def failing_install(host, target_dir, python, upgrade=False, q=queued):
                    if q:
                        self.installer.write_manifest(target_dir, pending=q)
                    raise RuntimeError("offline")

                def poll(host, finish):
                    self.installer._worker.join(10)
                    finish()

                with (
                    mock.patch.object(self.installer, "headless", return_value=False),
                    mock.patch.object(
                        self.installer, "is_installed", return_value=True
                    ),
                    mock.patch.object(
                        self.installer, "install", side_effect=failing_install
                    ),
                    mock.patch.object(self.installer, "_poll", side_effect=poll),
                    mock.patch.object(self.installer, "_feedback_begin"),
                    mock.patch.object(self.installer, "_feedback_end"),
                    mock.patch.object(self.installer, "launch") as launch,
                ):
                    self.installer.ensure_and_launch("blender")
                launch.assert_called_once_with("blender")
                self.assertEqual(
                    self.installer.read_manifest(target).get("pending"), expected
                )

    def test_provision_bootstraps_pythontk_then_delegates_to_install_targeted(self):
        calls = {}

        class FakePackageManager:
            def __init__(self, python_path):
                calls["python"] = python_path

            def install_targeted(self, specs, target, upgrade=False):
                calls["targeted"] = (list(specs), target, upgrade)
                return ["blendertk==0.5.84"]

        fake_ptk = types.ModuleType("pythontk")
        fake_ptk.PackageManager = FakePackageManager
        os.environ.pop("PIP_RETRIES", None)
        with (
            mock.patch.dict(sys.modules, {"pythontk": fake_ptk}),
            mock.patch.object(
                self.installer, "_has", side_effect=lambda name: name != "pythontk"
            ),
            mock.patch.object(
                self.installer, "_run", return_value=types.SimpleNamespace(returncode=0)
            ) as run,
            mock.patch.object(self.installer, "_run_checked") as run_checked,
        ):
            pins = self.installer.provision("blender", upgrade=True)
        self.assertEqual(pins, ["blendertk==0.5.84"])
        run.assert_called_once_with(["PY", "-s", "-m", "pip", "--version"])
        run_checked.assert_called_once()
        self.assertEqual(
            run_checked.call_args.args[0],
            ["PY", "-s", "-m", "pip", "install", "--no-deps", "--upgrade", "pythontk"],
        )
        self.assertEqual(
            run_checked.call_args.kwargs["env"]["PIP_TARGET"],
            str(self.target),
            "the bootstrap's target rides PIP_TARGET (see TestBootstrapTarget)",
        )
        self.assertEqual(calls["python"], "PY")
        self.assertEqual(
            calls["targeted"], (["tentacletk[blender]"], str(self.target), True)
        )
        self.assertNotIn(
            "PIP_RETRIES", os.environ, "pip env must be restored after the run"
        )

    def test_provision_skips_the_bootstrap_when_pythontk_resolves(self):
        fake_ptk = types.ModuleType("pythontk")
        fake_ptk.PackageManager = type(
            "PM",
            (),
            {
                "__init__": lambda self, python_path: None,
                "install_targeted": lambda self, specs, target, upgrade=False: [],
            },
        )
        with (
            mock.patch.dict(sys.modules, {"pythontk": fake_ptk}),
            mock.patch.object(self.installer, "_has", return_value=True),
            mock.patch.object(
                self.installer, "_run", return_value=types.SimpleNamespace(returncode=1)
            ) as run,
            mock.patch.object(self.installer, "_run_checked") as run_checked,
        ):
            self.installer.provision("maya")
        run_checked.assert_not_called()
        self.assertEqual(
            run.call_args_list[1].args[0][1:],
            ["-m", "ensurepip", "--upgrade"],
            "no pip -> ensurepip",
        )

    def test_provision_rejects_a_pythontk_without_install_targeted(self):
        fake_ptk = types.ModuleType("pythontk")  # an old copy earlier on sys.path
        with (
            mock.patch.dict(sys.modules, {"pythontk": fake_ptk}),
            mock.patch.object(self.installer, "_has", return_value=True),
            mock.patch.object(
                self.installer, "_run", return_value=types.SimpleNamespace(returncode=0)
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "too old"):
                self.installer.provision("maya")

    def test_provision_fails_loudly_when_nothing_imports_afterwards(self):
        fake_ptk = types.ModuleType("pythontk")
        fake_ptk.PackageManager = type(
            "PM",
            (),
            {
                "__init__": lambda self, python_path: None,
                "install_targeted": lambda self, specs, target, upgrade=False: [],
            },
        )
        with (
            mock.patch.dict(sys.modules, {"pythontk": fake_ptk}),
            mock.patch.object(
                self.installer, "_has", side_effect=lambda name: name == "pythontk"
            ),
            mock.patch.object(
                self.installer, "_run", return_value=types.SimpleNamespace(returncode=0)
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "do not import"):
                self.installer.provision("maya")

    def test_main_parses_the_verb_and_delegates(self):
        with (
            mock.patch.object(self.installer, "host", return_value="blender"),
            mock.patch.object(self.installer, "request", return_value="ok") as request,
        ):
            self.assertEqual(self.installer.main(["--", "uninstall"]), 0)
            request.assert_called_once_with("blender", "uninstall")
            request.side_effect = RuntimeError("boom")
            self.assertEqual(self.installer.main(["update"]), 1)


@unittest.skipUnless(
    LIVE, "set TENTACLE_LIVE_INSTALL=1 (downloads from PyPI, PySide6 included)"
)
class TestLiveBlenderCleanRoom(unittest.TestCase):
    """Real Blender, fresh profile, real PyPI: add-on install -> every start is a no-op ->
    uninstall requested from a running session -> applied at the next start."""

    @classmethod
    def setUpClass(cls):
        cls.blender = _find_blender()
        if not cls.blender:
            raise unittest.SkipTest("blender.exe not found")
        # A space and non-ASCII letters, like the profile dir of a user named José. The
        # dir must EXIST before Blender starts: pointed at a missing one, Blender silently
        # falls back to the REAL user profile (measured on 5.1.2).
        cls.res = TEMP / "blender res Jösé"
        shutil.rmtree(cls.res, ignore_errors=True)
        cls.res.mkdir(parents=True)
        cls.env = _clean_env(cls.res / "userbase", BLENDER_USER_RESOURCES=str(cls.res))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.res, ignore_errors=True)

    def _run(self, expr, factory=True, timeout=LIVE_TIMEOUT):
        args = (
            [self.blender, "--background"]
            + (["--factory-startup"] if factory else [])
            + ["--python-expr", expr]
        )
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            errors="replace",
            env=self.env,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout + proc.stderr

    def test_install_noop_start_then_uninstall_at_next_start(self):
        names = ("tentacle", "blendertk", "pythontk", "uitk", "qtpy", "PySide6")
        out1 = self.res / "report1.json"
        expr = textwrap.dedent(f"""
            import bpy, json, importlib.util, os
            bpy.ops.preferences.addon_install(filepath=r"{INSTALLER}", overwrite=True)
            bpy.ops.preferences.addon_enable(module="tentacle_installer")
            bpy.ops.wm.save_userpref()
            spec = importlib.util.find_spec
            rep = {{n: (spec(n).origin if spec(n) else None) for n in {names!r}}}
            rep["target"] = bpy.utils.user_resource("SCRIPTS", path="addons/modules")
            rep["addon"] = os.path.join(bpy.utils.user_resource("SCRIPTS", path="addons"), "tentacle_installer.py")
            import tentacle_installer as m
            rep["manifest"] = m.TentacleInstaller.read_manifest(rep["target"])
            rep["version"] = m.TentacleInstaller.installed_version(rep["target"])
            json.dump(rep, open(r"{out1}", "w"))
        """)
        rc, out = self._run(expr)
        self.assertEqual(rc, 0, out[-3000:])
        rep = json.loads(out1.read_text())
        self.assertIn("[tentacle] installed", out, out[-3000:])
        self.assertTrue(
            os.path.isfile(rep["addon"]),
            "Blender did not copy the add-on into its addons dir",
        )
        for name in names:
            self.assertIsNotNone(
                rep[name], f"{name} does not import after install: {rep}"
            )
            self.assertTrue(
                _under(rep[name], rep["target"]),
                f"{name} resolved outside the target: {rep[name]}",
            )
        self.assertTrue(
            rep["manifest"]["pins"] and rep["manifest"]["pending"] is None,
            rep["manifest"],
        )
        self.assertTrue(rep["version"], "installed_version must read the dist-info")

        # Start 2: enabled add-on, nothing to do; then the user asks for an uninstall while
        # the menu is loaded -> recorded as pending, nothing removed yet.
        out2 = self.res / "report2.json"
        expr = textwrap.dedent(f"""
            import bpy, json, importlib.util, sys
            import tentacle_installer as m
            msg = m.TentacleInstaller.request("blender", "uninstall")
            target = bpy.utils.user_resource("SCRIPTS", path="addons/modules")
            rep = {{"tentacle": importlib.util.find_spec("tentacle").origin, "msg": msg,
                    "enabled": "tentacle_installer" in bpy.context.preferences.addons,
                    "pending": m.TentacleInstaller.read_manifest(target).get("pending")}}
            json.dump(rep, open(r"{out2}", "w"))
        """)
        rc, out = self._run(expr, factory=False, timeout=300)
        self.assertEqual(rc, 0, out[-3000:])
        rep = json.loads(out2.read_text())
        self.assertNotIn(
            "Installing tentacle", out, "a second start must not provision again"
        )
        self.assertTrue(rep["enabled"], rep)
        self.assertEqual(rep["pending"], "uninstall", rep)
        self.assertIn("restart", rep["msg"])
        self.assertTrue(
            _under(rep["tentacle"], self.res), "nothing may be removed while loaded"
        )

        # Start 3: the pending uninstall completes before anything is imported; no launch.
        out3 = self.res / "report3.json"
        expr = textwrap.dedent(f"""
            import bpy, json, importlib.util, os, sys
            target = bpy.utils.user_resource("SCRIPTS", path="addons/modules")
            spec = importlib.util.find_spec
            rep = {{n: (spec(n).origin if spec(n) else None) for n in {names!r}}}
            rep["manifest_exists"] = os.path.isfile(os.path.join(target, "tentacle_installer.json"))
            rep["addon_exists"] = os.path.isfile(os.path.join(bpy.utils.user_resource("SCRIPTS", path="addons"), "tentacle_installer.py"))
            rep["tcl_loaded"] = "tentacle.tcl_blender" in sys.modules
            rep["left_in_target"] = sorted(os.listdir(target)) if os.path.isdir(target) else []
            json.dump(rep, open(r"{out3}", "w"))
        """)
        rc, out = self._run(expr, factory=False, timeout=600)
        self.assertEqual(rc, 0, out[-3000:])
        rep = json.loads(out3.read_text())
        self.assertIn("Tentacle uninstalled", out, out[-3000:])
        for name in ("tentacle", "blendertk", "uitk", "pythontk", "PySide6", "qtpy"):
            self.assertIsNone(
                rep[name], f"{name} still imports after uninstall: {rep[name]}"
            )
        self.assertFalse(
            rep["manifest_exists"] or rep["addon_exists"] or rep["tcl_loaded"], rep
        )
        self.assertEqual(
            rep["left_in_target"],
            [],
            "the uninstall left files in the SHARED addons/modules (pip's bin/ launchers?)",
        )


@unittest.skipUnless(LIVE, "set TENTACLE_LIVE_INSTALL=1 (downloads from PyPI)")
class TestLiveMayaCleanRoom(unittest.TestCase):
    """Real mayapy, fresh MAYA_APP_DIR, real PyPI: command-line install -> Maya autoloads the
    module -> update requested while loaded -> applied at the next start -> command-line
    uninstall (immediate) -> a start with nothing left."""

    @classmethod
    def setUpClass(cls):
        cls.mayapy = _find_mayapy()
        if not cls.mayapy:
            raise unittest.SkipTest("mayapy.exe not found")
        # A space and non-ASCII letters, like the prefs dir of a user named José: an
        # absolute module path in the .mod never loaded there (measured on Maya 2025).
        cls.app = TEMP / "maya app Jösé"
        shutil.rmtree(cls.app, ignore_errors=True)
        cls.app.mkdir(parents=True)
        cls.env = _clean_env(cls.app / "userbase", MAYA_APP_DIR=str(cls.app))
        cls.startup = _load().TentacleInstaller.MAYA_STARTUP

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.app, ignore_errors=True)

    def _run(self, args, timeout=LIVE_TIMEOUT, **paths):
        # cwd is the sandbox: ``-c`` puts the working directory on sys.path[0], and run from
        # the monorepo that makes every repo folder resolve as an EMPTY namespace package.
        # *paths* reach the ``-c`` program as LIVE_<NAME> environment variables, never
        # inside it: mayapy.exe decodes its command line as UTF-8 from the ANSI code page,
        # so a program naming the sandbox (a non-ASCII dir) would not even parse.
        env = {**self.env, **{f"LIVE_{k.upper()}": str(v) for k, v in paths.items()}}
        proc = subprocess.run(
            [self.mayapy] + args,
            capture_output=True,
            text=True,
            errors="replace",
            env=env,
            cwd=str(self.app),
            timeout=timeout,
        )
        return proc.returncode, proc.stdout + proc.stderr

    def _report(self, extra=""):
        """A ``-c`` program recording what this start imports into ``LIVE_OUT``."""
        return textwrap.dedent(f"""
            import maya.standalone; maya.standalone.initialize()
            import importlib.util, json, os, sys
            from maya import cmds
            find = importlib.util.find_spec
            names = ("tentacle", "mayatk", "pythontk", "uitk", "qtpy")
            rep = {{n: (find(n).origin if find(n) else None) for n in names}}
            rep["modules"] = cmds.moduleInfo(listModules=True)
            rep["startup_loaded"] = "{self.startup}" in sys.modules
            rep["version"] = cmds.about(version=True)
            {extra}
            json.dump(rep, open(os.environ["LIVE_OUT"], "w"))
        """)

    def test_cli_install_autoload_update_at_next_start_then_uninstall(self):
        # 1. command-line install: writes the module, provisions, no userSetup involved.
        rc, out = self._run([str(INSTALLER), "install"])
        self.assertEqual(rc, 0, out[-3000:])
        self.assertIn("[tentacle] installed", out, out[-3000:])
        version_dirs = [
            p for p in self.app.iterdir() if p.is_dir() and p.name.isdigit()
        ]
        self.assertEqual(len(version_dirs), 1, version_dirs)
        root = version_dirs[0] / "tentacle"
        site = root / "site"
        mod = version_dirs[0] / "modules" / "tentacle.mod"
        self.assertTrue(mod.is_file() and (root / "scripts" / "userSetup.py").is_file())

        # 2. plain start: the .mod autoloads, userSetup launches; then an update is requested
        #    while loaded -> pending. Then a NEWER installer is re-dropped the way Maya's
        #    drop executor does it: the dropped file must be the one that runs (not the
        #    cached startup copy), and it must refresh that copy with itself.
        out2 = self.app / "report2.json"
        newer = self.app / "downloads" / "tentacle_installer.py"
        extra = """
            import __STARTUP__ as m
            SITE, NEWER = os.environ["LIVE_SITE"], os.environ["LIVE_NEWER"]
            rep["msg"] = m.TentacleInstaller.request("maya", "update")
            norm = lambda p: os.path.normcase(os.path.normpath(p))
            rep["site_idx"] = [i for i, p in enumerate(sys.path) if norm(p) == norm(SITE)]
            rep["site_packages_idx"] = [i for i, p in enumerate(sys.path) if "autodesk" in norm(p) and norm(p).endswith("site-packages")]
            os.makedirs(os.path.dirname(NEWER), exist_ok=True)
            with open(os.environ["LIVE_INSTALLER"], 'rb') as src, open(NEWER, 'wb') as dst:
                dst.write(src.read() + b'\\n# newer build\\n')
            sys.path.insert(0, os.path.dirname(NEWER))
            dropped = importlib.import_module('tentacle_installer')
            dropped.onMayaDroppedPythonFile(None)  # no dialog in batch -> Cancel
            sys.path.pop(0)
            rep["dropped_file"] = dropped.__file__
            with open(os.path.join(os.path.dirname(SITE), 'scripts', '__STARTUP__.py'), 'rb') as fh:
                rep["startup_refreshed"] = fh.read().endswith(b'# newer build\\n')
            rep["pending"] = m.TentacleInstaller.read_manifest(SITE).get("pending")
        """.replace("__STARTUP__", self.startup)
        rc, out = self._run(
            ["-c", self._report(extra)],
            timeout=600,
            out=out2,
            site=site,
            newer=newer,
            installer=INSTALLER,
        )
        self.assertEqual(rc, 0, out[-3000:])
        rep = json.loads(out2.read_text())
        self.assertNotIn("Installing tentacle", out, "a plain start must not provision")
        self.assertIn("tentacle", rep["modules"], "Maya did not load the .mod")
        self.assertTrue(rep["startup_loaded"], "the module's userSetup.py did not run")
        self.assertEqual(
            os.path.normcase(rep["dropped_file"]),
            os.path.normcase(str(newer)),
            "a re-drop must run the dropped file, not the cached startup copy",
        )
        self.assertTrue(
            rep["startup_refreshed"], "a re-drop must refresh the startup copy"
        )
        for name in ("tentacle", "mayatk", "pythontk", "uitk", "qtpy"):
            self.assertTrue(
                rep[name] and _under(rep[name], site), f"{name}: {rep[name]}"
            )
        self.assertGreater(
            rep["site_idx"][0],
            rep["site_packages_idx"][-1],
            "module site must sit AFTER Maya's site-packages",
        )
        self.assertIn("restart", rep["msg"])
        self.assertEqual(rep["pending"], "update")

        # 3. next start applies the update (nothing newer: fast) and launches.
        out3 = self.app / "report3.json"
        extra = """
            import __STARTUP__ as m
            rep["pending"] = m.TentacleInstaller.read_manifest(os.environ["LIVE_SITE"]).get("pending")
        """.replace("__STARTUP__", self.startup)
        rc, out = self._run(
            ["-c", self._report(extra)], timeout=900, out=out3, site=site
        )
        self.assertEqual(rc, 0, out[-3000:])
        rep = json.loads(out3.read_text())
        self.assertIn(
            "[tentacle] installed", out, "the pending update must run at start"
        )
        self.assertIsNone(rep["pending"])
        self.assertTrue(rep["tentacle"] and _under(rep["tentacle"], site))

        # 4. command-line uninstall: immediate (userSetup skipped, nothing loaded).
        rc, out = self._run([str(INSTALLER), "uninstall"], timeout=600)
        self.assertEqual(rc, 0, out[-3000:])
        self.assertIn("Tentacle uninstalled", out, out[-3000:])
        self.assertFalse(root.exists(), "module root must be gone")
        self.assertFalse(mod.exists(), ".mod must be gone")

        # 5. a start with nothing left: no module, nothing imports, nothing printed.
        out5 = self.app / "report5.json"
        rc, out = self._run(["-c", self._report()], timeout=600, out=out5)
        self.assertEqual(rc, 0, out[-3000:])
        rep = json.loads(out5.read_text())
        self.assertNotIn("tentacle", rep["modules"])
        self.assertFalse(rep["startup_loaded"])
        self.assertIsNone(rep["tentacle"])
        self.assertNotIn("[tentacle]", out)


if __name__ == "__main__":
    unittest.main()
