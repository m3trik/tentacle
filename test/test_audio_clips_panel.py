#!/usr/bin/python
# coding=utf-8
"""The Audio Clips panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk.AudioClips``, so a fake engine
stands in for mayatk's or blendertk's and records what the panel asks of it:
plain pytest, no DCC, no widgets loaded. Each fake carries exactly its host's
operations (``MAYA_API`` / ``BLENDER_API``), which is what the panel's
capability gates read. The ``.ui`` is read as XML for the names it keeps. In
Maya, the same class drives the real ``mtk.AudioClips`` end to end; the engines'
own side is the libraries' ``test_audio_clips.py``.
"""

import os
import unittest
import wave
import xml.etree.ElementTree as ET
from unittest import mock

import pythontk as ptk

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.audio_clips import AudioClipsSlots

UI_PATH = os.path.join(
    os.path.dirname(tentacle.__file__), "ui", "tools", "audio_clips.ui"
)

#: The operations both engines carry: the panel's shared vocabulary.
SHARED_API = (
    "ITEM_NOUN",
    "PLACE_LABEL",
    "REVEAL_LABEL",
    "END_KEYS",
    "PLAYABLE_EXTENSIONS",
    "list_tracks",
    "find_track",
    "add_tracks",
    "rename_track",
    "replace_track",
    "remove_track",
    "remove",
    "key_track",
    "reveal",
    "watch",
)
#: mayatk's ``AudioClips``: the shared API plus the composite, keying options,
#: export, Channels, legacy schema and snap.
MAYA_API = SHARED_API + (
    "sync",
    "key_all",
    "next_track",
    "tracks_at",
    "activate_track",
    "attach_composite",
    "cleanup_unused",
    "export_composite",
    "export_tracks",
    "channels_config",
    "has_legacy_data",
    "migrate_legacy",
    "get_snap_frames",
    "set_snap_frames",
    "watch_snap",
)
#: blendertk's ``AudioClips``: the shared API plus a strip's trim and the
#: scene-range fit.
BLENDER_API = SHARED_API + ("get_trim", "trim_track", "sync_scene_range")

#: The names the panel builds in code, by host-neutral role (saved settings).
TRACKS_MENU = (
    "btn_add_tracks",
    "btn_rename_track",
    "btn_replace_track",
    "btn_remove_selected",
    "btn_cleanup_unused",
    "btn_remove_audio",
)


class _Combo:
    """The list's surface the panel uses (a real list, so picks stick)."""

    def __init__(self, items=()):
        self.items, self.index = list(items), 0 if items else -1
        self.option_box = mock.MagicMock()
        self.before_popup_shown = mock.MagicMock()

    def findText(self, text):
        return self.items.index(text) if text in self.items else -1

    def currentText(self):
        return self.items[self.index] if 0 <= self.index < len(self.items) else ""

    def setCurrentIndex(self, index):
        self.index = index

    def clear(self):
        self.items, self.index = [], -1

    def addItems(self, names):
        self.items.extend(names)
        if self.index < 0 and self.items:
            self.index = 0

    def count(self):
        return len(self.items)

    def blockSignals(self, _block):
        return False


def _engine(api=MAYA_API, tracks=("kick", "snare")):
    """A fake host engine carrying exactly *api*."""
    maya = api is MAYA_API
    engine = mock.MagicMock(spec=list(api))
    engine.ITEM_NOUN = "Track" if maya else "Clip"
    engine.PLACE_LABEL = "Key Audio Event" if maya else "Move To Current Frame"
    engine.REVEAL_LABEL = "Select Carrier Node" if maya else "Reveal In Sequencer"
    engine.END_KEYS = maya
    engine.PLAYABLE_EXTENSIONS = (
        frozenset({".wav", ".aif", ".aiff"})
        if maya
        else frozenset(ptk.AudioUtils.SOURCE_EXTENSIONS | {".aac", ".opus"})
    )
    engine.list_tracks.return_value = list(tracks)
    engine.key_track.return_value = 12.0
    return engine


