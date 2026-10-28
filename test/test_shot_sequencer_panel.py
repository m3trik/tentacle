#!/usr/bin/python
# coding=utf-8
"""The Shot Sequencer panel's one Slots class (and its controller's host seam),
shared by both hosts.

The panel reaches its host only through ``self.tk``: the host library's
``SequencerHost`` (every scene call), ``ShotSequencer`` and that class's
``STORE_CLASS``. Here a fake toolkit stands in for ``mtk`` / ``btk`` and records
what the panel asks of it -- plain unittest, no DCC; the ``.ui`` is read as XML,
and both libraries' ``SequencerHost`` are read as source, to pin that they
answer every call the panel makes under one signature. One class drives the
real ``mtk`` in a fresh Maya.

Where the rest is tested: the controller's behavior over the real ``mtk`` is
``test_shot_sequencer_controller.py`` (``--in-maya``), over ``btk`` without bpy
``test_shot_sequencer_panel_blender.py`` and in Blender
``test/blender/shot_sequencer_*_check.py`` (``--in-blender``); the host halves
are the libraries' (mayatk ``test_sequencer.py``, blendertk
``test_shot_sequencer.py``).
"""

import ast
import contextlib
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pythontk as ptk

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools import shot_sequencer as slots_module
from tentacle.slots.tools._shot_sequencer.controller import ShotSequencerController
from tentacle.slots.tools._shot_sequencer.shot_edit_dialog import ShotEditDialog
from tentacle.slots.tools.shot_sequencer import ShotSequencerSlots

PKG = Path(tentacle.__file__).resolve().parent
MONO = PKG.parents[1]
UI_PATH = PKG / "ui" / "tools" / "shot_sequencer.ui"
SLOTS_PATH = PKG / "slots" / "tools" / "shot_sequencer.py"
HELPERS = PKG / "slots" / "tools" / "_shot_sequencer"
#: Each library's host half of the panel.
HOST_PATHS = {
    lib: MONO
    / lib
    / lib
    / "anim_utils"
    / "shots"
    / "shot_sequencer"
    / "sequencer_host.py"
    for lib in ("mayatk", "blendertk")
}

#: The window's own widgets: saved settings key on these names.
UI_WIDGETS = (
    "shot_sequencer",
    "header",
    "footer",
    "cmb_mode",
    "cmb_shot",
    "sequencer_widget",
)


class _Store(ptk.ShotStore):
    """The pure model as a host's store class: no scene, no persistence."""


def _fake_tk(store_cls=_Store):
    """A toolkit double: ``SequencerHost`` and ``ShotSequencer`` are mocks
    (calls on them are recorded), the engine's ``STORE_CLASS`` is *store_cls*."""
    tk = mock.MagicMock()
    tk.ShotSequencer.STORE_CLASS = store_cls
    return tk


def _sb(tk=None):
    """A mock switchboard over *tk* whose window's dropdown has no nav options
    built yet (a first open)."""
    sb = mock.MagicMock()
    sb.tk = tk if tk is not None else _fake_tk()
    sb.loaded_ui.shot_sequencer.cmb_shot._shot_nav_options = None
    sb.loaded_ui.shot_sequencer._shot_seq_controller = None
    return sb


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)

    def _slots(self, sb=None):
        """``ShotSequencerSlots`` over *sb* with a mock controller class:
        ``(slots, sb, the controller class)``."""
        sb = sb or _sb()
        with mock.patch.object(slots_module, "ShotSequencerController") as ctl_cls:
            slots = ShotSequencerSlots(sb)
        return slots, sb, ctl_cls


def _host_reads(paths):
    """Every ``self.host.<name>`` the panel's modules read."""
    names = set()
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Attribute)
                and ast.unparse(node.value) == "self.host"
            ):
                names.add(node.attr)
    return names


