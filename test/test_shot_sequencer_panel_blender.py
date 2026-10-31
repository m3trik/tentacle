# !/usr/bin/python
# coding=utf-8
"""Panel tests for the shared Shot Sequencer tool, in Blender's handler.

Needs **Qt, not bpy**: loads ``ui/tools/shot_sequencer.ui`` (which promotes the
shared uitk ``SequencerWidget``) and wires ``ShotSequencerSlots`` through a real
(offscreen) Qt / Switchboard / BlenderUiHandler stack with tentacle's shared
roots registered, so the panel reaches Blender through blendertk as its ``tk``.
The controller's build path is headless-safe -- ``ShotStore.active()``
falls back to an in-memory store, the scene watcher attaches nothing without
``bpy`` (``btk.SequencerHost.watch_scene``), and ``_sync_to_widget`` degrades to
the shotless/no-scene path.  Proves the ``.ui`` compiles, the controller builds
(callbacks, store binding, widget signal wiring), and every widget signal maps
to a real controller slot.

The panel's handlers over a real scene are ``test/blender/shot_sequencer_panel_check.py``
(and the graph view's ``shot_sequencer_graph_check.py``); the engine and its host
half are blendertk's ``test_shot_sequencer.py``, under the Blender harness.
"""

import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")

HERE = os.path.dirname(os.path.abspath(__file__))
# blendertk is no install of the workspace Python: its repo goes on the path.
_BLENDERTK = os.path.join(os.path.dirname(os.path.dirname(HERE)), "blendertk")
if os.path.isdir(_BLENDERTK) and _BLENDERTK not in sys.path:
    sys.path.insert(0, _BLENDERTK)

try:
    from qtpy import QtWidgets
except Exception:  # pragma: no cover - Qt absent
    QtWidgets = None

if QtWidgets is not None:
    # Keep the panel's settings off the developer's live uitk stores.
    from uitk.testing import TestSandbox

    TestSandbox.activate()


