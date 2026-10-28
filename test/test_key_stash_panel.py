#!/usr/bin/python
# coding=utf-8
"""The Key Stash panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of its store: plain pytest, no DCC, no widgets loaded. The ``.ui``
is read as XML for the layout the panel relies on. In Maya, the same class
drives the real ``mtk`` store end to end. The store's own side (``stash_from``,
``select_clip_objects``, ``watch_undo``) is the libraries': mayatk's and
blendertk's ``test_key_stash.py``.
"""

import os
import types
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.key_stash import KeyStashSlots

KEYS = ((1, 0.0), (10, 5.0), (20, 10.0), (30, 15.0), (40, 20.0))
UI_PATH = os.path.join(os.path.dirname(tentacle.__file__), "ui", "tools", "key_stash.ui")


def _clip(clip_id=7, label="cube 10-30", objects=("|grp|cube",), start=10.0, end=30.0):
    """A stand-in for ``ptk.StashedClip``: what the panel reads off one."""
    return types.SimpleNamespace(
        clip_id=clip_id,
        label=label,
        objects=list(objects),
        start=start,
        end=end,
        created="2026-10-28T10:15:42",
        key_count=3,
        curves=[{"times": [10.0, 20.0, 30.0]}],
    )


def _panel(tk=None, selected=None):
    """A Slots instance over a mock ui and a mock toolkit (or *tk*, handed over
    before the panel is built, as ``Slots.tk`` is), initialized as the deferred
    timer would. *selected* is the clip id the clip list has selected."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        store = sb.tk.KeyStash.active.return_value
        store.clips = []
        store.is_previewing.return_value = False
    ui = sb.loaded_ui.key_stash
    _select(ui, selected)
    ui.cmb001.currentText.return_value = "Original Frames"
    slots = KeyStashSlots(sb)
    slots._initialize_ui()
    return slots, sb, ui


def _select(ui, clip_id):
    """Have the clip list report *clip_id* selected (``None``: nothing)."""
    if clip_id is None:
        ui.tree000.selectedItems.return_value = []
        return None
    item = mock.MagicMock()
    item.data.return_value = clip_id
    ui.tree000.selectedItems.return_value = [item]
    return item


def _footer(ui):
    """The footer's last message and level."""
    call = ui.footer.setText.call_args
    return call.args[0], call.kwargs.get("level")


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        # The class logger is shared: keep the footer's echo off the console.
        patcher = mock.patch.object(KeyStashSlots, "logger", mock.MagicMock())
        patcher.start()
        self.addCleanup(patcher.stop)