def _host_members(path):
    """``{name: parameter names}`` of a library's ``SequencerHost`` (``cls`` /
    ``self`` dropped; attributes map to ``None``)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    members = {}
    for node in tree.body:
        if not (isinstance(node, ast.ClassDef) and node.name == "SequencerHost"):
            continue
        for m in node.body:
            if isinstance(m, ast.FunctionDef):
                args = [a.arg for a in m.args.posonlyargs + m.args.args]
                decorators = {ast.unparse(d) for d in m.decorator_list}
                if "staticmethod" not in decorators:
                    args = args[1:]
                kw = [a.arg for a in m.args.kwonlyargs]
                members[m.name] = (tuple(args), tuple(kw))
            elif isinstance(m, ast.Assign):
                for target in m.targets:
                    if isinstance(target, ast.Name):
                        members[target.id] = None
    return members


# ---------------------------------------------------------------------- the .ui


class TestShotSequencerUi(_PanelCase):
    """The ``.ui`` is the libraries' (mayatk's and blendertk's twins were
    identical): its window and widget names are saved settings."""

    def setUp(self):
        super().setUp()
        root = ET.parse(UI_PATH).getroot()
        self.widgets = {w.get("name"): w.get("class") for w in root.iter("widget")}

    def test_the_window_and_its_widgets_keep_their_names(self):
        for name in UI_WIDGETS:
            self.assertIn(name, self.widgets)
        self.assertEqual(self.widgets["sequencer_widget"], "SequencerWidget")

    def test_the_runtime_rows_are_not_in_the_ui(self):
        self.assertEqual(
            set(ShotSequencerSlots.RUNTIME_WIDGETS) & set(self.widgets), set()
        )

    def test_the_ui_names_no_host(self):
        text = UI_PATH.read_text(encoding="utf-8")
        for word in ("Maya", "Blender"):
            self.assertNotIn(word, text)


# ---------------------------------------------------------------- the slots


class TestTheSlotsBuildThePanel(_PanelCase):
    """``__init__`` builds the controller, wires the widget, binds the keys and
    builds the host's graph half -- through ``self.tk`` only."""

    def test_the_controller_is_built_over_the_slots(self):
        slots, sb, ctl_cls = self._slots()
        ctl_cls.assert_called_once_with(slots)
        self.assertIs(slots.ui, sb.loaded_ui.shot_sequencer)
        self.assertIs(slots.ui._shot_seq_controller, slots.controller)

    def test_a_reinit_tears_the_previous_controller_down(self):
        sb = _sb()
        old = mock.MagicMock()
        sb.loaded_ui.shot_sequencer._shot_seq_controller = old
        self._slots(sb)
        old.remove_callbacks.assert_called_once_with()

    def test_every_widget_signal_reaches_its_controller_slot(self):
        slots, _sb_, _cls = self._slots()
        widget = slots.controller._get_sequencer_widget.return_value
        for sig_name, slot_name in ShotSequencerSlots._WIRING:
            with self.subTest(signal=sig_name):
                getattr(widget, sig_name).connect.assert_called_with(
                    getattr(slots.controller, slot_name)
                )
        self.assertEqual(
            len(widget._slots_connections), len(ShotSequencerSlots._WIRING)
        )
        self.assertTrue(widget.zone_menu_enabled)

    def test_every_wired_slot_is_a_controller_method(self):
        for _sig, slot_name in ShotSequencerSlots._WIRING:
            with self.subTest(slot=slot_name):
                self.assertTrue(
                    callable(getattr(ShotSequencerController, slot_name, None))
                )

    def test_a_reinit_disconnects_the_previous_wiring(self):
        sb = _sb()
        slots, _sb_, _cls = self._slots(sb)
        widget = slots.controller._get_sequencer_widget.return_value
        first = list(widget._slots_connections)
        sb.loaded_ui.shot_sequencer._shot_seq_controller = None
        with mock.patch.object(slots_module, "ShotSequencerController") as ctl_cls:
            ctl_cls.return_value._get_sequencer_widget.return_value = widget
            ShotSequencerSlots(sb)
        for sig_name, slot in first:
            getattr(widget, sig_name).disconnect.assert_any_call(slot)

    def test_the_keys_bind_to_the_controller(self):
        slots, _sb_, _cls = self._slots()
        widget = slots.controller._get_sequencer_widget.return_value
        keys = [c.args[:2] for c in widget.shortcut_manager.add_shortcut.call_args_list]
        self.assertEqual(
            keys,
            [
                ("Delete", slots.controller._delete_selected_clip_keys),
                ("Ctrl+C", slots.controller._copy_keys_shortcut),
                ("Ctrl+V", slots.controller._paste_keys_shortcut),
            ],
        )

    def test_the_graph_half_is_the_hosts(self):
        slots, sb, _cls = self._slots()
        widget = slots.controller._get_sequencer_widget.return_value
        graph_cls = sb.tk.SequencerHost.graph_sync_cls.return_value
        graph_cls.assert_called_once_with(slots.controller, widget)
        self.assertIs(widget._graph_sync, slots.graph_sync)

    def test_a_reinit_detaches_the_previous_graph_half(self):
        sb = _sb()
        slots, _sb_, _cls = self._slots(sb)
        widget = slots.controller._get_sequencer_widget.return_value
        old_graph = widget._graph_sync
        sb.loaded_ui.shot_sequencer._shot_seq_controller = None
        with mock.patch.object(slots_module, "ShotSequencerController") as ctl_cls:
            ctl_cls.return_value._get_sequencer_widget.return_value = widget
            ShotSequencerSlots(sb)
        old_graph.detach.assert_called_once_with()

    def test_no_widget_wires_nothing_and_still_populates(self):
        sb = _sb()
        with mock.patch.object(slots_module, "ShotSequencerController") as ctl_cls:
            ctl_cls.return_value._get_sequencer_widget.return_value = None
            slots = ShotSequencerSlots(sb)
        sb.tk.SequencerHost.graph_sync_cls.assert_not_called()
        slots.controller._setup_transport_controls.assert_called_once_with()
        slots.controller._sync_combobox.assert_called_once_with()
        slots.controller._sync_to_widget.assert_called_once_with()

    def test_the_shot_dropdown_restores_no_index(self):
        slots, _sb_, _cls = self._slots()
        self.assertFalse(slots.ui.cmb_shot.restore_state)