def _panel(engine=None, tk=None, current="kick"):
    """A Slots instance over a mock ui (its list a real ``_Combo`` showing
    *current*) and a fake engine, or the toolkit *tk* (handed over before the
    panel is built, as ``Slots.tk`` is)."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        sb.tk.AudioClips = engine if engine is not None else _engine()
    ui = sb.loaded_ui.audio_clips
    tracks = list(sb.tk.AudioClips.list_tracks()) if tk is None else []
    ui.cmb000 = _Combo(tracks)
    if current in ui.cmb000.items:
        ui.cmb000.setCurrentIndex(ui.cmb000.findText(current))
    for name in ("chk_auto_end_none", "chk_next_event", "chk_key_all"):
        getattr(ui.tb001.option_box.menu, name).isChecked.return_value = False
    ui.tb001.option_box.menu.spn_stagger.value.return_value = 0
    ui.header.menu.chk_auto_convert.isChecked.return_value = True
    return AudioClipsSlots(sb), sb, ui


class _ItemsMenu:
    """A menu whose ``add`` returns one mock per item, by objectName."""

    def __init__(self):
        self.items = {}
        self.titles = []

    def add(self, _kind, **kwargs):
        item = mock.MagicMock()
        name = kwargs.get("setObjectName")
        if name:
            self.items[name] = (item, kwargs)
        return item

    def setTitle(self, title):
        self.titles.append(title)


def _footer(ui):
    return ui.footer.setText.call_args.args[0]


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestAudioClipsPanelSetup(_PanelCase):
    def test_watches_the_scene_through_the_engine(self):
        slots, sb, ui = _panel()
        engine = sb.tk.AudioClips
        engine.watch.assert_called_once_with(
            owner=slots,
            on_scene=slots._on_scene_opened,
            on_tracks=slots._on_tracks_changed,
            on_time=slots._on_time_changed,
            widget=ui,
        )
        sb.QtCore.QTimer.singleShot.assert_called_once_with(0, slots._hydrate)

    def test_the_list_follows_the_playhead_only_where_the_engine_can_tell(self):
        """Blender's engine has no ``tracks_at``: its list stays the clip Move
        To Current Frame moves."""
        slots, sb, _ = _panel(_engine(BLENDER_API))
        self.assertIsNone(sb.tk.AudioClips.watch.call_args.kwargs["on_time"])

    def test_the_list_option_box_is_built_once_named_for_the_host(self):
        for api, noun in ((MAYA_API, "Track"), (BLENDER_API, "Clip")):
            with self.subTest(noun=noun):
                slots, sb, ui = _panel(_engine(api))
                menu = _ItemsMenu()
                ui.cmb000.option_box.menu = menu
                slots.cmb000_init(ui.cmb000)
                self.assertEqual(list(menu.items), list(TRACKS_MENU))
                self.assertEqual(
                    menu.items["btn_add_tracks"][1]["setText"], f"Add {noun}s…"
                )
                self.assertEqual(
                    menu.items["btn_rename_track"][1]["setText"], f"Rename {noun}"
                )
                ui.tracks_group.setTitle.assert_called_with(f"{noun}s")
                # Every item runs the method its objectName names, once:
                # never also connected here.
                for name, (item, _kwargs) in menu.items.items():
                    self.assertTrue(callable(getattr(slots, name)), name)
                    item.clicked.connect.assert_not_called()
                self.assertFalse(ui.cmb000.restore_state, "the list is the scene's")
                # A reloaded Slots instance on the same widget: built once,
                # the re-list handler swapped to the new instance.
                again, _, _ = _panel(sb.tk.AudioClips)
                again.ui = ui
                again.cmb000_init(ui.cmb000)
                self.assertEqual(len(menu.items), len(TRACKS_MENU))
                ui.cmb000.before_popup_shown.disconnect.assert_called_once_with(
                    slots._refresh_combo
                )
                ui.cmb000.before_popup_shown.connect.assert_called_with(
                    again._refresh_combo
                )

    def test_cleanup_unused_is_maya_only(self):
        for api, enabled in ((MAYA_API, True), (BLENDER_API, False)):
            slots, _, ui = _panel(_engine(api))
            menu = _ItemsMenu()
            ui.cmb000.option_box.menu = menu
            slots.cmb000_init(ui.cmb000)
            item = menu.items["btn_cleanup_unused"][0]
            item.setEnabled.assert_called_once_with(enabled)

    def test_the_list_fills_from_the_scene_and_keeps_the_pick(self):
        slots, sb, ui = _panel(current="snare")
        sb.tk.AudioClips.list_tracks.return_value = ["hat", "kick", "snare"]
        slots._refresh_combo()
        self.assertEqual(ui.cmb000.items, ["hat", "kick", "snare"])
        self.assertEqual(ui.cmb000.currentText(), "snare")
        ui.footer.setDefaultStatusText.assert_called_with("3 track(s) in the scene")
        sb.tk.AudioClips.list_tracks.return_value = []
        slots._refresh_combo()
        self.assertIn("No tracks", ui.footer.setDefaultStatusText.call_args.args[0])

    def test_the_header_gates_what_blender_has_no_use_for(self):
        for api, enabled in ((MAYA_API, True), (BLENDER_API, False)):
            with self.subTest(maya=enabled):
                slots, sb, _ = _panel(_engine(api))
                header = mock.MagicMock()
                header.menu = _ItemsMenu()
                slots.header_init(header)
                items = header.menu.items
                self.assertEqual(
                    list(items),
                    [
                        "chk_auto_convert",
                        "cmb_export_mode",
                        "btn_export",
                        "chk_trim_silence",
                        "chk_suffix_time_range",
                        "btn_channels",
                    ],
                )
                self.assertEqual(
                    items["cmb_export_mode"][1]["addItems"],
                    ["Composite", "Keyed Tracks", "All Tracks"],
                )
                for name, (item, _kwargs) in items.items():
                    item.setEnabled.assert_called_once_with(enabled)
                header.set_help_text.assert_called_once_with(
                    sb.tooltip.fmt.return_value
                )

    def test_the_place_option_box_is_named_and_gated_by_the_engine(self):
        maya_only = (
            "btn_sync_audio",
            "chk_auto_end_none",
            "chk_snap_frames",
            "chk_next_event",
            "chk_key_all",
        )
        for api, maya in ((MAYA_API, True), (BLENDER_API, False)):
            with self.subTest(maya=maya):
                slots, sb, ui = _panel(_engine(api))
                widget = mock.MagicMock(is_initialized=False)
                widget.option_box.menu = _ItemsMenu()
                slots.tb001_init(widget)
                engine = sb.tk.AudioClips
                widget.setText.assert_called_once_with(engine.PLACE_LABEL)
                items = widget.option_box.menu.items
                self.assertEqual(
                    items["btn_select_carrier"][1]["setText"], engine.REVEAL_LABEL
                )
                for name in maya_only:
                    items[name][0].setEnabled.assert_any_call(maya)
                # Snap To Frame is the scene's recipe, where the host has one.
                self.assertEqual(sb.ModelBinding.called, maya)
                if maya:
                    engine.watch_snap.assert_called_once_with(
                        sb.ModelBinding.return_value.refresh, widget=ui
                    )
                # Built once: a second init only relabels.
                slots.tb001_init(widget)
                self.assertEqual(widget.setText.call_count, 2)

    def test_key_all_takes_next_event_out_of_play(self):
        slots, _, _ = _panel()
        widget = mock.MagicMock(is_initialized=False)
        widget.option_box.menu = _ItemsMenu()
        slots.tb001_init(widget)
        items = widget.option_box.menu.items
        toggled = items["chk_key_all"][0].toggled.connect.call_args.args[0]
        toggled(True)
        items["chk_next_event"][0].setChecked.assert_called_with(False)
        items["chk_next_event"][0].setEnabled.assert_called_with(False)
        items["spn_stagger"][0].setEnabled.assert_called_with(True)


class TestAudioClipsPanelList(_PanelCase):
    def test_a_pick_puts_maya_tracks_on_the_time_slider(self):
        slots, sb, ui = _panel(current="snare")
        sb.tk.AudioClips.activate_track.return_value = "snare_audio"
        slots.cmb000(1)
        sb.tk.AudioClips.activate_track.assert_called_once_with("snare")
        self.assertEqual(_footer(ui), "Active: snare_audio")

    def test_a_pick_shows_a_blender_clips_trim(self):
        slots, sb, ui = _panel(_engine(BLENDER_API))
        sb.tk.AudioClips.get_trim.return_value = (3, 4)
        slots.cmb000(0)
        sb.tk.AudioClips.get_trim.assert_called_with("kick")
        ui.s000.setValue.assert_called_with(3)
        ui.s001.setValue.assert_called_with(4)

    def test_select_track_from_the_shot_manifest(self):
        slots, sb, ui = _panel()
        engine = sb.tk.AudioClips
        engine.find_track.return_value = "hat"
        engine.list_tracks.return_value = ["hat", "kick", "snare"]
        self.assertTrue(slots.select_track("Hat"))
        engine.find_track.assert_called_with("Hat")
        self.assertEqual(ui.cmb000.currentText(), "hat")
        self.assertEqual(_footer(ui), "Track 'hat'.")
        engine.find_track.return_value = None
        self.assertFalse(slots.select_track("nowhere"))
        self.assertEqual(_footer(ui), "No track 'nowhere' in this scene.")

    def test_add_takes_what_the_host_plays_and_what_ffmpeg_converts(self):
        slots, sb, ui = _panel()
        engine = sb.tk.AudioClips
        sb.file_dialog.return_value = ["C:/a/hat.wav", "C:/a/ride.mp3", "C:/a/x.doc"]
        engine.add_tracks.return_value = ["hat", "ride"]
        engine.list_tracks.return_value = ["hat", "kick", "ride", "snare"]
        with mock.patch.object(ptk.AudioUtils, "resolve_ffmpeg", return_value="ffmpeg"):
            slots.btn_add_tracks()
        engine.add_tracks.assert_called_once_with(["C:/a/hat.wav", "C:/a/ride.mp3"])
        self.assertIn("x.doc", sb.message_box.call_args.args[0])  # named, skipped
        sb.tk.CoreUtils.undo_chunk.assert_called_with("Add Audio Tracks")
        self.assertEqual(ui.cmb000.currentText(), "ride")
        self.assertEqual(_footer(ui), "Added 2 track(s).")
        # The dialog offers every format the host takes.
        types = sb.file_dialog.call_args.kwargs["file_types"]
        self.assertIn("*.mp3", types)
        self.assertIn("*.wav", types)

    def test_auto_convert_off_keeps_only_what_maya_plays(self):
        slots, sb, ui = _panel()
        ui.header.menu.chk_auto_convert.isChecked.return_value = False
        sb.file_dialog.return_value = ["C:/a/hat.wav", "C:/a/ride.mp3"]
        sb.tk.AudioClips.add_tracks.return_value = ["hat"]
        slots.btn_add_tracks()
        sb.tk.AudioClips.add_tracks.assert_called_once_with(["C:/a/hat.wav"])

    def test_blender_plays_every_offered_format_without_ffmpeg(self):
        slots, sb, _ = _panel(_engine(BLENDER_API))
        sb.file_dialog.return_value = ["C:/a/ride.mp3", "C:/a/pad.opus"]
        sb.tk.AudioClips.add_tracks.return_value = ["ride", "pad"]
        with mock.patch.object(ptk.AudioUtils, "resolve_ffmpeg") as ffmpeg:
            slots.btn_add_tracks()
        ffmpeg.assert_not_called()
        sb.tk.AudioClips.add_tracks.assert_called_once_with(
            ["C:/a/ride.mp3", "C:/a/pad.opus"]
        )

    def test_a_cancelled_dialog_adds_nothing(self):
        slots, sb, ui = _panel()
        sb.file_dialog.return_value = []
        slots.btn_add_tracks()
        sb.tk.AudioClips.add_tracks.assert_not_called()
        ui.footer.setText.assert_not_called()

    def test_rename_through_the_engine(self):
        slots, sb, ui = _panel()
        engine = sb.tk.AudioClips
        sb.input_dialog.return_value = " Kick Hard "
        engine.rename_track.return_value = "kick_hard"
        engine.list_tracks.side_effect = [["kick", "snare"], ["kick_hard", "snare"]]
        slots.btn_rename_track()
        engine.rename_track.assert_called_once_with("kick", "Kick Hard")
        self.assertEqual(ui.cmb000.currentText(), "kick_hard")
        self.assertEqual(_footer(ui), "Renamed 'kick' → 'kick_hard'.")

    def test_a_refused_rename_says_why(self):
        slots, sb, ui = _panel()
        sb.input_dialog.return_value = "snare"
        sb.tk.AudioClips.rename_track.side_effect = ValueError("the name is taken")
        slots.btn_rename_track()
        self.assertEqual(_footer(ui), "the name is taken")

    def test_replace_through_the_engine(self):
        slots, sb, ui = _panel()
        sb.file_dialog.return_value = "C:/a/kick_v2.wav"
        sb.tk.AudioClips.replace_track.return_value = "kick_v2"
        sb.tk.AudioClips.list_tracks.side_effect = [
            ["kick", "snare"],
            ["kick_v2", "snare"],
        ]
        slots.btn_replace_track()
        sb.tk.AudioClips.replace_track.assert_called_once_with(
            "kick", "C:/a/kick_v2.wav"
        )
        sb.file_dialog.assert_called_once()
        self.assertFalse(sb.file_dialog.call_args.kwargs["allow_multiple"])
        self.assertEqual(
            _footer(ui), "Replaced 'kick' with kick_v2.wav, now 'kick_v2'."
        )

    def test_a_stale_pick_is_refused_and_the_list_refreshed(self):
        slots, sb, ui = _panel()
        sb.tk.AudioClips.list_tracks.return_value = ["snare"]
        slots.btn_remove_selected()
        sb.tk.AudioClips.remove_track.assert_not_called()
        self.assertEqual(ui.cmb000.items, ["snare"])
        self.assertIn("'kick' is gone", _footer(ui))

    def test_remove_one_remove_all_and_cleanup(self):
        slots, sb, ui = _panel()
        engine = sb.tk.AudioClips
        slots.btn_remove_selected()
        engine.remove_track.assert_called_once_with("kick")
        self.assertEqual(_footer(ui), "Removed 'kick'.")
        engine.remove.return_value = 2
        slots.btn_remove_audio()
        self.assertEqual(_footer(ui), "Removed 2 track(s).")
        engine.cleanup_unused.return_value = ["snare"]
        slots.btn_cleanup_unused()
        self.assertEqual(_footer(ui), "Cleaned up 1 unused track(s).")
        for name in ("Remove Track", "Remove Audio", "Cleanup Unused Audio"):
            sb.tk.CoreUtils.undo_chunk.assert_any_call(name)


class TestAudioClipsPanelPlace(_PanelCase):
    def test_places_the_pick_at_the_playhead_in_one_undo_step(self):
        for api, label in (
            (MAYA_API, "Key Audio Event"),
            (BLENDER_API, "Move To Current Frame"),
        ):
            with self.subTest(label=label):
                slots, sb, ui = _panel(_engine(api))
                ui.tb001.option_box.menu.chk_auto_end_none.isChecked.return_value = True
                slots.tb001()
                # Blender's strips end where their sound does: no end key.
                sb.tk.AudioClips.key_track.assert_called_once_with(
                    "kick", auto_end=api is MAYA_API
                )
                sb.tk.CoreUtils.undo_chunk.assert_called_once_with(label)
                self.assertTrue(_footer(ui).startswith(f"{label}: 'kick' at frame 12"))

    def test_next_event_keys_the_engines_next_track(self):
        slots, sb, ui = _panel()
        ui.tb001.option_box.menu.chk_next_event.isChecked.return_value = True
        sb.tk.AudioClips.next_track.return_value = "snare"
        slots.tb001()
        sb.tk.AudioClips.key_track.assert_called_once_with("snare", auto_end=False)
        self.assertEqual(ui.cmb000.currentText(), "snare")

    def test_key_all_lays_every_track_out(self):
        slots, sb, ui = _panel()
        menu = ui.tb001.option_box.menu
        menu.chk_key_all.isChecked.return_value = True
        menu.spn_stagger.value.return_value = 4
        sb.tk.AudioClips.key_all.return_value = ["kick", "snare"]
        slots.tb001()
        sb.tk.AudioClips.key_all.assert_called_once_with(auto_end=False, stagger=4)
        sb.tk.AudioClips.key_track.assert_not_called()
        self.assertEqual(_footer(ui), "Key All: 2 track(s), stagger 4.")

    def test_blender_ignores_the_maya_keying_options(self):
        """Saved Maya state on a disabled control never reaches Blender's engine."""
        slots, sb, ui = _panel(_engine(BLENDER_API))
        menu = ui.tb001.option_box.menu
        menu.chk_key_all.isChecked.return_value = True
        menu.chk_next_event.isChecked.return_value = True
        slots.tb001()
        sb.tk.AudioClips.key_track.assert_called_once_with("kick", auto_end=False)

    def test_nothing_to_place(self):
        slots, sb, ui = _panel(_engine(tracks=()))
        slots.tb001()
        sb.tk.AudioClips.key_track.assert_not_called()
        self.assertEqual(_footer(ui), "No tracks — add audio files first.")

    def test_reveal_names_what_it_selected(self):
        slots, sb, ui = _panel()
        sb.tk.AudioClips.reveal.return_value = "data_internal"
        slots.btn_select_carrier()
        sb.tk.AudioClips.reveal.assert_called_once_with("kick")
        self.assertEqual(_footer(ui), "Selected 'data_internal'.")
        sb.tk.AudioClips.reveal.side_effect = ValueError("Select a clip first.")
        slots.btn_select_carrier()
        self.assertEqual(_footer(ui), "Select a clip first.")

    def test_sync_reports_the_composite(self):
        slots, sb, ui = _panel()
        sb.tk.AudioClips.sync.return_value = {
            "created": ["a"],
            "updated": [],
            "deleted": [],
            "composite": "audio_composite",
        }
        slots.btn_sync_audio()
        self.assertEqual(
            _footer(ui), "Synced 1 sound node change(s); composite rebuilt."
        )