class TestKeyStashPanelSetup(_PanelCase):
    def test_setup_waits_for_the_widgets_then_runs_once(self):
        sb = mock.MagicMock()
        slots = KeyStashSlots(sb)
        sb.QtCore.QTimer.singleShot.assert_called_once_with(0, slots._initialize_ui)
        sb.loaded_ui.key_stash.cmb000.add.assert_not_called()
        slots._initialize_ui()
        slots._initialize_ui()
        sb.loaded_ui.key_stash.cmb000.add.assert_called_once()

    def test_the_combos_keep_their_order_and_display_prefixes(self):
        """Both combos save an index, so their order is the saved meaning."""
        slots, sb, ui = _panel()
        self.assertEqual(
            KeyStashSlots.SOURCES,
            (
                ("Selected Keys", "selected_keys"),
                ("Timeline Selection", "timeline_selection"),
                ("Playback Range", "playback_range"),
            ),
        )
        self.assertEqual(KeyStashSlots.RETRIEVE_AT, ("Original Frames", "Current Time"))
        ui.cmb000.add.assert_called_once_with(list(KeyStashSlots.SOURCES))
        ui.cmb001.add.assert_called_once_with(list(KeyStashSlots.RETRIEVE_AT))
        self.assertEqual(ui.cmb000.current_text_prefix, "Source:  ")
        self.assertEqual(ui.cmb001.current_text_prefix, "Retrieve At:  ")

    def test_binds_the_host_store_and_follows_its_undo(self):
        slots, sb, ui = _panel()
        stash = sb.tk.KeyStash
        stash.add_invalidation_listener.assert_called_once_with(
            slots._on_store_invalidated
        )
        stash.watch_undo.assert_called_once_with(owner=slots, widget=ui)
        stash.active.return_value.add_listener.assert_called_once_with(
            slots._on_store_changed
        )
        ui.tree000.itemSelectionChanged.connect.assert_called_once_with(
            slots._sync_buttons
        )
        ui.tree000.itemDoubleClicked.connect.assert_called_once_with(
            slots._select_clip_objects
        )
        ui.footer.setDefaultStatusText.assert_called_with("No stored clips")

    def test_a_new_store_is_rebound_and_the_old_one_released(self):
        slots, sb, ui = _panel()
        old = sb.tk.KeyStash.active.return_value
        new = mock.MagicMock(clips=[])
        sb.tk.KeyStash.active.return_value = new
        self.assertIs(slots.store, new)
        old.remove_listener.assert_called_once_with(slots._on_store_changed)
        new.add_listener.assert_called_once_with(slots._on_store_changed)

    def test_an_invalidated_store_repaints_from_the_next_one(self):
        """A scene change drops the store: the panel binds the next one and
        repaints from it."""
        slots, sb, ui = _panel()
        new = mock.MagicMock(clips=[_clip()])
        new.is_previewing.return_value = False
        sb.tk.KeyStash.active.return_value = new
        ui.tree000.addTopLevelItem.reset_mock()
        slots._on_store_invalidated(None)
        new.add_listener.assert_called_once_with(slots._on_store_changed)
        ui.tree000.addTopLevelItem.assert_called_once()
        ui.footer.setDefaultStatusText.assert_called_with("1 stored clip")

    def test_header_offers_refresh_and_help(self):
        slots, sb, _ = _panel()
        header = mock.MagicMock()
        slots.header_init(header)
        header.config_buttons.assert_called_once_with("refresh", "collapse", "pin")
        header.refresh_requested.connect.assert_called_once_with(
            slots.refresh_from_scene
        )
        self.assertEqual(sb.tooltip.fmt.call_args.kwargs["title"], "Key Stash")
        header.set_help_text.assert_called_once_with(sb.tooltip.fmt.return_value)


class TestKeyStashPanelList(_PanelCase):
    def test_the_list_repaints_from_the_store(self):
        slots, sb, ui = _panel()
        store = sb.tk.KeyStash.active.return_value
        store.clips = [_clip(), _clip(clip_id=8, label="held", start=12.0, end=12.0)]
        store.is_previewing.side_effect = lambda clip_id=None: clip_id == 7
        ui.tree000.addTopLevelItem.reset_mock()
        slots.refresh()
        rows = [c.args[0] for c in ui.tree000.addTopLevelItem.call_args_list]
        self.assertEqual(
            [[row.text(i) for i in range(4)] for row in rows],
            [
                ["cube 10-30  (previewing)", "cube", "10 - 30", "2026-10-28 10:15"],
                ["held", "cube", "12", "2026-10-28 10:15"],
            ],
        )
        ui.footer.setDefaultStatusText.assert_called_with("2 stored clips")

    def test_clip_actions_gate_on_a_selected_clip(self):
        slots, sb, ui = _panel()
        for name in ("b001", "b003", "chk001"):
            getattr(ui, name).setEnabled.assert_called_with(False)
        ui.chk000.setEnabled.assert_called_with(True)
        _select(ui, 7)
        slots._sync_buttons()
        for name in ("b001", "b003", "chk001"):
            getattr(ui, name).setEnabled.assert_called_with(True)

    def test_a_running_preview_locks_in_context_and_shows_checked(self):
        slots, sb, ui = _panel()
        sb.tk.KeyStash.active.return_value.is_previewing.return_value = True
        slots._sync_buttons()
        ui.chk000.setEnabled.assert_called_with(False)
        ui.chk001.setEnabled.assert_called_with(True)  # so it can be ended
        ui.chk001.setChecked.assert_called_with(True)

    def test_header_refresh_prunes_through_the_store(self):
        slots, sb, ui = _panel()
        store = sb.tk.KeyStash.active.return_value
        store.reconcile.return_value = [3]
        slots.refresh_from_scene()
        self.assertEqual(
            _footer(ui),
            ("Pruned 1 clip(s) whose keys are gone from the scene.", "warning"),
        )
        store.reconcile.return_value = []
        slots.refresh_from_scene()
        self.assertIn("in sync", _footer(ui)[0])

    def test_double_click_selects_the_clips_objects_through_the_host(self):
        slots, sb, ui = _panel()
        store = sb.tk.KeyStash.active.return_value
        store.get_clip.return_value = _clip()
        item = mock.MagicMock()
        item.data.return_value = 7
        store.select_clip_objects.return_value = ["|grp|cube"]
        slots._select_clip_objects(item, 0)
        store.select_clip_objects.assert_called_once_with(7)
        self.assertEqual(_footer(ui)[0], "Selected 1 object(s) of 'cube 10-30'.")
        store.select_clip_objects.return_value = []
        slots._select_clip_objects(item, 0)
        self.assertEqual(
            _footer(ui), ("None of the clip's objects exist in the scene.", "warning")
        )


