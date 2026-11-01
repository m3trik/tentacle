#!/usr/bin/python
# coding=utf-8
"""The Light Rigs panel's Slots class (``slots/tools/light_rig.py``).

It reaches its host only through ``self.tk``, so a fake toolkit stands in for
``mtk`` and records what the panel asks of its ``LightRig``: plain unittest, no
DCC, no widgets. A Maya tool for now (``tentacle.slots.tools.HOSTS``): in Maya
the same class drives the real ``mtk.LightRig`` on a scratch library (never the
user's). The engine's own behavior is mayatk's ``test_light_rig.py``.
"""

import os
import unittest
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools import HOSTS
from tentacle.slots.tools.light_rig import LightRigSlots


class _Form:
    """A FormPanel stand-in: accepted (or dismissed), with the values a user typed."""

    def __init__(self, values, accepted=True):
        self._values, self._accepted = values, accepted
        self.deleted = False

    def exec_panel(self):
        return self._accepted

    def values(self):
        return dict(self._values)

    def deleteLater(self):
        self.deleted = True


def _fake_tk(names=("A", "B"), info=None, scene=()):
    """A toolkit double whose ``LightRig`` holds *names* (each with *info*, a
    user rig) and has *scene* (``[(group, rig)]``) in the scene."""
    info = info or {}
    tk = mock.MagicMock()
    engine = tk.LightRig.return_value
    engine.group = "LIGHT_RIG"
    engine.names.return_value = list(names)
    engine.scene_rigs.return_value = list(scene)
    engine.applied.return_value = (None, False)
    engine.can_swap_back.return_value = False
    engine.store.source.return_value = "user"
    engine.store.info.side_effect = lambda name: dict(info.get(name, {}))
    engine.store.exists.return_value = False
    return tk


def _panel(tk=None):
    """A ``LightRigSlots`` over a mock ui and *tk* (a fake by default), handed
    over before the panel is built, as ``Slots.tk`` is."""
    sb = mock.MagicMock()
    sb.tk = tk if tk is not None else _fake_tk()
    cmb = sb.loaded_ui.light_rig.cmb000
    cmb.currentData.return_value = None
    cmb.findData.return_value = 0
    cmb.count.return_value = 2
    return LightRigSlots(sb), sb


def _footer(sb):
    """``(text, level)`` of the footer's last message."""
    call = sb.loaded_ui.light_rig.footer.setText.call_args
    return call.args[0], call.kwargs.get("level")


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestLightRigPanelSetup(_PanelCase):
    def test_a_maya_tool_until_blendertk_has_the_engine(self):
        self.assertEqual(HOSTS["light_rig"], ("maya",))

    def test_follows_scene_opens_through_the_host_jobs(self):
        slots, sb = _panel()
        jobs = sb.tk.ScriptJobManager.instance.return_value
        events = [c.args[0] for c in jobs.subscribe.call_args_list]
        self.assertEqual(events, ["SceneOpened", "NewSceneOpened"])
        for c in jobs.subscribe.call_args_list:
            self.assertEqual(c.args[1], slots.refresh)
            self.assertIs(c.kwargs["owner"], slots)
        jobs.connect_cleanup.assert_called_once_with(sb.loaded_ui.light_rig, owner=slots)

    def test_an_event_the_host_lacks_does_not_block_the_open(self):
        tk = _fake_tk()
        tk.ScriptJobManager.instance.return_value.subscribe.side_effect = KeyError("x")
        slots, _sb = _panel(tk)
        self.assertIs(slots.engine, tk.LightRig.return_value)

    def test_the_first_refresh_waits_for_the_widgets(self):
        slots, sb = _panel()
        sb.QtCore.QTimer.singleShot.assert_called_once_with(0, slots.refresh)
        slots.engine.names.assert_not_called()

    def test_the_header_offers_the_rig_folder_and_the_reference(self):
        slots, _sb = _panel()
        header = mock.MagicMock()
        slots.header_init(header)
        header.config_buttons.assert_called_once_with("refresh", "menu", "collapse", "hide")
        header.refresh_requested.connect.assert_called_once_with(slots.refresh)
        names = [c.kwargs.get("setObjectName") for c in header.menu.add.call_args_list]
        self.assertEqual(names, ["open_rig_folder"])
        self.assertEqual(header.set_help_text.call_args.kwargs["url"], LightRigSlots.HELP_URL)

    def test_open_rig_folder_opens_the_library(self):
        slots, _sb = _panel()
        slots.engine.store.user_dir = "/rigs"
        with mock.patch.object(ptk.FileUtils, "open_explorer") as opener:
            slots.open_rig_folder()
        opener.assert_called_once_with("/rigs", create_dir=True, logger=slots.logger)