class TestAudioClipsPanelBlenderOnly(_PanelCase):
    def test_trim_and_range_are_gated_off_in_maya(self):
        for api, enabled in ((MAYA_API, False), (BLENDER_API, True)):
            slots, sb, _ = _panel(_engine(api))
            for name in ("s000", "s001", "b003"):
                widget = mock.MagicMock()
                getattr(slots, f"{name}_init")(widget)
                widget.setEnabled.assert_called_once_with(enabled)
            b004 = mock.MagicMock(is_initialized=False)
            b004.option_box.menu = _ItemsMenu()
            slots.b004_init(b004)
            b004.setEnabled.assert_called_once_with(enabled)
            self.assertEqual(
                b004.option_box.menu.items["cmb_fit"][1]["addItems"],
                ["Extend Only", "Exact Fit"],
            )

    def test_the_trim_fields_mirror_the_clip_never_a_saved_value(self):
        slots, _, _ = _panel(_engine(BLENDER_API))
        for name in ("s000", "s001"):
            widget = mock.MagicMock()
            getattr(slots, f"{name}_init")(widget)
            self.assertFalse(widget.restore_state, name)

    def test_apply_trim_and_fit_the_range(self):
        slots, sb, ui = _panel(_engine(BLENDER_API))
        engine = sb.tk.AudioClips
        ui.s000.value.return_value = 2.0
        ui.s001.value.return_value = 5.0
        engine.trim_track.return_value = 17
        slots.b003()
        engine.trim_track.assert_called_once_with("kick", start=2, end=5)
        self.assertEqual(_footer(ui), "Trimmed 'kick' — 17 frame(s) play.")
        engine.sync_scene_range.return_value = (1, 90)
        ui.b004.option_box.menu.cmb_fit.currentIndex.return_value = 1
        slots.b004()
        engine.sync_scene_range.assert_called_once_with(extend_only=False)
        self.assertEqual(_footer(ui), "Scene range synced to the clips: 1-90.")