@unittest.skipIf(QtWidgets is None, "Qt not available (Blender headless Python)")
class TestShotSequencerPanelLoads(unittest.TestCase):
    """The Shot Sequencer panel loads through the real discovery + compile path."""

    @classmethod
    def setUpClass(cls):
        import pythontk as ptk
        from blendertk import ShotStore

        # The panel's store is pure here, whatever host runs the suite (an
        # --in-maya run resolves Maya's, which would write that scene and open
        # its undo chunks); the host, its source and the prefs folder go back.
        cls._store_state = (
            ShotStore._host,
            ShotStore._host_source,
            ShotStore._prefs_dir_override,
        )
        ShotStore.set_host(ptk.PureShotsHost())
        cls._prefs_tmp = tempfile.mkdtemp(prefix="btk_seq_panel_")
        ShotStore._prefs_dir_override = cls._prefs_tmp
        ShotStore.clear_active()

        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        from uitk import Switchboard
        from blendertk.ui_utils.blender_ui_handler import BlenderUiHandler

        from tentacle.tcl import Tcl

        cls.sb = Switchboard()
        cls.handler = BlenderUiHandler(switchboard=cls.sb)
        # A process singleton: in a run that built it earlier (another panel
        # module) it keeps ITS switchboard, which is the one holding the UIs.
        cls.sb = cls.handler.sb
        Tcl.register_shared(cls.sb)
        cls.ui = cls.handler.get("shot_sequencer")
        for _ in range(5):
            cls.app.processEvents()

    @classmethod
    def tearDownClass(cls):
        from blendertk import ShotStore

        # Tear the controller's callbacks down explicitly (mirrors panel close).
        try:
            cls.ui.slots.controller.remove_callbacks()
        except Exception:
            pass
        ShotStore.clear_active()
        (
            ShotStore._host,
            ShotStore._host_source,
            ShotStore._prefs_dir_override,
        ) = cls._store_state

    def assertPromoted(self, name, *probes):
        """Fail (never skip) when a ``.ui`` widget did not promote to its uitk class.

        The Qt binding being absent is an *environment* gate and is handled once,
        at class level. Everything past that gate is a real defect: a widget that
        stayed a bare ``QWidget`` means the ``<customwidgets>`` header, the uitk
        class, or the loader broke -- exactly the regression these checks exist
        to catch, so it must assert rather than skip green.

        Parameters:
            name: Attribute name of the widget on ``self.ui``.
            probes: Attribute names the promoted class must expose.

        Returns:
            The promoted widget.
        """
        w = getattr(self.ui, name, None)
        self.assertIsNotNone(w, f"{name} is missing from the loaded shot_sequencer UI")
        for probe in probes:
            self.assertTrue(
                hasattr(w, probe),
                f"{name} did not promote to its uitk class "
                f"(no {probe!r}; got {type(w).__name__})",
            )
        return w

    def test_ui_loads(self):
        self.assertIsNotNone(self.ui, "shot_sequencer UI failed to load")

    def test_resolves_to_slots_class(self):
        self.assertEqual(type(self.ui.slots).__name__, "ShotSequencerSlots")

    def test_controller_built(self):
        ctrl = getattr(self.ui.slots, "controller", None)
        self.assertIsNotNone(ctrl)
        self.assertEqual(type(ctrl).__name__, "ShotSequencerController")

    def test_controller_mro_has_all_mixins(self):
        ctrl = self.ui.slots.controller
        names = {c.__name__ for c in type(ctrl).__mro__}
        for mixin in (
            "GapManagerMixin",
            "ClipMotionMixin",
            "ShotNavMixin",
            "MarkerManagerMixin",
        ):
            self.assertIn(mixin, names, f"{mixin} missing from controller MRO")

    def test_static_widgets_exist(self):
        expected = ["cmb_mode", "cmb_shot", "sequencer_widget"]
        missing = [w for w in expected if not hasattr(self.ui, w)]
        self.assertEqual(missing, [])

    def test_sequencer_widget_is_promoted(self):
        self.assertPromoted("sequencer_widget", "add_track")

    def test_signals_wired_to_real_slots(self):
        """Every widget signal in the wiring table maps to an existing controller slot."""
        from tentacle.slots.tools.shot_sequencer import ShotSequencerSlots

        ctrl = self.ui.slots.controller
        missing = [
            slot
            for _, slot in (
                *ShotSequencerSlots._WIRING,
                *ShotSequencerSlots._LAYER_WIRING,
            )
            if not hasattr(ctrl, slot)
        ]
        self.assertEqual(
            missing, [], f"wiring references missing controller slots: {missing}"
        )

    def test_widget_signal_connections_recorded(self):
        """The controller connected the widget signals (recorded on the widget)."""
        w = self.assertPromoted("sequencer_widget", "clip_resized")
        conns = getattr(w, "_slots_connections", [])
        self.assertGreater(len(conns), 0, "no widget signals were connected")

    def test_the_shot_layer_is_on_the_widget_and_wired(self):
        """The shot lane and the gaps are the panel's layer on uitk's widget
        (``ShotLayer``): added once, its lane under the ruler, its signals
        connected (recorded on the layer)."""
        from tentacle.slots.tools.shot_sequencer import ShotSequencerSlots

        w = self.assertPromoted("sequencer_widget", "add_layer")
        layer = w.layer("shot_lane")
        self.assertEqual(
            len(getattr(layer, "_slots_connections", [])),
            len(ShotSequencerSlots._LAYER_WIRING),
        )
        self.assertEqual(w.timeline.hit_zone(w._content_top - 1), "shot_lane")

    def test_zone_menu_reaches_the_controller(self):
        """Right-clicks emit ``zone_context_menu_requested`` (mayatk parity).

        The widget only emits it once ``zone_menu_enabled`` is set; otherwise
        every right-click falls through to its built-in default menu and the
        shot-lane menu (Edit / New Shot / Split / Merge / Trim ...) the
        controller wires is unreachable.
        """
        w = self.assertPromoted("sequencer_widget", "zone_menu_enabled")
        self.assertTrue(w.zone_menu_enabled)

    def test_shot_nav_options_built(self):
        """cmb_shot carries the full mayatk-mirror option set (prev/next/add/view/refresh).

        Pins the view-mode port through the REAL ActionOption path — the wiring
        sits in a try/except, so a bad option construction would otherwise be
        swallowed into a debug log and the dead-state regression would return.
        """
        cmb = self.assertPromoted("cmb_shot", "option_box")
        opts = getattr(cmb, "_shot_nav_options", None)
        self.assertIsNotNone(opts, "shot-nav options were not built (swallowed?)")
        for key in ("prev", "next", "add", "view", "views"):
            self.assertIsNotNone(opts.get(key), f"missing shot-nav option: {key}")
        # Show Internal Holds moved to the track view's Options menu; its
        # state is still adopted (mirror of mayatk)
        self.assertIsInstance(self.ui.slots.controller._show_internal_holds, bool)
        # the view cycle is adopted into the controller's display mode
        self.assertIn(
            self.ui.slots.controller._shot_display_mode, ("current", "adjacent", "all")
        )

    def test_playhead_to_shot_start_is_a_header_option(self):
        """One global option, on by default, that the controller follows
        (mayatk mirror, 2026-10-07)."""
        chk = getattr(self.ui, "chk_playhead_to_shot_start", None)
        self.assertIsNotNone(chk, "the header menu has no Playhead to Shot Start")
        ctrl = self.ui.slots.controller
        self.assertTrue(chk.isChecked())
        self.assertTrue(ctrl._playhead_to_shot_start)
        chk.setChecked(False)
        try:
            self.assertFalse(ctrl._playhead_to_shot_start)
        finally:
            chk.setChecked(True)
        self.assertTrue(ctrl._playhead_to_shot_start)

    def test_transport_controls_attached_once(self):
        """Footer carries ONE TransportControls row wired to the host's play
        controller (``btk.SequencerHost.play_controller``)."""
        from uitk.widgets.sequencer import TransportControls

        import blendertk as btk

        play_controller_cls = type(btk.SequencerHost.play_controller())

        footer = self.assertPromoted("footer", "add_action_button", "container_layout")
        transport = getattr(footer, "_shot_transport_controls", None)
        self.assertIsInstance(transport, TransportControls)
        self.assertIs(self.ui.slots.controller._transport_controls, transport)
        self.assertIsInstance(transport._play_controller, play_controller_cls)
        # headless (no bpy): the adapter reports "not playing" rather than raising
        self.assertFalse(transport._play_controller.is_playing())
        rows = [w for w in footer.findChildren(TransportControls)]
        self.assertEqual(len(rows), 1, "transport row duplicated on the footer")

    def test_cmb_shot_context_menu_installed(self):
        """Right-click on cmb_shot opens the New/Generate/Edit/Delete menu (mayatk mirror)."""
        from qtpy import QtCore

        cmb = self.assertPromoted("cmb_shot", "option_box")
        self.assertEqual(cmb.contextMenuPolicy(), QtCore.Qt.CustomContextMenu)
        for name in (
            "_cmb_context_menu",
            "_detect_next_shot",
            "_delete_shot",
            "_edit_shot_in_settings",
        ):
            self.assertTrue(callable(getattr(self.ui.slots, name, None)), name)

    def test_delete_shots_offers_each_scope_asks_and_drops_records(self):
        """The shot list's Delete Shots (mayatk mirror): a row per scope, on
        while that scope holds a shot; Stale asks with the names and drops
        records only.  The store's three scene hooks stand in for the file,
        so a Blender host answers as the .venv does."""
        from unittest import mock
        from qtpy import QtCore
        from uitk import ContextMenu

        ctl = self.ui.slots.controller
        store = ctl.sequencer.store
        for shot in list(store.shots):
            store.remove_shot(shot.shot_id)
        store.define_shot("GoneShot", 100, 120, objects=["Gone"])
        store.define_shot("LiveShot", 200, 220, objects=["Live"])
        store._existing_objects = lambda names: {n for n in names if n == "Live"}
        store._keyed_windows = lambda windows: [a <= 210 <= b for a, b in windows]
        # "Live" keys inside LiveShot; "Gone" resolves to nothing, so GoneShot
        # holds nothing and is Empty too (2026-10-10: Empty is what holds
        # nothing, whatever it names). Unstubbed, a Blender host's real hook
        # answered while the .venv's pure model never calls a shot empty.
        store._members_keyed_windows = lambda entries: [
            True if "Live" in names else None for names, _w in entries
        ]
        offered, asked = {}, []

        def shown(menu, *args, **kwargs):
            for row in menu.list.get_items():
                if callable(getattr(row, "text", None)):
                    offered[row.text()] = row.isEnabled()
                    if row.text() == "Delete Shots":
                        for child in row.sublist._row_widgets():
                            if hasattr(child, "text"):
                                offered[f"> {child.text()}"] = child.isEnabled()

        def answer(*args, **kwargs):
            asked.append(args[2])
            return QtWidgets.QMessageBox.Yes

        try:
            with mock.patch.object(ContextMenu, "exec_", new=shown):
                self.ui.slots._cmb_context_menu(QtCore.QPoint(0, 0))
            self.assertTrue(offered.get("Delete Shots"), offered)
            self.assertEqual(
                [offered.get(f"> {s}…") for s in ("Stale", "Empty", "All")],
                [True, True, True],
                offered,
            )
            with mock.patch.object(
                QtWidgets.QMessageBox, "question", new=staticmethod(answer)
            ):
                ctl.delete_shots("stale")
            self.assertIn("GoneShot [100–120]", asked[0])
            self.assertEqual([s.name for s in store.shots], ["LiveShot"])
        finally:
            del store._existing_objects, store._keyed_windows
            del store._members_keyed_windows
            for shot in list(store.shots):
                store.remove_shot(shot.shot_id)

    def test_the_view_button_the_header_refresh_and_the_track_options(self):
        """The view cycles beside the scope; Refresh is the header's; Show
        Internal Holds is the track view's Options row."""
        cmb = self.ui.cmb_shot
        views = cmb._shot_nav_options["views"]
        self.assertEqual(len(views._state_cycle.states), 3)
        self.assertNotIn("holds", cmb._shot_nav_options)
        self.assertNotIn("refresh", cmb._shot_nav_options)
        self.assertFalse(hasattr(self.ui, "cmb_view"))
        header = self.ui.header
        self.assertIn("refresh", header.buttons)
        dismiss = {"pin", "hide"} & set(header.buttons)
        self.assertEqual(len(dismiss), 1, f"one dismissal button: {dismiss}")
        self.assertEqual(header.help_url(), self.ui.slots.HELP_URL, "the guide")
        seq = self.ui.slots.controller._get_sequencer_widget()
        labels = [row["label"] for row in seq.editor("tracks").options()]
        self.assertIn("Show Internal Holds", labels)  # beside uitk's own rows
        ctl = self.ui.slots.controller
        ctl._set_view("compact")
        self.assertTrue(seq.row_metrics.flat_keys)
        ctl._set_view("standard")
        self.assertFalse(seq.row_metrics.flat_keys)

    def test_key_edit_rows_mirror_mayatk(self):
        """The Edit submenu's rows, Simplify included, and their handlers."""
        from qtpy import QtWidgets

        ctl = self.ui.slots.controller
        self.assertEqual(
            [label for label, _m in ctl._KEY_EDITS],
            [
                "Simplify",
                "Remove Intermediate Keys",
                "Snap Fractional Keys",
                "Invert Keys",
                "Align Keys",
                "Euler Filter",
            ],
        )
        for _label, method in ctl._KEY_EDITS:
            self.assertTrue(callable(getattr(ctl, method, None)), method)

        menu = QtWidgets.QMenu()
        try:
            targets = [("cube", "translateX", [0.0, 10.0], 1)]
            ctl._add_key_edit_actions(menu, targets, " (2)")
            edit = next(a.menu() for a in menu.actions() if a.text() == "Edit")
            self.assertEqual(
                [a.text() for a in edit.actions()],
                [label for label, _m in ctl._KEY_EDITS],
            )
        finally:
            menu.deleteLater()

    def test_sub_row_label_selection_is_wired(self):
        """The header's per-channel pick reaches a handler (mayatk mirror)."""
        ctl = self.ui.slots.controller
        self.assertTrue(callable(getattr(ctl, "on_sub_track_selected", None)))
        self.assertTrue(callable(getattr(ctl, "_mirror_channels", None)))
        self.assertIn(
            ("sub_track_selected", "on_sub_track_selected"),
            list(self.ui.slots._WIRING),
        )
        widget = ctl._get_sequencer_widget()
        if widget is not None:
            self.assertTrue(hasattr(widget, "sub_track_selected"))

    def test_move_to_shot_takes_stepped_and_read_only_clips(self):
        """Mirror of mayatk's TestMoveToShotTakesEveryVisibleClip."""

        class _Clip:
            def __init__(self, **data):
                self.data = data

        class _Widget:
            def __init__(self, clips):
                self._clips = clips

            def get_clip(self, cid):
                return self._clips.get(cid)

        widget = _Widget(
            {
                1: _Clip(obj="a", orig_start=10.0, orig_end=30.0),
                2: _Clip(obj="a", is_stepped=True, orig_start=45.0, orig_end=45.0),
                3: _Clip(obj="b", read_only=True, orig_start=70.0, orig_end=90.0),
            }
        )
        ctl = self.ui.slots.controller
        seqs = ctl._clips_to_sequences(widget, [1, 2, 3], include_read_only=True)
        self.assertEqual([q["obj"] for q in seqs], ["a", "a", "b"])
        self.assertEqual(seqs[1]["times"], [45.0])
        self.assertEqual(
            ctl._clips_to_sequences(widget, [3]), [], "drags keep the gate"
        )

    def test_controller_parity_surface(self):
        """Every mayatk controller slot the widget/menu can reach exists here too."""
        ctl = self.ui.slots.controller
        for name in (
            "_build_audio_tracks",
            "_clips_to_sequences",
            "_send_to_shot",
            "_add_send_to_shot_menu",
            "_set_show_internal_holds",
            "_ensure_sound_on_timeline",
            "_setup_transport_controls",
            "_playback_range",
            "on_key_selection_changed",
            "_delete_selected_clip_keys",
            "_reveal_in_outliner",
            "on_undo",
        ):
            self.assertTrue(callable(getattr(ctl, name, None)), name)
        # audio-track label prefix round-trips through _resolve_full_name
        self.assertEqual(ctl._resolve_full_name("♫ Strip"), "Strip")

    def test_reinit_stashes_and_tears_down_prior_controller(self):
        """Re-initing the slots over the same UI tears the old controller down
        (its scene watcher + store/invalidation listeners) instead of leaking it."""
        from tentacle.slots.tools.shot_sequencer import ShotSequencerSlots

        first = self.ui._shot_seq_controller
        self.assertIs(first, self.ui.slots.controller)
        second_slots = ShotSequencerSlots(self.sb)
        try:
            self.assertIsNot(
                self.ui._shot_seq_controller,
                first,
                "re-init did not stash the new controller",
            )
            # the old controller's invalidation listener must be gone
            from blendertk import ShotStore

            self.assertNotIn(
                first._on_store_invalidated, ShotStore._invalidation_listeners
            )
        finally:
            second_slots.controller.remove_callbacks()


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    )
    # Report the tally in the harness's (ok/attempted) form -- without it the
    # suite counts for zero checks in run_tests.py's totals. Skips are neither
    # passes nor failures, so they leave the ratio entirely (a fully skipped
    # suite reports 0/0, exactly what it contributed).
    _attempted = result.testsRun - len(result.skipped)
    _ok = _attempted - len(result.failures) - len(result.errors)
    _tally = f"{_ok}/{_attempted}" if _attempted else "skipped"
    print(f"===RESULT: {'PASS' if result.wasSuccessful() else 'FAIL'}=== ({_tally})")