class TestLightRigPanelRefresh(_PanelCase):
    def test_lists_the_library_with_each_rigs_note(self):
        tk = _fake_tk(info={"A": {"lights": 3, "read_only": True}, "B": {"description": "warm"}})
        slots, sb = _panel(tk)
        slots.refresh()
        cmb = sb.loaded_ui.light_rig.cmb000
        rows = [c.args for c in cmb.add_cells.call_args_list]
        self.assertEqual(
            rows,
            [
                ({"name": "A", "lights": "3", "note": "locked"}, "A"),
                ({"name": "B", "lights": "", "note": ""}, "B"),
            ],
        )
        self.assertFalse(cmb.restore_state)
        sb.loaded_ui.light_rig.b001.setEnabled.assert_called_with(False)
        self.assertEqual(
            _footer(sb), ("No rig in the scene: ＋ saves the lights under a group as one.", "info")
        )

    def test_a_shipped_rig_shows_no_user_info(self):
        tk = _fake_tk(names=("A",), info={"A": {"lights": 3}})
        tk.LightRig.return_value.store.source.return_value = "builtin"
        slots, sb = _panel(tk)
        slots.refresh()
        row = sb.loaded_ui.light_rig.cmb000.add_cells.call_args.args[0]
        self.assertEqual(row, {"name": "A", "lights": "", "note": ""})

    def test_reports_the_scene_rig_and_flags_an_edit(self):
        tk = _fake_tk(scene=[("RIG", "A")])
        tk.LightRig.return_value.applied.return_value = ("A", True)
        slots, sb = _panel(tk)
        slots.refresh()
        self.assertEqual(_footer(sb), ("Scene: A (edited) in RIG", "warning"))

    def test_picking_a_rig_shows_it_without_touching_the_scene(self):
        tk = _fake_tk(info={"B": {"lights": 2, "group": "RIG", "description": "warm"}})
        slots, sb = _panel(tk)
        combo = mock.MagicMock()
        combo.currentData.return_value = "B"
        slots.cmb000(1, combo)
        sb.loaded_ui.light_rig.footer.setText.assert_called_with("B: 2 lights in RIG — warm")
        slots.engine.apply.assert_not_called()