class TestAudioClipsPanelMayaOnly(_PanelCase):
    def test_export_by_mode(self):
        slots, sb, ui = _panel()
        engine = sb.tk.AudioClips
        menu = ui.header.menu
        menu.cmb_export_mode.currentIndex.return_value = 0
        menu.chk_trim_silence.isChecked.return_value = True
        engine.export_composite.return_value = ("C:/out/mix.wav", False)
        slots.btn_export()
        self.assertTrue(engine.export_composite.call_args.kwargs["trim_silence"])
        self.assertEqual(_footer(ui), "Exported composite → mix.wav (trim failed)")
        # The engine asks the panel's dialog where to write.
        chooser = engine.export_composite.call_args.args[0]
        chooser("C:/proj/sound/audio_composite.wav")
        self.assertEqual(
            sb.save_file_dialog.call_args.kwargs["start_dir"],
            "C:/proj/sound/audio_composite.wav",
        )
        menu.cmb_export_mode.currentIndex.return_value = 1
        menu.chk_suffix_time_range.isChecked.return_value = True
        engine.export_tracks.return_value = (3, ["hat"], "C:/out/clips")
        slots.btn_export()
        engine.export_tracks.assert_called_once()
        self.assertEqual(
            engine.export_tracks.call_args.kwargs,
            {"keyed_only": True, "suffix_range": True},
        )
        self.assertEqual(_footer(ui), "Exported 3 file(s) → clips (1 failed)")
        engine.export_tracks.side_effect = ValueError(
            "No keyed tracks — nothing to export."
        )
        slots.btn_export()
        self.assertEqual(_footer(ui), "No keyed tracks — nothing to export.")

    def test_channels_opens_on_the_engines_config(self):
        slots, sb, _ = _panel()
        config = {"targets": ["data_internal"], "filter": "Custom", "search": "a*"}
        sb.tk.AudioClips.channels_config.return_value = config
        slots.btn_channels()
        sb.handlers.marking_menu.show.assert_called_once_with("channels")
        sb.get_slots_instance.return_value.apply_launch_config.assert_called_once_with(
            **config
        )

    def test_the_list_follows_the_playhead(self):
        slots, sb, ui = _panel()
        sb.tk.AudioClips.tracks_at.return_value = ["snare"]
        slots._on_time_changed(30.0)
        sb.tk.AudioClips.tracks_at.assert_called_once_with(30.0)
        self.assertEqual(ui.cmb000.currentText(), "snare")
        sb.tk.AudioClips.tracks_at.return_value = []
        slots._on_time_changed(90.0)
        self.assertEqual(ui.cmb000.currentText(), "")

    def test_edits_elsewhere_resync_maya_and_relist_both(self):
        for api, syncs in ((MAYA_API, True), (BLENDER_API, False)):
            slots, sb, ui = _panel(_engine(api))
            sb.tk.AudioClips.list_tracks.return_value = ["kick", "snare", "tom"]
            slots._on_tracks_changed()
            self.assertEqual(ui.cmb000.items, ["kick", "snare", "tom"])
            if syncs:
                sb.tk.AudioClips.sync.assert_called_once_with()

    def test_a_scene_opening_rehydrates_and_offers_legacy_data_once(self):
        slots, sb, ui = _panel()
        engine = sb.tk.AudioClips
        engine.has_legacy_data.return_value = True
        engine.migrate_legacy.return_value = ["kick"]
        sb.message_box.return_value = "Yes"
        slots._on_scene_opened()
        engine.migrate_legacy.assert_called_once_with()
        engine.attach_composite.assert_called_once_with()
        self.assertEqual(_footer(ui), "Migrated 1 legacy track(s).")
        slots._hydrate()  # same scene: not offered again
        engine.migrate_legacy.assert_called_once_with()
        slots._on_scene_opened()
        self.assertEqual(engine.migrate_legacy.call_count, 2)

    def test_blender_hydrates_without_maya_machinery(self):
        slots, sb, ui = _panel(_engine(BLENDER_API))
        slots._hydrate()  # no has_legacy_data / attach_composite to call
        self.assertEqual(ui.cmb000.items, ["kick", "snare"])
        sb.message_box.assert_not_called()