class TestTheShotNav(_PanelCase):
    """The dropdown's option box: previous / next, New Shot, scope and view."""

    def test_the_options_are_built_once_and_kept_on_the_dropdown(self):
        slots, sb, _cls = self._slots()
        opts = slots.ui.cmb_shot._shot_nav_options
        self.assertEqual(set(opts), {"prev", "next", "add", "view", "views"})
        self.assertEqual(slots.ui.cmb_shot.option_box.add_option.call_count, 5)
        self.assertEqual(
            {c.kwargs.get("settings_key") for c in sb.ActionOption.call_args_list}
            - {None},
            {"shot_sequencer_view"},
        )

    def test_a_reinit_adopts_the_built_options(self):
        sb = _sb()
        built = {k: mock.MagicMock(current_state=0) for k in ("prev", "next", "view")}
        sb.loaded_ui.shot_sequencer.cmb_shot._shot_nav_options = built
        slots, _sb_, _cls = self._slots(sb)
        slots.ui.cmb_shot.option_box.add_option.assert_not_called()
        self.assertIs(slots.controller._prev_action, built["prev"])
        self.assertEqual(slots.controller._shot_display_mode, "current")

    def test_the_mode_combo_offers_shots_then_markers(self):
        slots, _sb_, _cls = self._slots()
        items = [c.args for c in slots.ui.cmb_mode.addItem.call_args_list]
        self.assertEqual(items, [("Shots:", "shots"), ("Markers:", "markers")])


