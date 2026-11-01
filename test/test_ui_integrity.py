#!/usr/bin/python
# coding=utf-8
"""Tests for UI file structure and slot↔UI coverage.

Validates:
- Every .ui file in ui/ has a matching _ui.py (and vice versa)
- Key binding targets in each host's chord table reference real UI files
- Slot modules have at least one corresponding UI file
"""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "tentacle"
UI_DIR = PKG / "ui"
UI_MAYA_DIR = UI_DIR / "maya_menus"
UI_BLENDER_DIR = UI_DIR / "blender_menus"
SLOTS_DIR = PKG / "slots" / "maya"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _ui_files(directory: Path):
    """Return set of stem names for .ui files (excluding __init__, __pycache__)."""
    return {f.stem for f in directory.glob("*.ui")}


def _generated_py(directory: Path):
    """Return set of stem names for generated _ui.py files."""
    return {f.stem.removesuffix("_ui") for f in directory.glob("*_ui.py")}


class TestUiFilePairing(unittest.TestCase):
    """Every .ui must have a _ui.py and vice versa."""

    def test_ui_dir_exists(self):
        self.assertTrue(UI_DIR.is_dir())

    def test_maya_menus_dir_exists(self):
        self.assertTrue(UI_MAYA_DIR.is_dir())

    def test_main_ui_pairing(self):
        """Each .ui in ui/ must have a corresponding _ui.py."""
        ui_stems = _ui_files(UI_DIR)
        py_stems = _generated_py(UI_DIR)
        missing_py = ui_stems - py_stems
        self.assertEqual(
            missing_py,
            set(),
            f".ui without _ui.py in ui/: {sorted(missing_py)}",
        )

    def test_main_py_has_ui(self):
        """Each _ui.py in ui/ must have a corresponding .ui."""
        ui_stems = _ui_files(UI_DIR)
        py_stems = _generated_py(UI_DIR)
        orphan_py = py_stems - ui_stems
        self.assertEqual(
            orphan_py,
            set(),
            f"_ui.py without .ui in ui/: {sorted(orphan_py)}",
        )

    def test_maya_menus_pairing(self):
        """Each .ui in ui/maya_menus/ must have a corresponding _ui.py."""
        ui_stems = _ui_files(UI_MAYA_DIR)
        py_stems = _generated_py(UI_MAYA_DIR)
        missing_py = ui_stems - py_stems
        self.assertEqual(
            missing_py,
            set(),
            f".ui without _ui.py in maya_menus/: {sorted(missing_py)}",
        )

    def test_maya_menus_py_has_ui(self):
        """Each _ui.py in ui/maya_menus/ must have a corresponding .ui."""
        ui_stems = _ui_files(UI_MAYA_DIR)
        py_stems = _generated_py(UI_MAYA_DIR)
        orphan_py = py_stems - ui_stems
        self.assertEqual(
            orphan_py,
            set(),
            f"_ui.py without .ui in maya_menus/: {sorted(orphan_py)}",
        )

    def test_blender_menus_dir_exists(self):
        self.assertTrue(UI_BLENDER_DIR.is_dir())

    def test_blender_menus_pairing(self):
        """Each .ui in ui/blender_menus/ must have a corresponding _ui.py."""
        ui_stems = _ui_files(UI_BLENDER_DIR)
        py_stems = _generated_py(UI_BLENDER_DIR)
        missing_py = ui_stems - py_stems
        self.assertEqual(
            missing_py,
            set(),
            f".ui without _ui.py in blender_menus/: {sorted(missing_py)}",
        )

    def test_blender_menus_py_has_ui(self):
        """Each _ui.py in ui/blender_menus/ must have a corresponding .ui."""
        ui_stems = _ui_files(UI_BLENDER_DIR)
        py_stems = _generated_py(UI_BLENDER_DIR)
        orphan_py = py_stems - ui_stems
        self.assertEqual(
            orphan_py,
            set(),
            f"_ui.py without .ui in blender_menus/: {sorted(orphan_py)}",
        )


