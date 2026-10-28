# !/usr/bin/python
# coding=utf-8
"""Audio Clips: the scene's audio files, placed on the timeline.

One Slots class for both hosts over the host library's ``AudioClips``
(``self.tk``), which owns how each host models audio: Maya keys tracks on a
carrier node and mixes them into one composite WAV for the Time Slider;
Blender's are Sequencer sound strips that play on their own. The panel words
its controls from the engine (``ITEM_NOUN``, ``PLACE_LABEL``,
``REVEAL_LABEL``) and disables a control whose operation its host's engine
does not have -- each gate names the host and why
(``tentacle/docs/parity_map.py``'s ``audio_clips_slots`` row has the full
reasons).
"""

import html
import logging
import os
from typing import Optional

import pythontk as ptk

from tentacle import Slots

_log = logging.getLogger(__name__)


class AudioClipsSlots(Slots):
    """Switchboard slots for the ``audio_clips.ui`` panel.

    Layout
    ------
    - **Header**: Auto Convert; the Export section; Channels; help.
    - **List** (``cmb000``): every track or clip in the scene. Its option box
      adds, renames, replaces and removes them.
    - **Place** (``tb001``): the engine's place action at the playhead (Maya:
      Key Audio Event; Blender: Move To Current Frame); its option box reveals
      the selection and holds Maya's keying options.
    - **Trim** (``s000``, ``s001``, ``b003``) and **Range** (``b004``): Blender's
      strip trim and scene-range fit.
    - **Footer**: the list's count; an action's report.
    """

    #: The header Export combo's modes, in its order (it saves its index).
    EXPORT_MODES = ("Composite", "Keyed Tracks", "All Tracks")
    #: Sync Scene Range's fit modes, in its combo's order (it saves its index).
    FIT_MODES = ("Extend Only", "Exact Fit")

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.audio_clips
        self.engine = self.tk.AudioClips
        self._syncing_combo = False  # the list is being refilled in code
        self._playing = None  # the track the list last followed to
        self._legacy_offered = False  # once per scene
        self._last_dir = ""  # where the last file dialog picked from
        # The list follows the playhead where the engine can say what plays
        # there. Blender's cannot (no ``tracks_at``) by design: its list picks
        # the clip Move To Current Frame moves, which following the playhead
        # would swap while scrubbing, and the Sequencer shows what plays.
        follows = getattr(self.engine, "tracks_at", None) is not None
        self.engine.watch(
            owner=self,
            on_scene=self._on_scene_opened,
            on_tracks=self._on_tracks_changed,
            on_time=self._on_time_changed if follows else None,
            widget=self.ui,
        )
        # Once the window shows: the scene's older audio data, Maya's composite.
        self.sb.QtCore.QTimer.singleShot(0, self._hydrate)

    # ------------------------------------------------------------------
    # Engine wording and capability
    # ------------------------------------------------------------------

    @property
    def noun(self) -> str:
        """One entry, capitalized: ``"Track"`` (Maya) or ``"Clip"`` (Blender)."""
        return self.engine.ITEM_NOUN

    def _has(self, operation: str) -> bool:
        """Whether this host's engine has *operation*. Every caller says which
        host lacks it and why."""
        return getattr(self.engine, operation, None) is not None

    def _gate(self, widget, operation: str):
        """Disable *widget* when the engine lacks *operation*; returns it."""
        widget.setEnabled(self._has(operation))
        return widget

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def header_init(self, widget) -> None:
        """The header menu: import, export and inspect options; help."""
        menu = widget.menu
        menu.add("Separator", setTitle="Import")
        convert = menu.add(
            "QCheckBox",
            setText="Auto Convert",
            setObjectName="chk_auto_convert",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Auto Convert",
                bullets=[
                    "<b>On:</b> Audio the host cannot play as it is (Maya: MP3, "
                    "OGG, M4A, FLAC) is accepted and converted to WAV with FFmpeg.",
                    "<b>Off:</b> Only formats the host plays are accepted; the "
                    "rest are skipped.",
                ],
            ),
        )
        # Blender: its media backend decodes every format the dialog offers,
        # so nothing is ever converted (parity_map: chk_auto_convert).
        convert.setEnabled(bool(self._convertible()))

        menu.add("Separator", setTitle="Export")
        export = [
            menu.add(
                "QComboBox",
                setObjectName="cmb_export_mode",
                addItems=list(self.EXPORT_MODES),
                setToolTip=self.sb.tooltip.fmt(
                    title="Export Mode",
                    bullets=[
                        "<b>Composite</b> — one mixed WAV of every keyed track.",
                        "<b>Keyed Tracks</b> — each keyed track's source file.",
                        "<b>All Tracks</b> — every loaded track's source file.",
                    ],
                ),
            ),
            menu.add(
                "QPushButton",
                setText="Export",
                setObjectName="btn_export",
                setToolTip="Export the audio in the mode above.",
            ),
            menu.add(
                "QCheckBox",
                setText="Trim Silence",
                setObjectName="chk_trim_silence",
                setChecked=True,
                setToolTip="Composite: trim the exported WAV's leading and "
                "trailing silence.",
            ),
            menu.add(
                "QCheckBox",
                setText="Suffix Time Range",
                setObjectName="chk_suffix_time_range",
                setChecked=False,
                setToolTip=self.sb.tooltip.fmt(
                    body="Keyed Tracks: append each keying's frame range to "
                    "the file name.",
                    rows=[("Example", "Footstep_12-47.wav")],
                ),
            ),
        ]
        # Blender: a strip already IS the audio file, in the .blend and on
        # disk; there is no composite or keyed export (parity_map: cmb_export_mode).
        for item in export:
            self._gate(item, "export_composite")

        menu.add("Separator", setTitle="Inspect")
        # Blender: a strip has no carrier node or hidden attributes to pin; its
        # properties show in the Sequencer's sidebar (parity_map: btn_channels).
        self._gate(
            menu.add(
                "QPushButton",
                setText="Channels",
                setObjectName="btn_channels",
                setToolTip="Open the Channels panel pinned to the audio carrier "
                "node, filtered to its track attributes.",
            ),
            "channels_config",
        )

        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Audio Clips",
                body="The scene's audio files, placed on the timeline. Maya keys "
                "<b>tracks</b> on a carrier node and mixes them into one "
                "composite WAV for Time-Slider scrubbing; Blender's are "
                "<b>clips</b>, Sequencer sound strips that play as they are.",
                steps=[
                    "<b>Add…</b> in the list's option box (▸) browses for audio "
                    "files (Maya: a file's stem names its track, and re-adding a "
                    "stem swaps its file and keeps its keys; Blender: each file "
                    "becomes a clip at the current frame).",
                    "Select one in the list and move the playhead to where it "
                    "should start.",
                    "Press the button under the list: <b>Key Audio Event</b> "
                    "keys the track on there (Maya; a track can play many "
                    "times), <b>Move To Current Frame</b> moves the clip there "
                    "(Blender).",
                ],
                sections=[
                    (
                        "Its option box (▸)",
                        [
                            "<b>Select Carrier Node</b> / <b>Reveal In "
                            "Sequencer</b> — show where the audio lives.",
                            "Maya: <b>Sync Audio to Timeline</b> rebuilds the "
                            "composite after keys change elsewhere; <b>Auto End "
                            "None</b> keys the track off where its file ends; "
                            "<b>Next Event</b> keys the next track; <b>Key "
                            "All</b> lays every track end to end.",
                        ],
                    ),
                    (
                        "Blender",
                        [
                            "<b>Trim</b> shaves frames off the selected clip's "
                            "ends; <b>Sync Scene Range</b> fits the frame range "
                            "to the clips.",
                        ],
                    ),
                ],
                notes=[
                    "A control the host has no use for is disabled there: "
                    "Blender's Sequencer plays and decodes every clip itself, "
                    "and a Maya track has no trim.",
                ],
            )
        )

    def btn_export(self) -> None:
        """Export the audio in the header's Export mode (Maya)."""
        menu = self.ui.header.menu
        mode = self.EXPORT_MODES[max(0, menu.cmb_export_mode.currentIndex())]
        try:
            if mode == "Composite":
                self._export_composite(menu.chk_trim_silence.isChecked())
            else:
                self._export_tracks(
                    keyed_only=mode == "Keyed Tracks",
                    suffix_range=menu.chk_suffix_time_range.isChecked(),
                )
        except ValueError as error:
            self._footer(str(error))
        except OSError as error:
            self._footer(f"Export failed: {error}")

    def _export_composite(self, trim_silence: bool) -> None:
        dest, trimmed = self.engine.export_composite(
            lambda start: self.sb.save_file_dialog(
                file_types=["*.wav"],
                title="Export Composite WAV",
                start_dir=start,
                filter_description="WAV Files",
            ),
            trim_silence=trim_silence,
        )
        if dest:
            failed = " (trim failed)" if trim_silence and not trimmed else ""
            self._footer(f"Exported composite → {os.path.basename(dest)}{failed}")

    def _export_tracks(self, keyed_only: bool, suffix_range: bool) -> None:
        exported, failed, folder = self.engine.export_tracks(
            lambda start: self.sb.dir_dialog(title="Export Audio", start_dir=start),
            keyed_only=keyed_only,
            suffix_range=suffix_range,
        )
        if folder:
            tail = f" ({len(failed)} failed)" if failed else ""
            self._footer(
                f"Exported {exported} file(s) → {os.path.basename(folder)}{tail}"
            )

    def btn_channels(self) -> None:
        """Open the Channels panel on the tracks' carrier (Maya)."""
        try:
            config = self.engine.channels_config()
        except ValueError as error:
            self.sb.message_box(str(error))
            return
        ui = self.sb.handlers.marking_menu.show("channels")
        slots = self.sb.get_slots_instance(ui)
        if slots is not None and hasattr(slots, "apply_launch_config"):
            slots.apply_launch_config(**config)

    # ------------------------------------------------------------------
    # The list
    # ------------------------------------------------------------------

    def cmb000_init(self, widget) -> None:
        """The list's option box: add, rename, replace and remove."""
        noun = self.noun
        self.ui.tracks_group.setTitle(f"{noun}s")
        # The list IS the scene's audio: a saved index would pick some entry
        # on open (and in Maya put its sound on the Time Slider).
        self.mirror_app_state(widget)
        menu = widget.option_box.menu
        # The option box outlives a reloaded Slots instance: build it once.
        if not getattr(widget, "is_initialized", False):
            widget.is_initialized = True
            menu.setTitle(f"{noun}s")
            # Each item runs the method its objectName names (Menu.add
            # registers it with the window), so none is also connected here.
            for name, text, tip in (
                (
                    "btn_add_tracks",
                    f"Add {noun}s…",
                    "Browse for audio files to add (Maya: re-adding a file of "
                    "the same stem swaps its file and keeps its keys; Blender: "
                    "each becomes a clip at the current frame).",
                ),
                (
                    "btn_rename_track",
                    f"Rename {noun}",
                    f"Rename the selected {noun.lower()}; its keys or placement stay.",
                ),
                (
                    "btn_replace_track",
                    f"Replace {noun}",
                    f"Point the selected {noun.lower()} at another audio file, "
                    "keeping its keys or placement (Maya: the track takes the "
                    "new file's name).",
                ),
                (
                    "btn_remove_selected",
                    f"Remove {noun}",
                    f"Delete the selected {noun.lower()}.",
                ),
                (
                    "btn_cleanup_unused",
                    "Cleanup Unused",
                    "Delete every track that holds no key, with its sound node.",
                ),
                (
                    "btn_remove_audio",
                    "Remove Audio",
                    f"Delete every {noun.lower()} in the scene (Maya: their "
                    "sound nodes and the composite too).",
                ),
            ):
                item = menu.add(
                    "QPushButton", setText=text, setObjectName=name, setToolTip=tip
                )
                if name == "btn_cleanup_unused":
                    # Blender: a strip is placed the moment it is added, so
                    # none is ever unkeyed (parity_map: btn_cleanup_unused).
                    self._gate(item, "cleanup_unused")
        self._rebind(widget, "before_popup_shown", self._refresh_combo)
        self._refresh_combo()

    @staticmethod
    def _rebind(widget, signal_name: str, handler) -> None:
        """Connect *handler* to *widget*'s signal, replacing the one a previous
        Slots instance connected (the widget outlives a reload)."""
        signal = getattr(widget, signal_name)
        bound = getattr(widget, "_audio_clips_handlers", {})
        prior = bound.get(signal_name)
        if prior is not None:
            try:
                signal.disconnect(prior)
            except (TypeError, RuntimeError):
                pass  # already gone with its receiver
        signal.connect(handler)
        bound[signal_name] = handler
        widget._audio_clips_handlers = bound

    def cmb000(self, index, widget=None) -> None:
        """A pick: Maya puts the track's sound on the Time Slider."""
        if self._syncing_combo:
            return
        self._sync_trim()
        track = self.ui.cmb000.currentText()
        # Blender: the Sequencer plays every strip; there is no one sound to
        # make active.
        if not track or not self._has("activate_track"):
            return
        node = self.engine.activate_track(track)
        self._footer(
            f"Active: {node}"
            if node
            else f"No sound node for '{track}' — sync to create it."
        )

    def _refresh_combo(self, *_args) -> None:
        """Re-list the scene's tracks, keeping the selected one."""
        cmb = self.ui.cmb000
        current = cmb.currentText()
        tracks = list(self.engine.list_tracks())
        syncing, self._syncing_combo = self._syncing_combo, True
        blocked = cmb.blockSignals(True)
        try:
            cmb.clear()
            cmb.addItems(tracks)
            if current in tracks:
                cmb.setCurrentIndex(cmb.findText(current))
        finally:
            cmb.blockSignals(blocked)
            self._syncing_combo = syncing
        noun = self.noun.lower()
        self.ui.footer.setDefaultStatusText(
            f"{len(tracks)} {noun}(s) in the scene"
            if tracks
            else f"No {noun}s — add audio files from the list's option box."
        )
        self._sync_trim()

    def _select(self, track: str) -> None:
        """Show *track* in the list (listed or not yet)."""
        cmb = self.ui.cmb000
        index = cmb.findText(track)
        if index < 0:
            self._refresh_combo()
            index = cmb.findText(track)
        if index >= 0:
            cmb.setCurrentIndex(index)

    def _selected_track(self) -> Optional[str]:
        """The list's track while it still exists in the scene; otherwise says
        why (re-listing a stale list) and returns ``None``."""
        track = self.ui.cmb000.currentText()
        if not track:
            self._footer(f"Select a {self.noun.lower()} first.")
            return None
        if track not in self.engine.list_tracks():
            self._refresh_combo()
            self._footer(f"'{track}' is gone from the scene; the list is refreshed.")
            return None
        return track

    def select_track(self, name: str) -> bool:
        """Show the track or clip answering to *name* -- the Shot Manifest's
        "Open in Audio Clips"; False when none does."""
        track = self.engine.find_track(name)
        if track is None:
            self._footer(f"No {self.noun.lower()} '{name}' in this scene.")
            return False
        self._select(track)
        self._footer(f"{self.noun} '{track}'.")
        return True

    # ------------------------------------------------------------------
    # The list's option box
    # ------------------------------------------------------------------

    def btn_add_tracks(self) -> None:
        """Browse for audio files and add them."""
        paths = self._pick_files(f"Add Audio {self.noun}s", multiple=True)
        accepted = self._prepare_paths(paths)
        if not accepted:
            if paths:
                self._footer("No audio files to add.")
            return
        with self.tk.CoreUtils.undo_chunk(f"Add Audio {self.noun}s"):
            added = self.engine.add_tracks(accepted)
        self._refresh_combo()
        noun = self.noun.lower()
        if not added:
            self._footer(f"No {noun}s added (the log says why).")
            return
        self._select(added[-1])
        failed = len(accepted) - len(added)
        tail = f" ({failed} failed)" if failed > 0 else ""
        self._footer(f"Added {len(added)} {noun}(s){tail}.")

    def btn_rename_track(self) -> None:
        """Rename the selected track or clip."""
        track = self._selected_track()
        if track is None:
            return
        new_name = self.sb.input_dialog(
            title=f"Rename {self.noun}",
            label=f"Rename '{track}' to:",
            text=track,
            parent=self.ui,
            placeholder="e.g. footstep_left",
            validate=lambda t: bool(t.strip()) and t.strip() != track,
            error_text="Name cannot be empty or unchanged.",
        )
        if not new_name:
            return
        try:
            with self.tk.CoreUtils.undo_chunk(f"Rename {self.noun}"):
                renamed = self.engine.rename_track(track, new_name.strip())
        except ValueError as error:
            self._footer(str(error))
            return
        self._select(renamed)
        self._footer(f"Renamed '{track}' → '{renamed}'.")

    def btn_replace_track(self) -> None:
        """Point the selected track or clip at another audio file."""
        track = self._selected_track()
        if track is None:
            return
        paths = self._prepare_paths(
            self._pick_files(f"Replace {self.noun} Audio", multiple=False)
        )
        if not paths:
            return
        try:
            with self.tk.CoreUtils.undo_chunk(f"Replace {self.noun}"):
                replaced = self.engine.replace_track(track, paths[0])
        except (ValueError, OSError) as error:
            self._footer(str(error))
            return
        self._select(replaced)
        renamed = f", now '{replaced}'" if replaced != track else ""
        self._footer(f"Replaced '{track}' with {os.path.basename(paths[0])}{renamed}.")

    def btn_remove_selected(self) -> None:
        """Delete the selected track or clip."""
        track = self._selected_track()
        if track is None:
            return
        with self.tk.CoreUtils.undo_chunk(f"Remove {self.noun}"):
            self.engine.remove_track(track)
        self._refresh_combo()
        self._footer(f"Removed '{track}'.")

    def btn_cleanup_unused(self) -> None:
        """Delete every track that holds no key (Maya)."""
        with self.tk.CoreUtils.undo_chunk("Cleanup Unused Audio"):
            removed = self.engine.cleanup_unused()
        self._refresh_combo()
        self._footer(
            f"Cleaned up {len(removed)} unused track(s)."
            if removed
            else "All tracks are keyed — nothing to clean up."
        )

    def btn_remove_audio(self) -> None:
        """Delete every track or clip in the scene."""
        with self.tk.CoreUtils.undo_chunk("Remove Audio"):
            count = self.engine.remove()
        self._refresh_combo()
        noun = self.noun.lower()
        self._footer(f"Removed {count} {noun}(s)." if count else "Nothing to remove.")

    def _pick_files(self, title: str, multiple: bool) -> list:
        """Audio files from a dialog, ``[]`` when cancelled."""
        picked = self.sb.file_dialog(
            file_types=self._file_types(),
            title=title,
            start_dir=self._last_dir,
            filter_description="Audio Files",
            allow_multiple=multiple,
        )
        paths = [picked] if isinstance(picked, str) else list(picked or [])
        if paths:
            self._last_dir = os.path.dirname(paths[0])
        return paths

    def _file_types(self) -> list:
        """Every format this host takes: what it plays, plus what FFmpeg converts."""
        accepted = set(self.engine.PLAYABLE_EXTENSIONS)
        accepted |= set(ptk.AudioUtils.SOURCE_EXTENSIONS)
        return [f"*{ext}" for ext in sorted(accepted)]

    def _convertible(self) -> set:
        """The source formats this host plays only once converted to WAV."""
        return set(ptk.AudioUtils.SOURCE_EXTENSIONS) - set(
            self.engine.PLAYABLE_EXTENSIONS
        )

    def _prepare_paths(self, paths) -> list:
        """*paths* this host can take: what it plays, plus -- with Auto
        Convert, once FFmpeg is found or installed -- what converts to WAV.
        Anything else is named and skipped."""
        playable, convertible, unsupported = [], [], []
        playable_ext = set(self.engine.PLAYABLE_EXTENSIONS)
        convertible_ext = self._convertible()
        for path in paths or ():
            ext = os.path.splitext(path)[1].lower()
            if ext in playable_ext:
                playable.append(path)
            elif ext in convertible_ext:
                convertible.append(path)
            else:
                unsupported.append(path)
        if unsupported:
            names = "<br>".join(
                html.escape(os.path.basename(p)) for p in unsupported[:8]
            )
            self.sb.message_box(
                f"<strong>Unsupported audio</strong>.<br>Skipped:<br>{names}"
            )
        if not convertible or not self.ui.header.menu.chk_auto_convert.isChecked():
            return playable
        if not ptk.AudioUtils.resolve_ffmpeg(required=False):
            answer = self.sb.message_box(
                "<strong>FFmpeg not found</strong>.<br>It converts these files to "
                "WAV. Download and install it now? (The first download takes a "
                "moment.)",
                "Yes",
                "No",
            )
            if answer != "Yes":
                return playable
            self._footer("Downloading FFmpeg …")
            self.sb.QtWidgets.QApplication.processEvents()
            installed = ptk.AudioUtils.resolve_ffmpeg(required=False, auto_install=True)
            self._footer("")
            if not installed:
                self.sb.message_box(
                    "<strong>Install failed</strong>.<br>FFmpeg could not be "
                    "installed automatically: install it and put it on the PATH."
                )
                return playable
        return playable + convertible

    # ------------------------------------------------------------------
    # Place
    # ------------------------------------------------------------------

    def tb001_init(self, widget) -> None:
        """The place action's label, and its option box."""
        widget.setText(self.engine.PLACE_LABEL)
        if getattr(widget, "is_initialized", False):
            return
        widget.is_initialized = True
        menu = widget.option_box.menu
        menu.setTitle(self.engine.PLACE_LABEL)
        menu.add(
            "QPushButton",
            setText=self.engine.REVEAL_LABEL,
            setObjectName="btn_select_carrier",
            setToolTip="Show where the audio lives (Maya: selects the carrier "
            "node, its track attributes in the Channel Box; Blender: selects "
            "the clip in the Sequencer and frames it).",
        )
        # Blender: no composite to rebuild; the Sequencer plays the strips as
        # they are (Sync Scene Range, its old pair, is a different action).
        self._gate(
            menu.add(
                "QPushButton",
                setText="Sync Audio to Timeline",
                setObjectName="btn_sync_audio",
                setToolTip="Re-derive the sound nodes and rebuild the composite "
                "WAV from the tracks and their keys -- after keys are edited "
                "elsewhere.",
            ),
            "sync",
        )
        auto_end = menu.add(
            "QCheckBox",
            setText="Auto End None",
            setObjectName="chk_auto_end_none",
            setToolTip="Also key the track off where its file ends (start + "
            "length), which the Graph Editor and the Shot Sequencer read as the "
            "clip's end.",
        )
        # Blender: a strip's end is intrinsic; there is no end key to write
        # (parity_map: chk_auto_end_none).
        auto_end.setEnabled(bool(self.engine.END_KEYS))
        snap = menu.add(
            "QCheckBox",
            setText="Snap To Frame",
            setObjectName="chk_snap_frames",
            setToolTip="Round audio keys to whole frames. The scene's effect "
            "recipe: this panel and the Shot Manifest's build key by it.",
        )
        # Blender: a strip's start and handles are whole frames already
        # (parity_map: chk_snap_frames).
        self._gate(snap, "set_snap_frames")
        if self._has("set_snap_frames"):
            self._bind_snap(snap)
        next_event = self._gate(
            menu.add(
                "QCheckBox",
                setText="Next Event",
                setObjectName="chk_next_event",
                setToolTip=self.sb.tooltip.fmt(
                    title="Next Event",
                    body="Key the next track instead of the selected one; the "
                    "list follows.",
                    bullets=[
                        "The track after the most recently started one, wrapping.",
                        "The first track when nothing is keyed yet.",
                    ],
                ),
            ),
            # Blender: a clip is placed when added; there is no queue of
            # unplaced ones to advance through (parity_map: chk_next_event).
            "next_track",
        )
        key_all = self._gate(
            menu.add(
                "QCheckBox",
                setText="Key All",
                setObjectName="chk_key_all",
                setToolTip="Key every track once, end to end from the playhead: "
                "each starts where the last one's file ended plus the stagger.",
            ),
            # Blender: the Sequencer plays strips side by side; nothing needs
            # laying out (parity_map: chk_key_all, spn_stagger).
            "key_all",
        )
        stagger = menu.add(
            "QSpinBox",
            setObjectName="spn_stagger",
            setPrefix="Stagger: ",
            setSuffix=" fr",
            setMinimum=0,
            setMaximum=9999,
            setValue=0,
            setToolTip="Frames between tracks under Key All.",
        )
        can_key_all, can_advance = self._has("key_all"), self._has("next_track")

        def key_all_toggled(checked):
            stagger.setEnabled(can_key_all and checked)
            if checked:
                next_event.setChecked(False)
            next_event.setEnabled(can_advance and not checked)

        key_all.toggled.connect(key_all_toggled)
        key_all_toggled(can_key_all and key_all.isChecked())

    def _bind_snap(self, checkbox) -> None:
        """Show Snap To Frame from the scene's recipe (also after another panel
        or an opened scene changes it) and write it there on toggle -- never
        restored from this panel's settings over the scene's value."""
        binding = self.sb.ModelBinding(
            read=lambda: {"audio_snap": self.engine.get_snap_frames()},
            write=self._write_snap,
        )
        binding.bind("audio_snap", checkbox)
        binding.refresh()
        self.engine.watch_snap(binding.refresh, widget=self.ui)

    def _write_snap(self, _field, value) -> None:
        try:
            self.engine.set_snap_frames(bool(value))
        except RuntimeError as error:
            self._footer(f"Snap not saved: {error}")

    def tb001(self, widget=None) -> None:
        """Place the selected track or clip at the playhead (Maya: key an audio
        event; Blender: move the strip)."""
        noun = self.noun.lower()
        tracks = list(self.engine.list_tracks())
        if not tracks:
            self._footer(f"No {noun}s — add audio files first.")
            return
        menu = self.ui.tb001.option_box.menu
        auto_end = bool(self.engine.END_KEYS) and menu.chk_auto_end_none.isChecked()
        end = " + end-off" if auto_end else ""
        if self._has("key_all") and menu.chk_key_all.isChecked():
            stagger = menu.spn_stagger.value()
            with self.tk.CoreUtils.undo_chunk("Key All Audio"):
                keyed = self.engine.key_all(auto_end=auto_end, stagger=stagger)
            gap = f", stagger {stagger}" if stagger else ""
            self._footer(f"Key All: {len(keyed)} track(s){end}{gap}.")
            return
        if self._has("next_track") and menu.chk_next_event.isChecked():
            track = self.engine.next_track()
            self._syncing_combo = True  # the list shows it; no pick runs
            try:
                self._select(track)
            finally:
                self._syncing_combo = False
        else:
            track = self._selected_track()
        if track is None:
            return
        try:
            with self.tk.CoreUtils.undo_chunk(self.engine.PLACE_LABEL):
                frame = self.engine.key_track(track, auto_end=auto_end)
        except ValueError as error:  # gone between the list and the click
            self._refresh_combo()
            self._footer(str(error))
            return
        self._footer(
            f"{self.engine.PLACE_LABEL}: '{track}' at frame {int(frame)}{end}."
        )

    def btn_select_carrier(self) -> None:
        """Show where the audio lives (Maya: the carrier node; Blender: the
        selected clip in the Sequencer)."""
        try:
            shown = self.engine.reveal(self.ui.cmb000.currentText() or None)
        except ValueError as error:
            self._footer(str(error))
            return
        self._footer(f"Selected '{shown}'.")

    def btn_sync_audio(self) -> None:
        """Rebuild the sound nodes and the composite from the keys (Maya)."""
        if not self.engine.list_tracks():
            self._footer("No tracks — add audio files first.")
            return
        with self.sb.progress(text="Working: Sync Audio to Timeline"):
            with self.tk.CoreUtils.undo_chunk("Sync Audio to Timeline"):
                result = self.engine.sync()
        changed = sum(
            len(result.get(k) or ()) for k in ("created", "updated", "deleted")
        )
        if not changed and not result.get("composite"):
            self._footer("Already synced — nothing changed.")
            return
        composite = "composite rebuilt" if result.get("composite") else "no composite"
        self._footer(f"Synced {changed} sound node change(s); {composite}.")

    # ------------------------------------------------------------------
    # Trim and Range (Blender)
    # ------------------------------------------------------------------

    def s000_init(self, widget) -> None:
        # The selected clip's live trim, never a saved value. Maya: a track
        # plays its whole file from each ON key; there is no trim.
        self.mirror_app_state(widget)
        self._gate(widget, "trim_track")

    def s001_init(self, widget) -> None:
        self.mirror_app_state(widget)
        self._gate(widget, "trim_track")  # Maya: see s000_init

    def b003_init(self, widget) -> None:
        self._gate(widget, "trim_track")  # Maya: see s000_init

    def b003(self) -> None:
        """Apply Trim: the Start/End frames off the selected clip's ends."""
        track = self._selected_track()
        if track is None:
            return
        with self.tk.CoreUtils.undo_chunk("Trim Clip"):
            visible = self.engine.trim_track(
                track, start=int(self.ui.s000.value()), end=int(self.ui.s001.value())
            )
        if visible is None:
            self._refresh_combo()
            self._footer(f"'{track}' is gone from the scene; the list is refreshed.")
            return
        self._footer(f"Trimmed '{track}' — {visible} frame(s) play.")

    def _sync_trim(self) -> None:
        """Show the selected clip's trim in Start/End (Blender's inspector)."""
        if not self._has("get_trim"):
            return  # Maya: no trim (see s000_init)
        track = self.ui.cmb000.currentText()
        trim = self.engine.get_trim(track) if track else None
        for spin, value in zip((self.ui.s000, self.ui.s001), trim or (0, 0)):
            blocked = spin.blockSignals(True)
            spin.setValue(int(value))
            spin.blockSignals(blocked)

    def b004_init(self, widget) -> None:
        """Sync Scene Range: its fit mode in the option box."""
        # Maya: not built yet (BACKLOG: fit the playback range to the keyed
        # tracks); the Sequencer's strips carry their own spans.
        self._gate(widget, "sync_scene_range")
        if getattr(widget, "is_initialized", False):
            return
        widget.is_initialized = True
        widget.option_box.menu.setTitle("Sync Scene Range")
        widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_fit",
            addItems=list(self.FIT_MODES),
            setToolTip=self.sb.tooltip.fmt(
                bullets=[
                    "<b>Extend Only</b> — grow the range to cover clips outside it.",
                    "<b>Exact Fit</b> — fit the range to the clips (it can shrink).",
                ],
            ),
        )

    def b004(self, widget=None) -> None:
        """Fit the scene frame range to the clips."""
        fit = self.ui.b004.option_box.menu.cmb_fit.currentIndex()
        with self.tk.CoreUtils.undo_chunk("Sync Scene Range"):
            start, end = self.engine.sync_scene_range(extend_only=fit <= 0)
        self._footer(f"Scene range synced to the clips: {start}-{end}.")

    # ------------------------------------------------------------------
    # The scene's events
    # ------------------------------------------------------------------

    def _visible(self) -> bool:
        try:
            return bool(self.ui.isVisible())
        except RuntimeError:  # the window is gone
            return False

    def _hydrate(self) -> None:
        """Re-read the scene: the list, an older scene's audio data (offered
        once per scene) and Maya's composite on the Time Slider."""
        if not self._visible():
            return
        self._refresh_combo()
        self._offer_legacy_migration()
        # Blender: the Sequencer plays every strip; no composite to attach.
        if self._has("attach_composite"):
            try:
                self.engine.attach_composite()
            except Exception:  # noqa: BLE001 -- a hydrate never blocks the panel
                _log.debug("attach_composite failed", exc_info=True)

    def _on_scene_opened(self) -> None:
        self._playing = None
        self._legacy_offered = False
        self._hydrate()

    def _on_tracks_changed(self) -> None:
        """A track was edited elsewhere (Maya: the carrier's attributes): the
        composite follows while the panel shows, and so does the list."""
        if self._syncing_combo or not self._visible():
            return
        try:
            if self._has("sync"):  # Blender: no composite (see btn_sync_audio)
                self.engine.sync()
            self._refresh_combo()
        except Exception:  # noqa: BLE001 -- an event never raises into the host
            _log.debug("_on_tracks_changed failed", exc_info=True)

    def _on_time_changed(self, frame) -> None:
        """The list follows the track playing at the playhead (Maya)."""
        if self._syncing_combo or not self._visible():
            return
        playing = self.engine.tracks_at(frame)
        track = playing[0] if playing else None
        if track == self._playing:
            return
        self._playing = track
        cmb = self.ui.cmb000
        self._syncing_combo = True
        blocked = cmb.blockSignals(True)
        try:
            cmb.setCurrentIndex(cmb.findText(track) if track else -1)
        finally:
            cmb.blockSignals(blocked)
            self._syncing_combo = False

    def _offer_legacy_migration(self) -> None:
        """Offer to move an older scene's audio data onto tracks, once per scene."""
        # Blender never had the legacy ``audio_trigger`` schema.
        if self._legacy_offered or not self._has("has_legacy_data"):
            return
        self._legacy_offered = True
        if not self.engine.has_legacy_data():
            return
        answer = self.sb.message_box(
            "<strong>Older audio data</strong>.<br>This scene keeps its audio in "
            "the legacy <i>audio_trigger</i> schema. Move it onto tracks now? "
            "(Keys and file paths are kept.)",
            "Yes",
            "No",
        )
        if answer != "Yes":
            return
        try:
            with self.tk.CoreUtils.undo_chunk("Migrate Legacy Audio"):
                migrated = self.engine.migrate_legacy()
        except Exception as error:  # noqa: BLE001 -- reported, never raised
            self.sb.message_box(f"<strong>Migration failed</strong>.<br>{error}")
            return
        self._refresh_combo()
        self._footer(f"Migrated {len(migrated)} legacy track(s).")

    # ------------------------------------------------------------------

    def _footer(self, text: str) -> None:
        self.ui.footer.setText(text)