class TestTheHeaderMenu(_PanelCase):
    """The header's rows are saved settings: their names and each combo's item
    order (a combo saves its index) never change."""

    def _built(self):
        """The header after ``header_init``: each row ``menu.add`` built is its
        own mock, kept by objectName in ``rows``."""
        slots, _sb_, _cls = self._slots()
        header = mock.MagicMock()
        rows = {}

        def add(*args, **kwargs):
            row = mock.MagicMock()
            if "setObjectName" in kwargs:
                rows[kwargs["setObjectName"]] = row
            return row

        header.menu.add.side_effect = add
        slots.header_init(header)
        header.rows = rows
        return slots, header

    def test_every_runtime_row_is_built(self):
        _slots, header = self._built()
        names = {
            c.kwargs["setObjectName"]
            for c in header.menu.add.call_args_list
            if "setObjectName" in c.kwargs
        }
        self.assertEqual(names, set(ShotSequencerSlots.RUNTIME_WIDGETS))

    def test_the_combos_keep_their_item_order(self):
        slots, header = self._built()
        expected = {
            "cmb_shortcut_overlay": ["off", "on", "modifier"],
            "cmb_playback_range": ["off", "follows_view", "locked"],
            "cmb_track_order": ["visible", "global"],
        }
        for name, data in expected.items():
            with self.subTest(combo=name):
                items = [c.args[1] for c in header.rows[name].addItem.call_args_list]
                self.assertEqual(items, data)
        built = [c.args[0] for c in header.menu.add.call_args_list]
        self.assertIn(slots.sb.WidgetComboBox, built)
        # Follows Scope is the playback range's default.
        header.rows["cmb_playback_range"].setCurrentIndex.assert_called_with(1)

    def test_the_store_owned_rows_restore_nothing(self):
        _slots, header = self._built()
        for name in ("chk_select_on_load", "chk_frame_on_shot_change"):
            with self.subTest(row=name):
                self.assertFalse(header.rows[name].restore_state)

    def test_extend_distance_follows_its_switch(self):
        slots, header = self._built()
        chk, spn = header.rows["chk_extend_to_keys"], header.rows["spn_extend_reach"]
        spn.setEnabled.assert_called_once_with(False)
        chk.toggled.connect.assert_any_call(slots.controller._set_extend_to_keys)
        chk.toggled.connect.assert_any_call(spn.setEnabled)
        spn.valueChanged.connect.assert_called_once_with(
            slots.controller._set_extend_reach
        )

    def test_sticky_chrome_and_the_guide(self):
        slots, header = self._built()
        header.config_buttons.assert_called_with("refresh", "menu", "collapse", "hide")
        self.assertEqual(header.set_help_text.call_args.kwargs["url"], slots.HELP_URL)

    def test_the_help_names_no_host(self):
        slots, _sb_, _cls = self._slots()
        header = mock.MagicMock()
        slots.sb.tooltip.fmt = lambda **kw: repr(kw)
        slots.sb.tooltip.kbd = lambda *keys: "+".join(keys)
        slots._set_help(header)
        text = header.set_help_text.call_args.args[0]
        for word in ("Maya", "Blender"):
            self.assertNotIn(word, text)


class TestTheDropdown(_PanelCase):
    """``cmb_shot``: a shot goes to the shot, a marker moves the playhead."""

    def _host(self, mode, data):
        cmb = mock.MagicMock()
        cmb.itemData.return_value = data
        controller = mock.MagicMock(_cmb_mode=mode)
        return SimpleNamespace(ui=SimpleNamespace(cmb_shot=cmb), controller=controller)

    def test_a_shot_goes_to_the_shot(self):
        host = self._host("shots", 7)
        ShotSequencerSlots.cmb_shot(host, 2)
        host.controller._go_to_shot.assert_called_once_with(7)

    def test_a_marker_moves_the_playhead(self):
        host = self._host("markers", 42.0)
        ShotSequencerSlots.cmb_shot(host, 0)
        widget = host.controller._get_sequencer_widget.return_value
        widget.set_playhead.assert_called_once_with(42.0)
        widget.playhead_moved.emit.assert_called_once_with(42.0)
        host.controller._go_to_shot.assert_not_called()

    def test_no_index_does_nothing(self):
        host = self._host("shots", 7)
        ShotSequencerSlots.cmb_shot(host, -1)
        host.controller._go_to_shot.assert_not_called()