class TestBindingTargetsResolve(unittest.TestCase):
    """Default binding targets (both DCCs) must point to real UI files — no chord may dead-end.

    Targets come from two places since the chord table was shared: the four common entries are
    built by ``Tcl.chord_bindings`` (read from the live function — it is DCC-free, so this is the
    real runtime value rather than scraped source), and the both-button target is supplied by each
    fork at its call site, which is read from that fork's source (constructing one needs its DCC).
    """

    @staticmethod
    def _host_targets(host):
        """Every target of *host*'s chord table, as ``Tcl.build`` makes it: the shared chords
        plus the both-button chord's ``<host>#startmenu``."""
        from tentacle.tcl import Tcl

        return list(Tcl.chord_bindings(None, f"{host}#startmenu").values())

    def _assert_all_resolve(self, targets, all_ui, label):
        self.assertGreater(len(targets), 0, f"Could not extract any {label} binding targets")
        missing = sorted({t for t in targets if t not in all_ui})
        self.assertEqual(missing, [], f"{label} binding targets without .ui: {missing}")

    def test_shared_chord_table_targets_exist(self):
        """The common chords every DCC gets must resolve in ui/."""
        from tentacle.tcl import Tcl

        self._assert_all_resolve(
            list(Tcl.chord_bindings().values()), _ui_files(UI_DIR), "shared chord table"
        )

    def test_maya_binding_ui_files_exist(self):
        """Each Maya binding target (e.g. 'hud#startmenu', the both-button 'maya#startmenu')
        must have a .ui in ui/ or ui/maya_menus/."""
        self._assert_all_resolve(
            self._host_targets("maya"),
            _ui_files(UI_DIR) | _ui_files(UI_MAYA_DIR),
            "maya",
        )

    def test_blender_binding_ui_files_exist(self):
        """Each Blender binding target (incl. the both-button 'blender#startmenu') must
        resolve to a .ui in ui/ or ui/blender_menus/ — so no chord can dead-end."""
        self._assert_all_resolve(
            self._host_targets("blender"),
            _ui_files(UI_DIR) | _ui_files(UI_BLENDER_DIR),
            "blender",
        )

    def test_every_host_has_its_native_menu_pages(self):
        """``Tcl.build`` registers ``ui/<host>_menus`` by convention: each host has one."""
        from tentacle.tcl import Tcl

        for host in Tcl.HOSTS:
            with self.subTest(host=host):
                self.assertTrue((UI_DIR / f"{host}_menus").is_dir())


class TestSlotUiCoverage(unittest.TestCase):
    """Spot-check that major slot modules have at least one UI file."""

    # These slot files should definitely have a UI counterpart
    EXPECTED_PAIRS = [
        "animation",
        "cameras",
        "display",
        "edit",
        "lighting",
        "materials",
        "normals",
        "nurbs",
        "pivot",
        "polygons",
        "preferences",
        "rendering",
        "rigging",
        "scene",
        "selection",
        "settings",
        "subdivision",
        "symmetry",
        "transform",
        "utilities",
        "uv",
    ]

    def test_slot_has_ui(self):
        """Each major slot module should have at least one .ui file."""
        all_ui_stems = set()
        for f in UI_DIR.glob("*.ui"):
            # "animation#submenu.ui" -> base name "animation"
            all_ui_stems.add(f.stem.split("#")[0])
        for f in UI_MAYA_DIR.glob("*.ui"):
            all_ui_stems.add(f.stem.split("#")[0])

        missing = [name for name in self.EXPECTED_PAIRS if name not in all_ui_stems]
        self.assertEqual(missing, [], f"Slots without any UI file: {missing}")


class TestMenuButtonTargets(unittest.TestCase):
    """Every promoted MenuButton must carry a non-empty ``target``.

    The marking menu's hover (``child_enterEvent``) and breadcrumb-clone paths
    navigate via ``accessibleName``, which MenuButton derives from ``target``.
    A target-less nav button therefore yields an empty accessibleName and
    silently breaks navigation — the exact regression this guards against.
    Qt-free (pure XML) so it runs in the structural CI suite.
    """

    def _scan(self, directory: Path):
        """Return (inspected_count, offenders) for MenuButtons in *directory*."""
        inspected, offenders = 0, []
        for f in directory.glob("*.ui"):
            root = ET.parse(f).getroot()
            for w in root.iter("widget"):
                if w.get("class") != "MenuButton":
                    continue
                inspected += 1
                target = ""
                for prop in w.findall("property"):
                    if prop.get("name") == "target":
                        s = prop.find("string")
                        target = (s.text or "") if s is not None else ""
                if not target.strip():
                    offenders.append(f"{f.name}:{w.get('name')}")
        return inspected, offenders

    def test_menubuttons_have_target(self):
        n1, off1 = self._scan(UI_DIR)
        n2, off2 = self._scan(UI_MAYA_DIR)
        offenders = off1 + off2
        self.assertEqual(
            offenders, [], f"MenuButton(s) with empty/missing target: {offenders}"
        )
        # Guard against a vacuous pass (parsing finding zero MenuButtons).
        self.assertGreater(n1 + n2, 0, "No MenuButton widgets found to validate")


