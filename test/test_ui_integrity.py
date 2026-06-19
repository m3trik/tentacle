#!/usr/bin/python
# coding=utf-8
"""Tests for UI file structure and slot↔UI coverage.

Validates:
- Every .ui file in ui/ has a matching _ui.py (and vice versa)
- Key binding targets in TclMaya reference real UI files
- Slot modules have at least one corresponding UI file
"""
import ast
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
    """Tcl default bindings (both DCCs) must point to real UI files."""

    def _get_binding_targets(self, tcl_filename="tcl_maya.py"):
        """Parse a tcl_*.py and extract binding values (UI references)."""
        tcl_path = PKG / tcl_filename
        source = tcl_path.read_text(encoding="utf-8")
        # Bindings are string values like "hud#startmenu", "cameras#startmenu", etc.
        targets = []
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for val in node.values:
                    if isinstance(val, ast.Constant) and isinstance(val.value, str):
                        if "#" in val.value:
                            targets.append(val.value)
                    elif isinstance(val, ast.JoinedStr):
                        # f-string — skip dynamic parts, just grab the literal suffix
                        for part in val.values:
                            if isinstance(part, ast.Constant) and "#" in str(
                                part.value
                            ):
                                targets.append(part.value.lstrip("|"))
        return targets

    def test_maya_binding_ui_files_exist(self):
        """Each TclMaya binding target (e.g. 'hud#startmenu') must have a .ui file."""
        targets = self._get_binding_targets("tcl_maya.py")
        self.assertGreater(len(targets), 0, "Could not extract any TclMaya binding targets")

        all_ui = _ui_files(UI_DIR) | _ui_files(UI_MAYA_DIR)
        missing = [t for t in targets if t not in all_ui]
        self.assertEqual(missing, [], f"TclMaya binding targets without .ui: {missing}")

    def test_blender_binding_ui_files_exist(self):
        """Each TclBlender binding target (incl. the both-button 'blender#startmenu') must
        resolve to a .ui in ui/ or ui/blender_menus/ — so no chord can dead-end."""
        targets = self._get_binding_targets("tcl_blender.py")
        self.assertGreater(len(targets), 0, "Could not extract any TclBlender binding targets")

        all_ui = _ui_files(UI_DIR) | _ui_files(UI_BLENDER_DIR)
        missing = [t for t in targets if t not in all_ui]
        self.assertEqual(missing, [], f"TclBlender binding targets without .ui: {missing}")


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


if __name__ == "__main__":
    unittest.main()