class TestGenerateNextShot(_PanelCase):
    """Generate Next Shot: the engine's next cluster, named in the dialog,
    defined inside one ``scene_edit``."""

    def _panel(self, cand):
        store = _Store()
        store.define_shot("A", 0, 50)
        edits = []

        @contextlib.contextmanager
        def scene_edit(label="edit", snapshot=True):
            edits.append(label)
            yield mock.MagicMock()

        store.scene_edit = scene_edit
        seq = mock.MagicMock()
        seq.store = store
        seq.detect_next_shot.return_value = cand
        controller = mock.MagicMock(sequencer=seq)
        return SimpleNamespace(controller=controller, ui=None), seq, edits

    def test_a_cluster_becomes_a_shot(self):
        cand = {"name": "Shot_1", "start": 60.0, "end": 90.0, "objects": ["a"]}
        panel, seq, edits = self._panel(cand)
        with mock.patch.object(
            ShotEditDialog, "show", return_value=("Next", 60.0, 90.0, "d")
        ) as show:
            ShotSequencerSlots._detect_next_shot(panel)
        self.assertEqual(show.call_args.kwargs["validate"], seq.store.name_error)
        seq.define_shot.assert_called_once_with(
            name="Next", start=60.0, end=90.0, objects=["a"], description="d"
        )
        self.assertEqual(edits, ["Generate Shot"])
        panel.controller._take_new_shot.assert_called_once_with(
            seq.define_shot.return_value
        )

    def test_no_cluster_says_so(self):
        panel, seq, edits = self._panel(None)
        ShotSequencerSlots._detect_next_shot(panel)
        panel.controller._set_footer.assert_called_once_with(
            "No additional animation clusters found."
        )
        self.assertEqual(edits, [])

    def test_a_cancelled_or_empty_dialog_defines_nothing(self):
        cand = {"name": "Shot_1", "start": 60.0, "end": 90.0, "objects": []}
        for answer in (None, ("Next", 90.0, 60.0, "")):
            with self.subTest(answer=answer):
                panel, seq, edits = self._panel(cand)
                with mock.patch.object(ShotEditDialog, "show", return_value=answer):
                    ShotSequencerSlots._detect_next_shot(panel)
                seq.define_shot.assert_not_called()
                self.assertEqual(edits, [])


# ---------------------------------------------------------------- the host seam


class TestTheControllerReachesTheHostThroughTk(unittest.TestCase):
    """The controller's host is ``tk.SequencerHost``; its engine and store
    classes ``tk.ShotSequencer`` and its ``STORE_CLASS``."""

    def _bare(self, tk):
        ctl = ShotSequencerController.__new__(ShotSequencerController)
        ctl.tk = tk
        ctl._sequencer = None
        ctl.logger = mock.MagicMock()
        return ctl

    def test_the_host_is_the_toolkits(self):
        tk = _fake_tk()
        self.assertIs(self._bare(tk).host, tk.SequencerHost)

    def test_the_engine_is_built_over_the_active_store(self):
        self.addCleanup(_Store.clear_active)
        tk = _fake_tk()
        ctl = self._bare(tk)
        self.assertIs(ctl._store_cls(), _Store)
        seq = ctl.sequencer
        tk.ShotSequencer.assert_called_once_with(store=_Store.active())
        self.assertIs(seq, tk.ShotSequencer.return_value)

    def test_the_playhead_is_the_hosts_and_none_on_failure(self):
        tk = _fake_tk()
        ctl = self._bare(tk)
        tk.SequencerHost.current_time.return_value = 12.0
        self.assertEqual(ctl._current_time(), 12.0)
        tk.SequencerHost.current_time.side_effect = RuntimeError("no scene")
        self.assertIsNone(ctl._current_time())