class TestLightRigPanelVerbs(_PanelCase):
    def _picked(self, name, tk=None):
        slots, sb = _panel(tk)
        sb.loaded_ui.light_rig.cmb000.currentData.return_value = name
        return slots, sb

    def test_apply_puts_the_pick_in_the_scene(self):
        slots, sb = self._picked("B")
        slots.engine.apply.return_value = {
            "name": "B", "group": "RIG", "lights": ["L1", "L2"], "skipped": [], "disconnected": []
        }
        slots.b000()
        slots.engine.apply.assert_called_once_with("B")
        self.assertEqual(_footer(sb), ("Applied B: 2 lights in RIG.", "success"))

    def test_apply_reports_the_plugs_it_took_over(self):
        slots, sb = self._picked("B")
        slots.engine.apply.return_value = {
            "name": "B", "group": "RIG", "lights": [], "skipped": ["lamp locked"],
            "disconnected": ["lamp.intensity"],
        }
        slots.b000()
        text, level = _footer(sb)
        self.assertEqual(level, "warning")
        self.assertIn("1 driven plug(s) taken over", text)
        self.assertIn("1 override(s) left alone", text)

    def test_apply_without_a_pick_asks_for_one(self):
        slots, sb = self._picked(None)
        slots.b000()
        slots.engine.apply.assert_not_called()
        self.assertEqual(_footer(sb), ("Pick a rig to apply.", "warning"))

    def test_an_unreadable_rig_is_reported(self):
        slots, sb = self._picked("A")
        slots.engine.apply.side_effect = ValueError("payload version 9")
        slots.b000()
        self.assertEqual(_footer(sb), ("Could not apply A: payload version 9", "error"))

    def test_swap_back_with_nothing_to_return_to_says_so(self):
        slots, sb = _panel()
        slots.engine.swap_back.side_effect = LookupError("No rig to swap back to.")
        slots.b001()
        self.assertEqual(_footer(sb), ("No rig to swap back to.", "warning"))

    def test_the_save_form_saves_the_scene_rig(self):
        slots, sb = _panel()
        form = _Form({"name": " N ", "description": "first", "group": "RIG"})
        slots._form = lambda *a, **k: form
        slots.prompt_save()
        slots.engine.save.assert_called_once_with(
            "N", description="first", group="RIG", force=False
        )
        self.assertTrue(form.deleted)
        self.assertEqual(_footer(sb), ("Saved N.", "success"))

    def test_a_dismissed_form_saves_nothing(self):
        slots, _sb = _panel()
        form = _Form({}, accepted=False)
        slots._form = lambda *a, **k: form
        slots.prompt_save()
        slots.engine.save.assert_not_called()
        self.assertTrue(form.deleted)

    def test_replacing_a_rig_asks_first(self):
        slots, _sb = _panel()
        slots.engine.store.exists.return_value = True
        slots._form = lambda *a, **k: _Form({"name": "A", "description": "", "group": ""})
        slots._ask = mock.MagicMock(return_value=False)
        slots.prompt_save()
        slots._ask.assert_called_once()
        slots.engine.save.assert_not_called()

    def test_a_locked_rig_is_not_saved_over(self):
        slots, sb = _panel()
        slots.engine.save.side_effect = PermissionError("locked")
        slots._form = lambda *a, **k: _Form({"name": "A", "description": "", "group": ""})
        slots.prompt_save()
        text, level = _footer(sb)
        self.assertEqual(level, "error")
        self.assertIn("A is locked", text)

    def test_renaming_in_the_dropdown_renames_the_rig(self):
        slots, sb = _panel()
        sb.loaded_ui.light_rig.cmb000.itemData.return_value = "A"
        slots.engine.rename.return_value = True
        slots._on_cells_edited(0, {"name": " A2 "})
        slots.engine.rename.assert_called_once_with("A", "A2")
        self.assertEqual(slots.engine.names.call_count, 1)  # refreshed
        # The outcome outlives the refresh's own scene report.
        self.assertEqual(_footer(sb), ("Renamed A to A2.", "success"))

    def test_compare_lists_what_applying_would_change(self):
        slots, sb = _panel()
        slots.engine.normalize.return_value = {"group": "RIG"}
        slots.engine.compare.return_value = [f"L{i}: intensity 1 -> 2" for i in range(30)]
        slots._compare("A")
        slots.engine.compare.assert_called_once_with("A", "RIG")
        text = sb.message_box.call_args.args[0]
        self.assertIn("Applying A would change 30 thing(s)", text)
        self.assertIn("(+5 more in the log)", text)

    def test_delete_keeps_a_locked_rig(self):
        """And the outcome outlives the refresh's own scene report."""
        slots, sb = _panel()
        slots._ask = mock.MagicMock(return_value=True)
        slots.engine.delete.return_value = False
        slots._delete("A")
        self.assertEqual(_footer(sb), ("A is locked.", "error"))
        slots.engine.delete.return_value = True
        slots._delete("A")
        self.assertEqual(_footer(sb), ("Deleted A.", "success"))

    def test_lock_writes_the_library_entry(self):
        slots, _sb = _panel()
        slots._lock("A", True)
        slots.engine.store.set_info.assert_called_with("A", read_only=True)
        slots._lock("A", False)
        slots.engine.store.set_info.assert_called_with("A", read_only=None)