class TestKeyStashPanelActions(_PanelCase):
    def test_store_keys_stashes_from_the_chosen_source(self):
        slots, sb, ui = _panel()
        store = sb.tk.KeyStash.active.return_value
        ui.cmb000.currentData.return_value = "playback_range"
        store.stash_from.return_value = _clip()
        slots.b000()
        store.stash_from.assert_called_once_with("playback_range")
        self.assertEqual(_footer(ui), ("Stored 3 keys as 'cube 10-30'.", "success"))

    def test_store_keys_says_why_nothing_was_stored(self):
        slots, sb, ui = _panel()
        store = sb.tk.KeyStash.active.return_value
        # The host words a source it can't answer yet (Maya: no drag range;
        # Blender: no preview range); the panel says it as given.
        refusal = "Drag-select a range on the time slider first."
        store.stash_from.side_effect = ValueError(refusal)
        slots.b000()
        self.assertEqual(_footer(ui), (refusal, "warning"))
        store.stash_from.side_effect = RuntimeError("locked")
        slots.b000()
        self.assertEqual(_footer(ui), ("Store failed: locked", "error"))
        store.stash_from.side_effect = None
        store.stash_from.return_value = None
        slots.b000()
        self.assertEqual(_footer(ui), ("No keys found to store.", "warning"))

    def test_retrieve_at_the_original_frames_or_the_hosts_current_time(self):
        slots, sb, ui = _panel(selected=7)
        store = sb.tk.KeyStash.active.return_value
        store.retrieve.return_value = 3
        slots.b001()
        store.retrieve.assert_called_once_with(7, at=None)
        self.assertEqual(_footer(ui), ("Retrieved 3 keys.", "success"))
        ui.cmb001.currentText.return_value = "Current Time"
        sb.tk.AnimUtils.get_current_frame.return_value = 50.0
        slots.b001()
        store.retrieve.assert_called_with(7, at=50.0)

    def test_retrieve_says_what_went_wrong(self):
        slots, sb, ui = _panel(selected=7)
        store = sb.tk.KeyStash.active.return_value
        store.retrieve.return_value = 0
        slots.b001()
        self.assertEqual(_footer(ui)[1], "warning")
        self.assertIn("Nothing retrieved", _footer(ui)[0])
        store.retrieve.side_effect = RuntimeError("referenced")
        slots.b001()
        self.assertEqual(_footer(ui), ("Retrieve failed: referenced", "error"))

    def test_clip_actions_without_a_selected_clip_ask_for_one(self):
        slots, sb, ui = _panel()
        store = sb.tk.KeyStash.active.return_value
        slots.b001()
        self.assertEqual(_footer(ui), ("Select a stored clip to retrieve.", "warning"))
        slots.b003()
        self.assertEqual(_footer(ui), ("Select a stored clip to drop.", "warning"))
        ui.chk001.setChecked.reset_mock()
        slots.chk001(True)
        self.assertEqual(_footer(ui), ("Select a stored clip to preview.", "warning"))
        ui.chk001.setChecked.assert_called_once_with(False)  # unchecks itself
        store.retrieve.assert_not_called()
        store.drop.assert_not_called()
        store.preview.assert_not_called()

    def test_drop_confirms_through_the_message_box(self):
        slots, sb, ui = _panel(selected=7)
        store = sb.tk.KeyStash.active.return_value
        store.get_clip.return_value = _clip()
        sb.message_box.return_value = "No"
        slots.b003()
        self.assertIn("cube 10-30", sb.message_box.call_args.args[0])
        self.assertEqual(sb.message_box.call_args.args[1:], ("Yes", "No"))
        store.drop.assert_not_called()
        sb.message_box.return_value = "Yes"
        slots.b003()
        store.drop.assert_called_once_with(7)
        self.assertEqual(_footer(ui)[0], "Dropped 'cube 10-30'.")

    def test_preview_starts_and_ends_on_the_store(self):
        slots, sb, ui = _panel(selected=7)
        store = sb.tk.KeyStash.active.return_value
        ui.chk000.isChecked.return_value = False
        slots.chk001(True)
        store.preview.assert_called_once_with(7, in_context=False)
        self.assertIn("Previewing", _footer(ui)[0])
        store.end_preview.return_value = True
        slots.chk001(False)
        store.end_preview.assert_called_once_with()
        self.assertEqual(_footer(ui)[0], "Preview ended.")

    def test_a_refused_preview_unchecks_itself(self):
        slots, sb, ui = _panel(selected=7)
        store = sb.tk.KeyStash.active.return_value
        store.preview.side_effect = RuntimeError("none of the clip's objects")
        ui.chk001.setChecked.reset_mock()
        slots.chk001(True)
        ui.chk001.setChecked.assert_called_once_with(False)
        self.assertEqual(_footer(ui), ("none of the clip's objects", "error"))