class TestTheModulesNameNoHost(unittest.TestCase):
    """One copy for both hosts: no module of the panel imports a host, a host
    library or uitk (uitk resolves off the switchboard)."""

    BANNED = ("maya", "bpy", "mayatk", "blendertk", "uitk")

    def test_no_host_import(self):
        for path in [SLOTS_PATH, *sorted(HELPERS.glob("*.py"))]:
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    roots = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    roots = [(node.module or "").split(".")[0]]
                else:
                    continue
                with self.subTest(module=path.name, line=node.lineno):
                    self.assertFalse(set(roots) & set(self.BANNED), ast.unparse(node))


@unittest.skipUnless(
    all(p.is_file() for p in HOST_PATHS.values()), "the libraries are not checked out"
)
class TestBothHostsAnswerEveryCall(unittest.TestCase):
    """Every ``self.host.<name>`` the panel reads is a ``SequencerHost`` member
    in BOTH libraries, and every public member has one signature in both --
    the seam's whole contract, read from source so it needs no host."""

    def setUp(self):
        self.members = {lib: _host_members(p) for lib, p in HOST_PATHS.items()}

    def test_every_call_is_answered(self):
        reads = _host_reads([SLOTS_PATH, *HELPERS.glob("*.py")])
        self.assertTrue(reads, "no host reads found: a moved package?")
        for lib, members in self.members.items():
            with self.subTest(lib=lib):
                self.assertEqual(sorted(reads - set(members)), [])

    def test_one_signature_in_both_hosts(self):
        maya, blender = self.members["mayatk"], self.members["blendertk"]
        public = {n for n in set(maya) | set(blender) if not n.startswith("_")}
        for name in sorted(public):
            with self.subTest(member=name):
                self.assertIn(name, maya)
                self.assertIn(name, blender)
                self.assertEqual(maya[name], blender[name])


# ---------------------------------------------------------------- in Maya


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestShotSequencerPanelInMaya(unittest.TestCase):
    """The controller over the real ``mtk``: the toolkit is handed over before
    anything resolves through it, as the slots do."""

    def setUp(self):
        self.cmds = cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        cmds.file(new=True, force=True)
        self.store = self.mtk.ShotStore()
        self.store.define_shot("A", 0, 50)
        self.store.define_shot("B", 60, 100)
        self.ctl = ShotSequencerController.__new__(ShotSequencerController)
        self.ctl.tk = self.mtk
        self.ctl._sequencer = self.mtk.ShotSequencer(store=self.store)
        self.ctl._syncing = False
        self.ctl._cmb_mode = "shots"
        self.ctl.ui = SimpleNamespace()  # no dropdown: the store / playhead decide
        self.ctl.logger = mock.MagicMock()

    def tearDown(self):
        self.mtk.ShotStore.clear_active()

    def test_every_host_call_resolves_on_mtk(self):
        reads = _host_reads([SLOTS_PATH, *HELPERS.glob("*.py")])
        missing = sorted(n for n in reads if not hasattr(self.mtk.SequencerHost, n))
        self.assertEqual(missing, [])

    def test_the_playhead_picks_the_shot_when_none_is_active(self):
        self.cmds.currentTime(75)
        self.assertEqual(self.ctl._current_time(), 75.0)
        self.assertEqual(self.ctl.active_shot_id, self.store.shot_by_name("B").shot_id)

    def test_a_gap_lock_lands_in_the_store(self):
        self.ctl.on_gap_lock_changed(50.0, 60.0, True)
        a, b = self.store.shot_by_name("A"), self.store.shot_by_name("B")
        self.assertTrue(self.store.is_gap_locked(a.shot_id, b.shot_id))
        self.ctl.on_gap_lock_changed(50.0, 60.0, False)
        self.assertFalse(self.store.is_gap_locked(a.shot_id, b.shot_id))


if __name__ == "__main__":
    unittest.main()