@unittest.skipUnless(MAYA_AVAILABLE, "needs a Maya runtime")
class TestLightRigPanelInMaya(_PanelCase):
    """The panel over the real ``mtk.LightRig`` on a scratch library: what
    mayatk's GUI-only ``test_light_rig_panel.py`` covered before the panel moved
    here (the dropdown is the library, Apply and Swap Back act on the pick, the
    footer reports the scene's rig and an edit to it, the picker's verbs)."""

    @classmethod
    def setUpClass(cls):
        cls.cmds = maya_module("maya.cmds")
        cls.mtk = maya_module("mayatk")
        cls.temp = ptk.TempArtifacts("light_rig_panel", policy="scoped")
        cls.root = str(cls.temp.dir_path())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup(force=True)

    def setUp(self):
        super().setUp()
        self.cmds.file(new=True, force=True)
        self.slots, self.sb = _panel(tk=self.mtk)
        self.addCleanup(self.mtk.ScriptJobManager.instance().unsubscribe_all, self.slots)
        self.store = ptk.PresetStore(
            "light_rigs", user_dir=os.path.join(self.root, self._testMethodName)
        )
        self.engine = self.mtk.LightRig(group="TEST_RIG", store=self.store)
        self.slots.engine = self.engine
        self.slots._ask = lambda *a: True

    def _rig(self, name, intensity):
        """Save a one-light rig *name*, then clear the scene of it."""
        cmds = self.cmds
        tf = cmds.rename(cmds.shadingNode("pointLight", asLight=True), "L_KEY")
        shape = cmds.listRelatives(tf, shapes=True, fullPath=True)[0]
        cmds.setAttr(shape + ".intensity", intensity)
        cmds.group(tf, name="TEST_RIG", world=True)
        self.engine.save(name)
        self.engine.remove()

    def _pick(self, name):
        self.sb.loaded_ui.light_rig.cmb000.currentData.return_value = name

    def _intensity(self):
        return self.cmds.getAttr("|TEST_RIG|L_KEY|L_KEYShape.intensity")

    def test_the_dropdown_lists_the_library_not_the_swap_snapshot(self):
        self._rig("A", 1)
        self._rig("B", 2)
        self.engine.apply("A")
        self.engine.apply("B")  # leaves the swap snapshot in the scene record
        self.slots.refresh()
        cmb = self.sb.loaded_ui.light_rig.cmb000
        self.assertEqual([c.args[1] for c in cmb.add_cells.call_args_list], ["A", "B"])
        self.sb.loaded_ui.light_rig.b001.setEnabled.assert_called_with(True)
        self.assertIn("B", _footer(self.sb)[0])

    def test_apply_puts_the_picked_rig_in_the_scene(self):
        self._rig("A", 1)
        self._rig("B", 2)
        self._pick("B")
        self.slots.b000()
        self.assertEqual(self.engine.applied(), ("B", False))
        self.assertAlmostEqual(self._intensity(), 2)

    def test_swap_back_returns_to_the_replaced_rig(self):
        self._rig("A", 1)
        self._rig("B", 2)
        self._pick("A")
        self.slots.b000()
        self._pick("B")
        self.slots.b000()
        self.slots.b001()
        self.assertEqual(self.engine.applied(), ("A", False))
        self.assertAlmostEqual(self._intensity(), 1)

    def test_the_footer_flags_an_edited_scene_rig(self):
        self._rig("A", 1)
        self.engine.apply("A")
        self.cmds.setAttr("|TEST_RIG|L_KEY|L_KEYShape.intensity", 5)
        self.slots.refresh()
        self.assertIn("(edited)", _footer(self.sb)[0])

    def test_renaming_in_the_dropdown_renames_the_rig(self):
        self._rig("A", 1)
        self.sb.loaded_ui.light_rig.cmb000.itemData.return_value = "A"
        self.slots._on_cells_edited(0, {"name": "A2"})
        self.assertEqual(self.engine.names(), ["A2"])

    def test_a_locked_rig_survives_delete(self):
        self._rig("A", 1)
        self.slots._lock("A", True)
        self.slots._delete("A")
        self.assertTrue(self.store.exists("A"))
        self.slots._lock("A", False)
        self.slots._delete("A")
        self.assertFalse(self.store.exists("A"))

    def test_the_save_form_saves_the_scene_rig(self):
        cmds = self.cmds
        tf = cmds.rename(cmds.shadingNode("pointLight", asLight=True), "L_KEY")
        cmds.group(tf, name="TEST_RIG", world=True)
        self.slots._form = lambda *a, **k: _Form(
            {"name": "N", "description": "first", "group": "TEST_RIG"}
        )
        self.slots.prompt_save()
        self.assertEqual(self.engine.names(), ["N"])
        self.assertEqual(self.store.info("N").get("description"), "first")

    def test_compare_reports_what_applying_would_change(self):
        self._rig("A", 1)
        self.engine.apply("A")
        self.cmds.setAttr("|TEST_RIG|L_KEY|L_KEYShape.intensity", 5)
        self.slots._compare("A")
        text = self.sb.message_box.call_args.args[0]
        self.assertIn("intensity", text)


if __name__ == "__main__":
    unittest.main()
