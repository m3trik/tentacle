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
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import textwrap
import threading
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

    def test_spec_names_strips_extras_and_version_pins(self):
        self.assertEqual(
            self.installer._spec_names(
                ["tentacletk[blender]==1.2.3", "pythontk>=0.9", "PySide6", ""]
            ),
            ["PySide6", "pythontk", "tentacletk"],
        )

    def test_a_failed_install_still_records_what_it_was_installing(self):
        """A part-provisioned Blender target must not orphan shared dists.

        install() only wrote the manifest AFTER provision() returned, so a provision
        that raised left PySide6/pythontk in the shared addons/modules with nothing
        recording them -- and a later uninstall read no pins, removed nothing, and
        deleted the add-on that was the only way to retry.
        """
        t = str(self.target)
        with (
            mock.patch.object(
                self.installer, "specs", return_value=["tentacletk[blender]==1.2"]
            ),
            mock.patch.object(self.installer, "python_exe", return_value="PY"),
            mock.patch.object(
                self.installer, "provision", side_effect=RuntimeError("pip blew up")
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.installer.install("blender", t)

        self.assertEqual(
            self.installer.read_manifest(t)["pins"],
            ["tentacletk"],
            "a failed install recorded nothing to uninstall",
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
            r"(?m)^\+ tentacle \d+\.\d+ .*[\\/]2025[\\/]tentacle\s*$",
            text.splitlines()[0],
        )
        self.assertIn(
            "PYTHONPATH +:= site",
            text,
            "the site dir must ride the module's PYTHONPATH",
        )
        scripts = Path(root) / "scripts"
        self.assertEqual(
            (scripts / "tentacle_installer.py").read_bytes(),
            INSTALLER.read_bytes(),
            "the module must carry a verbatim copy of the installer",
        )
        user_setup = (scripts / "userSetup.py").read_text(encoding="utf-8")
        self.assertIn("import tentacle_installer", user_setup)
        self.assertIn("ensure_and_launch('maya')", user_setup)
        self.assertTrue((Path(root) / "site").is_dir())

    def test_rerun_is_idempotent_and_survives_dropping_the_copy(self):
        root = self.installer.write_maya_module(str(INSTALLER), str(self.app), "2025")
        first = {p: p.read_bytes() for p in Path(self.app).rglob("*") if p.is_file()}
        self.installer.write_maya_module(str(INSTALLER), str(self.app), "2025")
        # Dropping the module's own copy onto the viewport must not raise on copyfile.
        self.installer.write_maya_module(
            str(Path(root) / "scripts" / "tentacle_installer.py"), str(self.app), "2025"
        )
        second = {p: p.read_bytes() for p in Path(self.app).rglob("*") if p.is_file()}
        self.assertEqual(first, second)

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
        run_checked.assert_called_once_with(
            [
                "PY",
                "-s",
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--upgrade",
                "--target",
                str(self.target),
                "pythontk",
            ]
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
        cls.res = TEMP / "blender_res"
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
        cls.app = TEMP / "maya_app"
        shutil.rmtree(cls.app, ignore_errors=True)
        cls.app.mkdir(parents=True)
        cls.env = _clean_env(cls.app / "userbase", MAYA_APP_DIR=str(cls.app))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.app, ignore_errors=True)

    def _run(self, args, timeout=LIVE_TIMEOUT):
        # cwd is the sandbox: ``-c`` puts the working directory on sys.path[0], and run from
        # the monorepo that makes every repo folder resolve as an EMPTY namespace package.
        proc = subprocess.run(
            [self.mayapy] + args,
            capture_output=True,
            text=True,
            errors="replace",
            env=self.env,
            cwd=str(self.app),
            timeout=timeout,
        )
        return proc.returncode, proc.stdout + proc.stderr

    def _report(self, out_file, extra=""):
        return textwrap.dedent(f"""
            import maya.standalone; maya.standalone.initialize()
            import importlib.util, json, os, sys
            from maya import cmds
            find = importlib.util.find_spec
            names = ("tentacle", "mayatk", "pythontk", "uitk", "qtpy")
            rep = {{n: (find(n).origin if find(n) else None) for n in names}}
            rep["modules"] = cmds.moduleInfo(listModules=True)
            rep["installer_loaded"] = "tentacle_installer" in sys.modules
            rep["version"] = cmds.about(version=True)
            {extra}
            json.dump(rep, open(r"{out_file}", "w"))
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
        #    while loaded -> pending.
        out2 = self.app / "report2.json"
        extra = """
            import tentacle_installer as m
            rep["msg"] = m.TentacleInstaller.request("maya", "update")
            rep["pending"] = m.TentacleInstaller.read_manifest(r'__SITE__').get("pending")
            norm = lambda p: os.path.normcase(os.path.normpath(p))
            rep["site_idx"] = [i for i, p in enumerate(sys.path) if norm(p) == norm(r'__SITE__')]
            rep["site_packages_idx"] = [i for i, p in enumerate(sys.path) if "autodesk" in norm(p) and norm(p).endswith("site-packages")]
        """.replace("__SITE__", str(site))
        rc, out = self._run(["-c", self._report(out2, extra)], timeout=600)
        self.assertEqual(rc, 0, out[-3000:])
        rep = json.loads(out2.read_text())
        self.assertNotIn("Installing tentacle", out, "a plain start must not provision")
        self.assertIn("tentacle", rep["modules"], "Maya did not load the .mod")
        self.assertTrue(
            rep["installer_loaded"], "the module's userSetup.py did not run"
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
            import tentacle_installer as m
            rep["pending"] = m.TentacleInstaller.read_manifest(r'__SITE__').get("pending")
        """.replace("__SITE__", str(site))
        rc, out = self._run(["-c", self._report(out3, extra)], timeout=900)
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
        rc, out = self._run(["-c", self._report(out5)], timeout=600)
        self.assertEqual(rc, 0, out[-3000:])
        rep = json.loads(out5.read_text())
        self.assertNotIn("tentacle", rep["modules"])
        self.assertFalse(rep["installer_loaded"])
        self.assertIsNone(rep["tentacle"])
        self.assertNotIn("[tentacle]", out)


if __name__ == "__main__":
    unittest.main()