class TestNoShadowedObjectNames(unittest.TestCase):
    """No widget objectName may shadow a callable attribute on uitk's MainWindow.

    ``MainWindow.register_widget`` binds each child widget as an attribute keyed by
    its objectName, but refuses (with a HUD warning) any name that collides with a
    callable already on the class — e.g. a group named ``create`` shadows
    ``QWidget.create()``. The widget is then unreachable via ``sb.<name>`` and
    silently degrades. This guards every .ui against that whole collision class,
    replicating the exact runtime check
    (mainWindow.py: ``callable(getattr(type(self), name, None))``).
    """

    def _object_names(self, directory: Path):
        """(file, objectName) for every ``<widget>`` under *directory*, recursively."""
        names = []
        for f in directory.rglob("*.ui"):
            for w in ET.parse(f).getroot().iter("widget"):
                name = w.get("name")
                if name:
                    names.append((f.name, name))
        return names

    def test_no_objectname_shadows_mainwindow(self):
        try:
            from uitk.widgets.mainWindow import MainWindow
        except ImportError as e:  # Qt/uitk absent (e.g. minimal env) — nothing to check
            self.skipTest(f"uitk/PySide unavailable: {e}")

        names = self._object_names(UI_DIR)
        # Guard against a vacuous pass (parsing finding zero widgets).
        self.assertGreater(len(names), 0, "No widget objectNames found to validate")

        offenders = sorted(
            {
                f"{fname}:{name}"
                for fname, name in names
                if callable(getattr(MainWindow, name, None))
            }
        )
        self.assertEqual(
            offenders,
            [],
            "objectName(s) shadow a MainWindow callable and won't bind as attributes "
            f"— rename them: {offenders}",
        )


class TestCustomWidgetsAreDeclared(unittest.TestCase):
    """A widget class a ``.ui`` uses is Qt's own or declared in that file's
    ``<customwidgets>``. uitk's runtime loader silently drops an undeclared
    class -- the widget never exists -- while the compiled path tolerates it, so
    the panel works in one launch and not the other (2026-10-31: the Naming
    panel's new Scope combo, a ``ComboBox`` the file never declared)."""

    def test_every_widget_class_is_qt_or_declared(self):
        try:
            from qtpy import QtWidgets
        except Exception as e:  # Qt absent: nothing to resolve the Qt classes
            self.skipTest(f"Qt unavailable: {e}")
        offenders, checked = [], 0
        for path in sorted(UI_DIR.rglob("*.ui")):
            root = ET.parse(path).getroot()
            declared = {c.findtext("class") for c in root.iter("customwidget")}
            for widget in root.iter("widget"):
                cls = widget.get("class")
                checked += 1
                if cls in declared or hasattr(QtWidgets, cls):
                    continue
                offenders.append(f"{path.relative_to(UI_DIR)}:{widget.get('name')} ({cls})")
        self.assertGreater(checked, 0, "no widget parsed")
        self.assertEqual(
            offenders, [], f"undeclared custom widget class(es): {offenders}"
        )


class TestFixedSpacersAreGapsNotDeadSpace(unittest.TestCase):
    """A `Fixed` vertical spacer's sizeHint is its EXACT height — it can
    neither grow nor shrink. Qt Designer stamps 20x40 on every new spacer,
    so an untuned default becomes 40px of permanent dead space above the
    footer that the user cannot resize away (live report: the materials
    panel). The panels use a deliberate ~10px gap; pin that.
    """

    MAX_GAP = 12

    def test_no_oversized_fixed_vertical_spacer(self):
        offenders = []
        # Recursive: the rule is about the spacer declaration itself, so it
        # holds for the menu subdirectories too, not just the main panels.
        for path in sorted(UI_DIR.rglob("*.ui")):
            for spacer in ET.parse(path).iter("spacer"):
                # Default to "" not None: a spacer may omit either property
                # (sizeType defaults to Expanding), and None.endswith raises.
                orientation = size_type = ""
                height = None
                for prop in spacer.findall("property"):
                    name = prop.get("name")
                    if name == "orientation":
                        orientation = prop.findtext("enum") or ""
                    elif name == "sizeType":
                        size_type = prop.findtext("enum") or ""
                    elif name == "sizeHint":
                        size = prop.find("size")
                        if size is not None:
                            height = int(size.findtext("height") or 0)
                if (
                    orientation.endswith("Vertical")
                    and size_type.endswith("Fixed")
                    and height is not None
                    and height > self.MAX_GAP
                ):
                    offenders.append(f"{path.name}:{spacer.get('name')}={height}px")
        self.assertEqual(
            offenders,
            [],
            "Fixed vertical spacer(s) taller than "
            f"{self.MAX_GAP}px are unresizable dead space above the footer "
            f"(Qt Designer's untuned 20x40 default): {offenders}",
        )


if __name__ == "__main__":
    unittest.main()