class TestAudioClipsPanelUi(unittest.TestCase):
    """The ``.ui``: every saved name kept, the panel's widgets declared."""

    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(UI_PATH).getroot()
        cls.widgets = {w.get("name"): w for w in cls.root.iter("widget")}

    def test_every_name_mayatk_saved_is_kept(self):
        for name in (
            "header",
            "tracks_group",
            "cmb000",
            "key_group",
            "tb001",
            "footer",
        ):
            self.assertIn(name, self.widgets, name)

    def test_blenders_trim_and_range_are_kept_under_their_names(self):
        for name in ("trim_group", "s000", "s001", "b003", "range_group", "b004"):
            self.assertIn(name, self.widgets, name)

    def test_the_header_names_the_tool(self):
        text = self.widgets["header"].find("property[@name='text']/string").text
        self.assertEqual(text, "AUDIO CLIPS")
        header = next(
            c for c in self.root.iter("customwidget") if c.findtext("class") == "Header"
        )
        self.assertEqual(header.findtext("extends"), "QLabel")
        self.assertEqual(header.findtext("header"), "uitk.widgets.header.Header.h")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestAudioClipsPanelInMaya(_PanelCase):
    """The panel over the real ``mtk.AudioClips`` and a real scene (the widgets
    stay mocks; the list is a ``_Combo`` and file dialogs answer as given)."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.tmp = ptk.TempArtifacts(prefix="tcl_audio_clips_")
        self.addCleanup(self.tmp.cleanup, force=True)
        self.slots, self.sb, self.ui = _panel(tk=self.mtk)
        self.addCleanup(
            self.mtk.ScriptJobManager.instance().unsubscribe_all, self.slots
        )

    def _wav(self, stem, seconds=0.5):
        path = os.path.join(self.tmp.dir_path(name="wav"), f"{stem}.wav").replace(
            "\\", "/"
        )
        with wave.open(path, "wb") as fh:
            fh.setnchannels(1)
            fh.setsampwidth(2)
            fh.setframerate(22050)
            fh.writeframes(b"\x00\x00" * int(22050 * seconds))
        return path

    def _add(self, *stems):
        self.sb.file_dialog.return_value = [self._wav(s) for s in stems]
        self.slots.btn_add_tracks()
        return self.ui.cmb000.items

    def test_the_engine_carries_the_panels_vocabulary(self):
        missing = [n for n in MAYA_API if not hasattr(self.mtk.AudioClips, n)]
        self.assertEqual(missing, [])

    def test_add_then_key_at_the_playhead(self):
        self.assertEqual(self._add("kick", "snare"), ["kick", "snare"])
        self.ui.cmb000.setCurrentIndex(1)
        self.cmds.currentTime(24)
        self.slots.tb001()
        self.assertEqual(
            self.mtk.AudioUtils.read_keys("snare"), [(24.0, 1.0)], _footer(self.ui)
        )
        self.assertIn("Key Audio Event: 'snare' at frame 24", _footer(self.ui))

    def test_rename_and_remove(self):
        self._add("kick", "snare")
        self.ui.cmb000.setCurrentIndex(0)
        self.sb.input_dialog.return_value = "Kick Hard"
        self.slots.btn_rename_track()
        self.assertEqual(self.mtk.AudioUtils.list_tracks(), ["kick_hard", "snare"])
        self.assertEqual(self.ui.cmb000.currentText(), "kick_hard")
        self.slots.btn_remove_selected()
        self.assertEqual(self.mtk.AudioUtils.list_tracks(), ["snare"])
        self.slots.btn_remove_audio()
        self.assertEqual(self.mtk.AudioUtils.list_tracks(), [])
        self.assertEqual(self.ui.cmb000.items, [])

    def test_select_track_and_reveal(self):
        self._add("kick", "snare")
        self.assertTrue(self.slots.select_track("Snare"))
        self.assertEqual(self.ui.cmb000.currentText(), "snare")
        self.slots.btn_select_carrier()
        carrier = self.mtk.AudioUtils.CARRIER_NODE
        self.assertEqual(self.cmds.ls(selection=True), [carrier])

    def test_cleanup_keeps_the_keyed_track(self):
        self._add("kick", "snare")
        self.slots.tb001()  # keys the pick: the last track added
        keyed = [t for t in ("kick", "snare") if self.mtk.AudioUtils.read_keys(t)]
        self.slots.btn_cleanup_unused()
        self.assertEqual(self.mtk.AudioUtils.list_tracks(), keyed)


if __name__ == "__main__":
    unittest.main()
