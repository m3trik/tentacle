#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.hud, the one HUD Slots class.

It reaches its host only through ``self.tk`` (``EnvUtils.scene_status``,
``NodeUtils.selection_summary``): a fake toolkit stands in for it here (plain
pytest), and in Maya the same class reads the real ``mtk``.

Bug: warnings (e.g. autosave-off, default-framerate) fired on brand-new
untitled scenes during initial setup, creating noise. Warnings are skipped
when chk_warn_skip_unsaved is enabled (default) AND the scene was never saved.

Bug: the "Prev Command" line printed the slot's *entire* docstring -- a slot
with a ``Parameters:`` block dumped a wall of text into the HUD (and an
undocumented slot printed "None"). It is now the summary line only, capped at
``PREV_COMMAND_MAX_CHARS``.

Bug: the HUD text view was persisted like an input (``restore_state``).
"""

import os
import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.hud import HudSlots


def _status(**overrides):
    """A ``scene_status`` answer: a saved, unremarkable scene."""
    status = dict(
        symmetry=None,
        xform_constraint=None,
        workspace=None,
        units="centimeter",
        fps=24.0,
        time_unit="film",
        default_fps=False,
        autosave=True,
        autosave_scene=False,
        saved=True,
    )
    status.update(overrides)
    return status


class _FakeHud:
    """Collects the paragraphs a hud TextEdit would have appended."""

    def __init__(self):
        self.lines = []

    def insertText(self, text, **kwargs):
        self.lines.append(text)

    def joined(self):
        return "\n".join(self.lines)


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        with mock.patch.object(HudSlots, "_start_version_check"):
            self.slots = HudSlots(self.sb)
        self.slots._versions = mock.MagicMock(new_version_available=False)
        self.tk = self.sb.tk
        self.tk.EnvUtils.scene_status.return_value = _status()
        self.prefs = self.sb.loaded_ui.preferences
        self._opt_in(
            chk_warn_framerate=False,
            chk_warn_autosave_off=False,
            chk_warn_autosave_open=False,
            chk_warn_skip_unsaved=True,
        )

    def _opt_in(self, **flags):
        for name, state in flags.items():
            getattr(self.prefs, name).isChecked.return_value = state

    def _keys(self):
        return [w["key"] for w in self.slots.evaluate_warnings()]


class TestWarningGates(_SlotsCase):
    def test_a_warning_fires_only_when_opted_into(self):
        self.tk.EnvUtils.scene_status.return_value = _status(autosave=False)
        self.assertEqual(self._keys(), [])
        self._opt_in(chk_warn_autosave_off=True)
        self.assertEqual(self._keys(), ["chk_warn_autosave_off"])

    def test_nothing_opted_into_reads_no_status(self):
        self.assertEqual(self._keys(), [])
        self.tk.EnvUtils.scene_status.assert_not_called()

    def test_an_unsaved_scene_is_skipped_when_asked(self):
        self._opt_in(chk_warn_autosave_off=True)
        self.tk.EnvUtils.scene_status.return_value = _status(
            autosave=False, saved=False
        )
        self.assertEqual(self._keys(), [])
        self._opt_in(chk_warn_skip_unsaved=False)
        self.assertEqual(self._keys(), ["chk_warn_autosave_off"])

    def test_missing_prefs_means_disabled(self):
        self.sb.loaded_ui = type("Ui", (), {})()  # no preferences UI at all
        self.assertEqual(self.slots.evaluate_warnings(), [])

    def test_a_failing_status_never_breaks_the_hud(self):
        self._opt_in(chk_warn_autosave_off=True)
        self.tk.EnvUtils.scene_status.side_effect = RuntimeError("no scene")
        self.assertEqual(self.slots.evaluate_warnings(), [])


class TestWarningChecks(_SlotsCase):
    def setUp(self):
        super().setUp()
        self._opt_in(
            chk_warn_framerate=True,
            chk_warn_autosave_off=True,
            chk_warn_autosave_open=True,
        )

    def test_each_check_reads_its_fact(self):
        for fact, key in (
            ({"default_fps": True}, "chk_warn_framerate"),
            ({"autosave": False}, "chk_warn_autosave_off"),
            ({"autosave_scene": True}, "chk_warn_autosave_open"),
        ):
            with self.subTest(key=key):
                self.tk.EnvUtils.scene_status.return_value = _status(**fact)
                self.assertEqual(self._keys(), [key])

    def test_the_framerate_detail_names_the_rate(self):
        self.tk.EnvUtils.scene_status.return_value = _status(default_fps=True)
        (warning,) = self.slots.evaluate_warnings()
        self.assertIn("24 fps FILM", warning["detail"])
        self.tk.EnvUtils.scene_status.return_value = _status(
            default_fps=True, fps=23.976023976, time_unit=None
        )
        (warning,) = self.slots.evaluate_warnings()
        self.assertIn("23.976 fps<", warning["detail"])

    def test_icons_then_details(self):
        self.tk.EnvUtils.scene_status.return_value = _status(autosave=False)
        warnings = self.slots.evaluate_warnings()
        hud = _FakeHud()
        self.slots.insert_warning_icons(hud, warnings)
        self.slots.insert_warning_details(hud, warnings)
        self.assertEqual(len(hud.lines), 2)
        self.assertIn("Autosave", hud.lines[0])
        self.assertIn("DISABLED", hud.lines[1])


class TestHudBuild(_SlotsCase):
    def _build(self, summary):
        self.tk.NodeUtils.selection_summary.return_value = summary
        self.sb.prev_slot = None
        hud = _FakeHud()
        self.sb.loaded_ui.hud_startmenu.hudTextEdit = hud
        self.slots.ui = self.sb.loaded_ui.hud_startmenu
        self.slots.construct_hud()
        return hud

    def test_nothing_selected_shows_the_scene(self):
        self.tk.EnvUtils.scene_status.return_value = _status(
            symmetry="X", xform_constraint="surface", workspace="proj"
        )
        self.slots._versions.new_version_available = True
        self.slots._versions.latest_ver = "9.9.9"
        text = self._build(None).joined()
        for words in (
            "9.9.9",
            "Symmetry Axis",
            ">X<",
            "surface",
            "proj",
            "Units",
            "centimeter",
            "24 fps FILM",
        ):
            self.assertIn(words, text)

    def test_a_host_without_a_fact_shows_no_line(self):
        self.tk.EnvUtils.scene_status.return_value = _status(
            units="metric meters", time_unit=None
        )
        text = self._build(None).joined()
        self.assertNotIn("Symmetry", text)
        self.assertNotIn("Xform Constraint", text)
        self.assertNotIn("Workspace", text)
        self.assertIn("24 fps<", text)

    def test_selected_objects(self):
        text = self._build(
            dict(
                mode="object",
                count=1,
                objects=[("cube", "mesh")],
                instances=3,
                normals_locked=True,
                faces=6,
                tris=12,
                uvs=None,
            )
        ).joined()
        for words in (
            "Selected:",
            "cube",
            ":mesh",
            "LOCKED",
            "Instances",
            "Faces",
            "Tris",
        ):
            self.assertIn(words, text)
        self.assertNotIn("UVs", text)
        self.tk.NodeUtils.selection_summary.assert_called_once_with(
            limit=HudSlots.LIST_LIMIT
        )

    def test_a_lone_object_is_no_instance(self):
        text = self._build(
            dict(
                mode="object",
                count=1,
                objects=[],
                instances=1,
                normals_locked=False,
                faces=None,
                tris=None,
                uvs=None,
            )
        ).joined()
        self.assertNotIn("Instances", text)
        self.assertNotIn("LOCKED", text)

    def test_components(self):
        text = self._build(
            dict(mode="component", component="Verts", selected=3, total=8)
        ).joined()
        self.assertIn("Selected Verts", text)
        self.assertIn(">3 <", text)
        self.assertIn("/8", text)


class TestVersionCheck(_SlotsCase):
    def test_runs_against_the_pip_capable_python(self):
        self.sb.OptionalPackageManager.pip_python.return_value = "mayapy"
        self.slots._start_version_check()
        self.slots._versions.start_version_check.assert_called_once_with(
            package_name="tentacletk", python_path="mayapy"
        )

    def test_no_such_python_no_check(self):
        """The host binary itself would hang on pip."""
        self.sb.OptionalPackageManager.pip_python.return_value = None
        self.slots._start_version_check()
        self.slots._versions.start_version_check.assert_not_called()


class TestPrevCommandLine(_SlotsCase):
    """``insert_prev_command`` shows one capped summary line, never a full docstring."""

    @staticmethod
    def _slot(doc):
        def slot():
            pass

        slot.__doc__ = doc
        return slot

    def test_long_docstring_is_capped(self):
        cap = HudSlots.PREV_COMMAND_MAX_CHARS
        summary = "x" * (cap * 2)
        hud = _FakeHud()
        self.slots.insert_prev_command(hud, self._slot(summary))
        line = hud.lines[0]
        self.assertNotIn(summary, line)
        self.assertIn("x" * cap, line)
        # truncate() appends its ".." marker past the cap; nothing more.
        self.assertLessEqual(
            len(line.split('Yellow;">')[1].split("</font>")[0]), cap + 2
        )

    def test_only_the_summary_line_is_shown(self):
        hud = _FakeHud()
        doc = "Do The Thing: act on the selection.\n\n    Parameters:\n        x (int): nope."
        self.slots.insert_prev_command(hud, self._slot(doc))
        self.assertIn("Do The Thing: act on the selection.", hud.lines[0])
        self.assertNotIn("Parameters:", hud.lines[0])

    def test_undocumented_slot_falls_back_to_its_name(self):
        hud = _FakeHud()
        self.slots.insert_prev_command(hud, self._slot(None))
        self.assertIn("slot", hud.lines[0])
        self.assertNotIn("None", hud.lines[0])

    def test_no_prev_slot_inserts_nothing(self):
        hud = _FakeHud()
        self.slots.insert_prev_command(hud, None)
        self.assertEqual(hud.lines, [])


class TestHudDisplayIsNotPersisted(_SlotsCase):
    """The HUD text is composed afresh on every show -- never a persisted value.

    Regression: registration defaults every widget to ``restore_state=True``, so
    the read-only ``hudTextEdit`` was persisted like an input. Its hide-time
    ``clear()`` -- and every line the delayed build appends -- wrote the whole
    HUD to the settings store and flushed it, on every gesture, and the
    previous session's HUD text was restored into it at load.
    """

    def test_the_hud_text_edit_opts_out_of_state_persistence(self):
        widget = type("Widget", (), {"restore_state": True})()
        self.slots.hudTextEdit_init(widget)
        self.assertIs(widget.restore_state, False)

    def test_the_skip_unsaved_preference_ships_checked(self):
        """The .ui must ship chk_warn_skip_unsaved checked by default."""
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tentacle",
            "ui",
            "preferences.ui",
        )
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()
        idx = content.find('name="chk_warn_skip_unsaved"')
        self.assertNotEqual(
            idx, -1, "chk_warn_skip_unsaved missing from preferences.ui"
        )
        block = content[idx : content.find("</widget>", idx)]
        self.assertIn(
            "<bool>true</bool>", block, "chk_warn_skip_unsaved must default to checked"
        )


@unittest.skipUnless(MAYA_AVAILABLE, "reads the real mtk; runs in a fresh Maya")
class TestHudInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")
        self.sb.prev_slot = None

    def tearDown(self):
        self.cmds.file(new=True, force=True)

    def _build(self):
        hud = _FakeHud()
        self.sb.loaded_ui.hud_startmenu.hudTextEdit = hud
        self.slots.ui = self.sb.loaded_ui.hud_startmenu
        self.slots.construct_hud()
        return hud.joined()

    def test_an_empty_selection_shows_the_scene(self):
        text = self._build()
        self.assertIn("Units", text)
        self.assertIn("fps", text)

    def test_a_selected_cube(self):
        self.cmds.select(self.cmds.polyCube(name="hud_cube")[0])
        text = self._build()
        self.assertIn("hud_cube", text)
        self.assertIn("Faces: <font", text)
        self.assertIn(">6", text)

    def test_an_untitled_scene_skips_the_warnings(self):
        self._opt_in(chk_warn_framerate=True, chk_warn_autosave_off=True)
        self.assertEqual(self.slots.evaluate_warnings(), [])


if __name__ == "__main__":
    unittest.main()