class TestKeyStashPanelUi(unittest.TestCase):
    """The ``.ui``: the house layout the panel's widgets rely on."""

    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(UI_PATH).getroot()
        cls.widgets = {w.get("name"): w for w in cls.root.iter("widget")}

    def _prop(self, name, prop):
        node = self.widgets[name].find(f"property[@name='{prop}']")
        return node

    def _parent_group(self, name):
        for group in ("store_group", "clip_group"):
            if any(w.get("name") == name for w in self.widgets[group].iter("widget")):
                return group
        return None

    def test_every_widget_the_panel_uses_exists(self):
        for name in (
            "header", "store_group", "cmb000", "b000", "tree000", "clip_group",
            "cmb001", "b001", "b003", "chk000", "chk001", "footer",
        ):
            self.assertIn(name, self.widgets, name)

    def test_titled_groups_frame_the_actions(self):
        for group, title in (("store_group", "Store"), ("clip_group", "Selected Clip")):
            self.assertEqual(self.widgets[group].get("class"), "QGroupBox")
            self.assertEqual(self._prop(group, "title").findtext("string"), title)
        self.assertEqual(self._parent_group("cmb000"), "store_group")
        self.assertEqual(self._parent_group("b001"), "clip_group")
        self.assertEqual(self._parent_group("chk001"), "clip_group")

    def test_controls_use_the_19px_row(self):
        for name in ("cmb000", "b000", "cmb001", "b001", "b003", "chk000", "chk001"):
            height = self._prop(name, "maximumSize").findtext("size/height")
            self.assertEqual(height, "19", name)

    def test_preview_and_in_context_are_checkboxes_in_context_on(self):
        for name, text in (("chk001", "Preview"), ("chk000", "In Context")):
            self.assertEqual(self.widgets[name].get("class"), "QCheckBox")
            self.assertEqual(self._prop(name, "text").findtext("string"), text)
        self.assertEqual(self._prop("chk000", "checked").findtext("bool"), "true")

    def test_clip_list_shape(self):
        tree = self.widgets["tree000"]
        self.assertEqual(tree.get("class"), "TreeWidget")
        self.assertEqual(
            [c.findtext("property/string") for c in tree.findall("column")],
            ["Clip", "Objects", "Range", "Stored"],
        )
        self.assertEqual(
            self._prop("tree000", "selectionMode").findtext("enum"),
            "QAbstractItemView::SingleSelection",
        )
        self.assertEqual(self._prop("tree000", "rootIsDecorated").findtext("bool"), "false")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestKeyStashPanelInMaya(_PanelCase):
    """The panel over the real ``mtk`` store and a real scene (the widgets stay
    mocks: the clip list's selection is handed over as the tree would)."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self._reset_store()
        self.addCleanup(self._reset_store)
        self.cube = self.cmds.polyCube(name="stash_panel_cube")[0]
        for t, v in KEYS:
            self.cmds.setKeyframe(self.cube, attribute="translateX", time=t, value=v)
        self.cmds.currentTime(1)
        self.slots, self.sb, self.ui = _panel(tk=self.mtk)
        self.addCleanup(
            self.mtk.ScriptJobManager.instance().unsubscribe_all, self.slots
        )

    def _reset_store(self):
        stash = self.mtk.KeyStash
        if stash._active is not None and stash._active.is_previewing():
            stash._active.end_preview()
        backend = stash._persistence
        if backend is not None and hasattr(backend, "remove_callbacks"):
            backend.remove_callbacks()
        stash._active = None
        stash.set_persistence(None)

    def _times(self):
        return self.cmds.keyframe(
            f"{self.cube}.translateX", query=True, timeChange=True
        ) or []

    def _store_range(self, start=10, end=30):
        self.cmds.select(self.cube)
        self.cmds.playbackOptions(minTime=start, maxTime=end)
        self.ui.cmb000.currentData.return_value = "playback_range"
        self.slots.b000()
        clips = self.slots.store.clips
        self.assertTrue(clips, _footer(self.ui))
        return clips[-1]

    def test_the_sources_are_the_hosts(self):
        self.assertEqual(
            tuple(source for _, source in KeyStashSlots.SOURCES),
            tuple(self.mtk.KeyStash.STASH_SOURCES),
        )

    def test_store_then_retrieve_round_trips_the_keys(self):
        clip = self._store_range()
        self.assertEqual(self._times(), [1, 40])
        self.assertIn("Stored 3 keys", _footer(self.ui)[0])
        _select(self.ui, clip.clip_id)
        self.slots.b001()
        self.assertEqual(self._times(), [1, 10, 20, 30, 40])
        self.assertEqual(self.slots.store.clips, [])

    def test_retrieve_at_the_current_time(self):
        clip = self._store_range()
        _select(self.ui, clip.clip_id)
        self.ui.cmb001.currentText.return_value = "Current Time"
        self.cmds.currentTime(50)
        self.slots.b001()
        self.assertEqual(self._times(), [1, 40, 50, 60, 70])

    def test_store_without_a_selection_says_what_to_select(self):
        self.cmds.select(clear=True)
        self.ui.cmb000.currentData.return_value = "playback_range"
        self.slots.b000()
        self.assertEqual(self.slots.store.clips, [])
        self.assertIn("Select the object", _footer(self.ui)[0])

    def test_double_click_selects_the_clip_objects(self):
        clip = self._store_range()
        self.cmds.select(clear=True)
        item = _select(self.ui, clip.clip_id)
        self.slots._select_clip_objects(item, 0)
        self.assertEqual(self.cmds.ls(selection=True), [self.cube])

    def test_preview_runs_on_the_store_and_ends(self):
        clip = self._store_range()
        _select(self.ui, clip.clip_id)
        self.ui.chk000.isChecked.return_value = True
        self.slots.chk001(True)
        self.assertTrue(self.slots.store.is_previewing(clip.clip_id))
        self.slots.chk001(False)
        self.assertFalse(self.slots.store.is_previewing())

    def test_drop_deletes_the_clip_for_good(self):
        clip = self._store_range()
        _select(self.ui, clip.clip_id)
        self.sb.message_box.return_value = "Yes"
        self.slots.b003()
        self.assertEqual(self.slots.store.clips, [])
        self.assertEqual(self._times(), [1, 40])


if __name__ == "__main__":
    unittest.main()
